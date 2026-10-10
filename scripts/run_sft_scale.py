"""Bounded single-arm LoRA SFT. Default is CPU validation; --execute needs user approval."""
import argparse,gc,hashlib,importlib.metadata,json,os,sys,threading,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from run_day3 import ROOT,write,append,Monitor
from run_sft_probe import frozen_sample
from veriagent.sft_stage import validate_deployment,verify_weights,require,sha
from veriagent.sft_scale import load_inputs


def validate_actual_tokenizer(cfg,examples):
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(ROOT/cfg['weights_path'],local_files_only=True,trust_remote_code=False)
    # Recheck actual Transformers tokenizer against every complete encoded string.
    source=ROOT/'experiments'/cfg['source_run']
    rows={r['task_uid']:r for r in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
    for ex in examples:
        r=rows[ex['task_uid']];turn=r['rounds'][ex['turn']-1]
        prefix=tokenizer.apply_chat_template(turn['input_messages'],tools=r['tool_schemas'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        complete=tokenizer.apply_chat_template(turn['input_messages']+[turn['assistant_message']],tools=r['tool_schemas'],tokenize=False,add_generation_prompt=False,enable_thinking=False)
        require(complete.startswith(prefix) and complete.endswith('<|im_end|>\n'),'Actual template continuation mismatch')
        require(hashlib.sha256(prefix.encode()).hexdigest()==ex['prefix_sha256'],'Actual prefix hash differs')
        require(tokenizer(prefix,add_special_tokens=False)['input_ids']==ex['input_ids'][:ex['prefix_tokens']],'Actual prefix IDs differ')
        require(tokenizer(complete[len(prefix):-1],add_special_tokens=False)['input_ids']==ex['labels'][ex['prefix_tokens']:],'Actual target IDs differ')
    return tokenizer


def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=['S100'],required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--run-id');p.add_argument('--hourly-rmb',type=float)
    args=p.parse_args();cfg,selection,examples,order=load_inputs(args.arm,reencode=True)
    if not args.execute:
        print(json.dumps({'status':'CPU_ADMISSION_PASSED_NO_MODEL_LOAD','arm':args.arm,'tasks':len(selection['tasks']),
                          'examples':len(examples),'planned_updates':len(order),'totals_per_epoch':selection['totals']}));return
    require(os.name=='posix' and args.run_id and args.run_id.startswith('SFT-'+args.arm+'-'),'Explicit bounded Linux run ID required')
    require(Path(args.run_id).name==args.run_id,'Invalid run ID')
    if args.hourly_rmb is not None:require(0<args.hourly_rmb<float('inf'),'Invalid price')
    build=validate_deployment(['configs/sft_scale_plan_v2.json','veriagent/sft_scale.py','scripts/run_sft_scale.py'])
    out=ROOT/'experiments'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    write(out/'config.json',{**cfg,'arm':args.arm,'status':'RUNNING','hourly_rmb':args.hourly_rmb})
    write(out/'sample_order.json',order);write(out/'selection.json',selection)
    identity={'experiment_id':args.run_id,'code_commit':build['code_commit'],'deployment':build,'arm':args.arm,
        'model_revision':cfg['model_revision'],'data_sha256':selection['data_sha256'],'seed':cfg['seed'],
        'started_at':datetime.now(timezone.utc).isoformat(),'initialization':'fresh_base_fresh_LoRA'}
    write(out/'identity.json',identity);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started'})
    started=time.perf_counter();steps=[]
    def deadline():
        write(out/'deadline.json',{'status':'SFT_WALL_LIMIT','completed_updates':len(steps),'max_wall_seconds':cfg['max_wall_seconds']})
        os._exit(124)
    timer=threading.Timer(cfg['max_wall_seconds'],deadline);timer.daemon=True;timer.start()
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start()
    try:
        packages={n:importlib.metadata.version(n) for n in cfg['required_packages']}
        require(packages==cfg['required_packages'],'Unqualified package versions')
        write(out/'weight_revalidation.json',verify_weights(cfg))
        import torch
        from torch.nn import functional as F
        from transformers import AutoTokenizer,AutoModelForCausalLM,set_seed
        from peft import LoraConfig,TaskType,get_peft_model,PeftModel
        require(torch.cuda.device_count()==1,'Exactly one GPU required')
        require(torch.cuda.get_device_properties(0).total_memory>=cfg['min_gpu_memory_gib']*2**30,'Need80/96GB class GPU')
        set_seed(cfg['seed']);path=ROOT/cfg['weights_path']
        tokenizer=validate_actual_tokenizer(cfg,examples)
        def base():
            return AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,
                dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        model=get_peft_model(base(),LoraConfig(task_type=TaskType.CAUSAL_LM,r=cfg['lora_rank'],lora_alpha=cfg['lora_alpha'],
            lora_dropout=cfg['lora_dropout'],bias='none',target_modules=cfg['target_modules']))
        model.config.use_cache=False;model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
        require(sum(p.numel() for p in trainable.values())==cfg['expected_trainable_parameters'],'Wrong trainable count')
        require(all('lora_' in n for n in trainable),'Unexpected trainable base weights')
        before={n:p.detach().cpu().clone() for n,p in trainable.items()};frozen=frozen_sample(model)
        optimizer=torch.optim.AdamW(list(trainable.values()),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
        identity.update({'packages':packages,'gpu':torch.cuda.get_device_name(0),'trainable_parameters':sum(p.numel() for p in trainable.values()),'frozen_sample_before':frozen})
        write(out/'identity.json',identity);torch.cuda.reset_peak_memory_stats();model.train()
        for number,item in enumerate(order,1):
            ex=examples[item['example_index']]
            batch={k:torch.tensor([ex[k]],dtype=torch.long,device='cuda') for k in ['input_ids','labels','attention_mask']}
            optimizer.zero_grad(set_to_none=True);torch.cuda.synchronize();tick=time.perf_counter()
            output=model(**batch,use_cache=False);loss=output.loss
            require(loss.requires_grad and torch.isfinite(loss).item(),'Invalid loss/graph')
            delta=None
            if number==1:
                labels=batch['labels'][:,1:];mask=labels!=-100
                manual=F.cross_entropy(output.logits[:,:-1,:].detach()[mask].float(),labels[mask])
                delta=abs(manual.item()-loss.item())
                require(torch.allclose(manual,loss.detach(),atol=1e-4,rtol=1e-4),'Manual/model shifted CE disagree')
                del manual,labels,mask
            loss.backward();grads=[p.grad for p in trainable.values() if p.grad is not None]
            require(grads and all(torch.isfinite(g).all().item() for g in grads),'Nonfinite/missing gradients')
            nonzero=sum(g.count_nonzero().item()>0 for g in grads);require(nonzero>0,'Zero adapter gradient')
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),cfg['max_grad_norm'],error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize()
            step={'step':number,**item,'task_uid':ex['task_uid'],'turn':ex['turn'],'loss':loss.detach().item(),
                'manual_ce_abs_diff':delta,'nonzero_gradient_tensors':nonzero,'grad_norm':norm.item(),
                'processed_tokens':ex['processed_tokens'],'supervised_tokens':ex['supervised_tokens'],'seconds':time.perf_counter()-tick}
            steps.append(step);append(out/'steps.jsonl',step);print(json.dumps(step),flush=True)
            del output,loss,batch,grads
        require(len(steps)==310,'Incomplete training schedule')
        peak=torch.cuda.max_memory_allocated();reserved=torch.cuda.max_memory_reserved()
        changes={n:(p.detach().cpu().float()-before[n].float()).abs().max().item() for n,p in trainable.items()}
        require(any(v>0 for v in changes.values()),'No LoRA change');require(frozen_sample(model)==frozen,'Frozen sample changed')
        write(out/'adapter_changes.json',changes)
        model.gradient_checkpointing_disable();model.eval();ex=examples[0];prefix=ex['input_ids'][:ex['prefix_tokens']]
        fixed={'input_ids':torch.tensor([prefix],device='cuda'),'attention_mask':torch.ones((1,len(prefix)),dtype=torch.long,device='cuda')}
        def readout(policy):
            with torch.inference_mode():
                logits=policy(**fixed,use_cache=False,logits_to_keep=1).logits[0,-1].float().cpu()
                ids=policy.generate(**fixed,max_new_tokens=min(64,8192-len(prefix)),do_sample=False,use_cache=True,
                    pad_token_id=tokenizer.pad_token_id)[0,len(prefix):].tolist()
            return logits,ids
        expected,expected_ids=readout(model);adapter=out/'adapter';model.save_pretrained(adapter,safe_serialization=True)
        hashes={f.name:sha(f) for f in adapter.iterdir() if f.is_file()};write(out/'adapter_manifest.json',hashes)
        del optimizer,trainable,before,model;gc.collect();torch.cuda.empty_cache()
        reloaded=PeftModel.from_pretrained(base(),adapter,is_trainable=False);reloaded.eval()
        actual,actual_ids=readout(reloaded)
        reload_ok=torch.allclose(expected,actual,atol=cfg['reload_atol'],rtol=cfg['reload_rtol']) and expected_ids==actual_ids
        write(out/'reload_check.json',{'passed':reload_ok,'max_logit_abs_diff':(expected-actual).abs().max().item(),
            'expected_ids':expected_ids,'reloaded_ids':actual_ids,'interpretation':'Identity only,not Agent evaluation'})
        require(reload_ok,'Reload failed');wall=time.perf_counter()-started
        result={'status':'SFT_TRAINING_COMPLETE_RELOAD_PASSED','arm':args.arm,'optimizer_updates':310,
            'training_tasks':100,'processed_tokens':sum(s['processed_tokens'] for s in steps),
            'supervised_tokens':sum(s['supervised_tokens'] for s in steps),'mean_step_seconds':sum(s['seconds'] for s in steps)/len(steps),
            'peak_training_allocated_gib':peak/2**30,'peak_training_reserved_gib':reserved/2**30,
            'changed_adapter_tensors':sum(v>0 for v in changes.values()),'frozen_samples_unchanged':True,
            'wall_seconds':wall,'gpu_hours':wall/3600,'cost_estimate_rmb':wall/3600*args.hourly_rmb if args.hourly_rmb is not None else None,
            'agent_evaluation':'NOT_RUN','checkpoint_selection':'fixed_final','generalization_claim':False,
            'cost_scope':'Execution record creation through save/reload; earlier CPU admission/instance uptime/storage excluded and must be reported separately'}
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps(result),flush=True)
    except Exception as exc:
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),
            'completed_updates':len(steps),'wall_seconds':time.perf_counter()-started,'retain_cost':True})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete'});raise
    finally:timer.cancel();monitor.stop()


if __name__=='__main__':main()
