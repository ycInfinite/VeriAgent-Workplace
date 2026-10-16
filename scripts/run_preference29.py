"""Frozen29-task current-S1 chosen-SFT versus DPO comparison; default is validation.

Execution requires a separately authorized GPU session and pinned deployment.
No rollout, network, installation, evaluation or next-stage launch is performed.
"""
import argparse, gc, hashlib, importlib.metadata, json, math, os, threading, time, traceback
from datetime import datetime, timezone
from pathlib import Path
from run_day3 import ROOT, write, append, Monitor
from run_sft_probe import frozen_sample
from veriagent.dpo import load_pairs, cache_key, branch_score, pair_backward
from veriagent.sft_stage import require, sha, validate_deployment, verify_weights


def actual_tokenizer_check(tokenizer, pairs):
    count=0
    for p in pairs:
        for side in ['chosen','rejected']:
            messages=p[side]['messages'];examples=iter(p[side]['encoded_turns'])
            for i,m in enumerate(messages):
                if m['role']!='assistant':continue
                e=next(examples)
                prefix=tokenizer.apply_chat_template(messages[:i],tools=p['tools'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
                complete=tokenizer.apply_chat_template(messages[:i+1],tools=p['tools'],tokenize=False,add_generation_prompt=False,enable_thinking=False)
                require(complete.startswith(prefix) and complete.endswith('<|im_end|>\n'),'HF template changed')
                ids=tokenizer(prefix,add_special_tokens=False)['input_ids']
                targets=tokenizer(complete[len(prefix):-1],add_special_tokens=False)['input_ids']
                require(e['input_ids']==ids+targets and e['labels']==[-100]*len(ids)+targets,'HF IDs/mask mismatch')
                count+=1
    return count


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--condition',choices=['CHOSEN_SFT','DPO'],required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--run-id');ap.add_argument('--hourly-rmb',type=float)
    args=ap.parse_args();cfg,pairs=load_pairs('configs/preference29_plan.json')
    if not args.execute:
        print(json.dumps({'status':'LOCAL_DATA_ADMISSION_ONLY','pairs':len(pairs),'model_loaded':False,'parameter_updates':0}));return
    require(os.name=='posix' and args.run_id and args.run_id==cfg['training_run_ids'][args.condition] and Path(args.run_id).name==args.run_id,'Explicit Linux probe ID required')
    if args.hourly_rmb is not None:require(math.isfinite(args.hourly_rmb) and args.hourly_rmb>0,'Invalid rate')
    require(cfg['GPU_training_authorized'], 'Training not authorized')
    build=validate_deployment(cfg['deployment_files'])
    out=ROOT/'experiments'/args.run_id;out.mkdir(exist_ok=False);start=time.perf_counter();steps=[]
    write(out/'config.json',{**cfg,'condition':args.condition});write(out/'identity.json',{'code_commit':build['code_commit'],'deployment':build,'started_at':datetime.now(timezone.utc).isoformat(),'seed':cfg['seed'],'model_revision':cfg['model_revision'],'dataset_revision':cfg['dataset_revision'],'initial_adapter_sha256':cfg['initial_adapter_sha256'],'condition':args.condition})
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started'})
    def deadline():
        write(out/'invalid_run.json',{'kind':'wall_limit','updates_completed':len(steps),'max_seconds':cfg['max_wall_seconds']});os._exit(124)
    timer=threading.Timer(cfg['max_wall_seconds'],deadline);timer.daemon=True;timer.start()
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start()
    try:
        packages={n:importlib.metadata.version(n) for n in cfg['required_packages']}
        require(packages==cfg['required_packages'],'Package mismatch')
        write(out/'weights.json',verify_weights(cfg))
        adapter=ROOT/cfg['initial_adapter_path']
        for name,h in cfg['initial_adapter_sha256'].items():require(sha(adapter/name)==h,'Wrong initial S1 adapter')
        import torch
        from check_preference_torch import run_controls
        write(out/'torch_cpu_controls.json',run_controls())
        from transformers import AutoTokenizer,AutoModelForCausalLM,set_seed
        from peft import PeftModel
        require(torch.cuda.device_count()==1 and torch.cuda.is_bf16_supported(),'Single BF16 GPU required')
        require(torch.cuda.get_device_properties(0).total_memory>=cfg['min_gpu_memory_gib']*2**30,'Probe qualified hardware plan requires96GB class;80GB unqualified')
        set_seed(cfg['seed']);tokenizer=AutoTokenizer.from_pretrained(ROOT/cfg['weights_path'],local_files_only=True)
        actual_count=actual_tokenizer_check(tokenizer,pairs)
        require(actual_count==179, 'Whole29 HF turn count changed')
        write(out/'host_preflight.json',{'HF_turns_checked':actual_count,'packages':packages,'gpu':torch.cuda.get_device_name(0),'torch_cuda':torch.version.cuda,'single_gpu':True})
        def base():
            return AutoModelForCausalLM.from_pretrained(ROOT/cfg['weights_path'],local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
        model=PeftModel.from_pretrained(base(),adapter,is_trainable=True)
        model.config.use_cache=False;model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});model.train()
        require(getattr(model.config,'attention_dropout',0.)==0.,'Attention dropout must be zero')
        require(all(m.p==0 for m in model.modules() if isinstance(m,torch.nn.Dropout)),'Two-pass exact gradient requires dropout0')
        trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
        require(sum(p.numel() for p in trainable.values())==cfg['expected_trainable_parameters'] and all('lora_' in n for n in trainable),'Trainable policy mismatch')
        before={n:p.detach().cpu().clone() for n,p in trainable.items()};frozen=frozen_sample(model)
        selected={p['task_id']:p for p in pairs};order=[selected[i] for i in cfg['task_order']]
        require(len(order)==cfg['optimizer_updates']==29,'Comparison schedule changed')
        torch.cuda.reset_peak_memory_stats();reference={};tick=time.perf_counter()
        for p in (order if args.condition=='DPO' else []):
            reference[p['pair_id']]={'cache_key':cache_key(cfg,p),**{s:branch_score(model,p[s]['encoded_turns']) for s in ['chosen','rejected']}}
        reference_seconds=time.perf_counter()-tick;write(out/'reference_scores.json',reference);reference_hash=sha(out/'reference_scores.json')
        require(frozen_sample(model)==frozen and all(torch.equal(p.detach().cpu(),before[n]) for n,p in trainable.items()),'Reference pass mutated policy')
        optimizer=torch.optim.AdamW(list(trainable.values()),lr=cfg['learning_rate'],weight_decay=0.)
        for number,p in enumerate(order,1):
            optimizer.zero_grad(set_to_none=True);torch.cuda.synchronize();tick=time.perf_counter()
            if args.condition=='DPO':
                ref=reference[p['pair_id']];require(ref['cache_key']==cache_key(cfg,p),'Reference cache identity mismatch')
                evidence=pair_backward(model,p,ref,cfg['beta'],cfg['recompute_atol'])
                if number==1:require(abs(evidence['relative_margin'])<=cfg['initial_margin_atol'] and abs(evidence['loss']-math.log(2))<.01,'Initial policy differs from S1 reference')
            else:
                from veriagent.dpo import turn_logp
                target_count=p['chosen']['target_tokens'];total=0.
                for ex in p['chosen']['encoded_turns']:
                    nll=-turn_logp(model,ex)/target_count
                    total+=float(nll.detach());nll.backward();del nll
                evidence={'loss':total,'objective':'task_mean_chosen_CE','target_tokens':target_count}
            grads=[p.grad for p in trainable.values() if p.grad is not None]
            require(grads and all(torch.isfinite(g).all().item() for g in grads) and any(g.count_nonzero().item()>0 for g in grads),'Invalid DPO gradients')
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),cfg['max_grad_norm'],error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize()
            entry={'step':number,'pair_id':p['pair_id'],**evidence,'grad_norm':norm.item(),'seconds':time.perf_counter()-tick}
            steps.append(entry);append(out/'steps.jsonl',entry);print(json.dumps(entry),flush=True)
        require(sha(out/'reference_scores.json')==reference_hash,'Reference cache changed')
        changed={n:float((p.detach().cpu().float()-before[n].float()).abs().max()) for n,p in trainable.items()}
        require(any(v>0 for v in changed.values()) and frozen_sample(model)==frozen,'Update/frozen parameter failure')
        write(out/'adapter_changes.json',changed)
        for name,h in cfg['initial_adapter_sha256'].items():require(sha(adapter/name)==h,'Initial S1 artifact modified')
        allocated=torch.cuda.max_memory_allocated()/2**30;reserved=torch.cuda.max_memory_reserved()/2**30
        model.gradient_checkpointing_disable();model.eval();ex=order[0]['chosen']['encoded_turns'][0]
        fixed=torch.tensor([ex['input_ids'][:ex['prefix_tokens']]],device='cuda')
        def readout(policy):
            with torch.inference_mode():
                logits=policy(input_ids=fixed,attention_mask=torch.ones_like(fixed),use_cache=False,logits_to_keep=1).logits[0,-1].float().cpu()
                ids=policy.generate(input_ids=fixed,attention_mask=torch.ones_like(fixed),max_new_tokens=64,do_sample=False,use_cache=True,pad_token_id=tokenizer.pad_token_id)[0,fixed.shape[1]:].tolist()
            return logits,ids
        expected,expected_ids=readout(model);model.save_pretrained(out/'adapter',safe_serialization=True)
        write(out/'adapter_manifest.json',{p.name:sha(p) for p in (out/'adapter').iterdir() if p.is_file()})
        del optimizer,trainable,before,model;gc.collect();torch.cuda.empty_cache()
        reloaded=PeftModel.from_pretrained(base(),out/'adapter',is_trainable=False);reloaded.eval();actual,ids=readout(reloaded)
        ok=torch.allclose(actual,expected,atol=.001,rtol=.001) and ids==expected_ids
        write(out/'reload_check.json',{'passed':ok,'max_logit_abs_diff':float((actual-expected).abs().max()),'expected_ids':expected_ids,'reloaded_ids':ids});require(ok,'Reload mismatch')
        wall=time.perf_counter()-start
        write(out/'result.json',{'status':'PREFERENCE_TRAINING_COMPLETE_RELOAD_PASSED','condition':args.condition,'optimizer_updates':len(steps),'reference_seconds':reference_seconds,'mean_step_seconds':sum(s['seconds'] for s in steps)/len(steps),'peak_allocated_GiB':allocated,'peak_reserved_GiB':reserved,'wall_seconds':wall,'GPU_hours':wall/3600,'estimated_rmb':None if args.hourly_rmb is None else wall/3600*args.hourly_rmb,'agent_success_measured':False,'reference_sha256':reference_hash,'note':'Includes reference passes and reload;setup/idle/storage excluded;not onlineRL or efficacy evidence'})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
    except Exception:
        write(out/'invalid_run.json',{'traceback':traceback.format_exc(),'completed_updates':len(steps),'wall_seconds':time.perf_counter()-start});append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'failed_preserved'});raise
    finally:timer.cancel();monitor.stop()


if __name__=='__main__':main()
