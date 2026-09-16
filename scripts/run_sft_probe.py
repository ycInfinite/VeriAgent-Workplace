"""Eight-update single-GPU LoRA integrity probe with strict training admission.

Requires actual, manually reviewed training-pool trajectories. Never treats dev
examples or educational code as a training corpus. No automatic data generation.
"""
import argparse
from datetime import datetime,timezone
import gc
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from veriagent.sft_data import TurnEncoder,content_sha256,export_training_turns


def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def append(path,value):
    with path.open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(value,ensure_ascii=False)+'\n');handle.flush()


def prepare_examples(config,trajectory_path,review_path,source_format='recorded-policy'):
    cohort=json.loads((ROOT/config['cohort_manifest']).read_text())
    approved_tasks={x['task_uid']:x for x in cohort['tasks']}
    raw=[json.loads(x) for x in trajectory_path.read_text().splitlines() if x.strip()]
    by_hash={content_sha256(x):x for x in raw}
    reviews=json.loads(review_path.read_text())['approved']
    if len({x['trajectory_sha256'] for x in reviews})!=len(reviews):
        raise ValueError('Duplicate quality approval')
    selected=[];examples=[]
    if source_format=='canonical-teacher':
        from veriagent.teacher_data import CanonicalTeacherEncoder,export_teacher_turns
        encoder=CanonicalTeacherEncoder(config['max_context_tokens'])
        teacher_config=json.loads((trajectory_path.parent/'config.json').read_text())
    elif source_format=='recorded-policy':
        encoder=TurnEncoder(config['max_context_tokens'])
    else:raise ValueError('Unknown source format')
    for review in reviews:
        record=by_hash.get(review['trajectory_sha256'])
        if record is None:raise ValueError('Reviewed trajectory missing from raw artifact')
        if record['condition']!='B1':raise ValueError('Unexpected prompt condition')
        if source_format=='canonical-teacher':
            examples.extend(export_teacher_turns(record,review,approved_tasks,encoder,teacher_config))
        else:examples.extend(export_training_turns(record,review,approved_tasks,encoder))
        selected.append(record)
    task_count=len({r['task_uid'] for r in selected})
    if not config['min_training_tasks']<=task_count<=config['max_training_tasks']:
        raise ValueError('Probe requires two to four distinct approved training tasks')
    if task_count!=len(selected):raise ValueError('Use one trajectory per task for this probe')
    if not 1<=len(examples)<=config['max_examples']:raise ValueError('Example-count bound exceeded')
    return selected,examples,encoder


def frozen_sample(model):
    digest=hashlib.sha256()
    for name,p in model.named_parameters():
        if not p.requires_grad:
            digest.update(name.encode())
            digest.update(p.detach().reshape(-1)[:32].float().cpu().numpy().tobytes())
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--trajectories',required=True)
    parser.add_argument('--reviews',required=True)
    parser.add_argument('--hourly-rmb',type=float)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--source-format',choices=['recorded-policy','canonical-teacher'],default='recorded-policy')
    args=parser.parse_args()
    config=json.loads((ROOT/'configs/sft_probe_plan.json').read_text())
    if args.hourly_rmb is not None and (not math.isfinite(args.hourly_rmb) or args.hourly_rmb<=0):
        raise ValueError('Invalid actual price')
    trajectory_path=ROOT/args.trajectories;review_path=ROOT/args.reviews
    selected,examples,encoder=prepare_examples(config,trajectory_path,review_path,args.source_format)
    if args.validate_only:
        print(json.dumps({'status':'DATA_ADMISSION_PASSED','tasks':len(selected),
            'examples':len(examples),'source_format':args.source_format,
            'processed_tokens':sum(x['processed_tokens'] for x in examples),
            'supervised_tokens':sum(x['supervised_tokens'] for x in examples),'model_loaded':False}));return
    integrity=json.loads((ROOT/'model_integrity.json').read_text())
    if integrity.get('revision')!=config['model_revision'] or not integrity.get('all_match'):
        raise ValueError('Weight integrity gate missing')
    packages={name:importlib.metadata.version(name) for name in config['required_packages']}
    if packages!=config['required_packages']:raise ValueError('Unqualified training package versions')
    out=ROOT/'experiments'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    config.update({'hourly_rmb':args.hourly_rmb,'trajectory_artifact':args.trajectories,
        'review_artifact':args.reviews,'source_format':args.source_format,'status':'RUNNING'})
    write(out/'config.json',config)
    manifest=json.loads((ROOT/'bundle_manifest.json').read_text())
    for entry in manifest['files']:
        if hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Training bundle content mismatch')
    identity={'experiment_id':args.run_id,'kind':'REAL_LORA_SFT_INTEGRITY_PROBE',
        'started_at':datetime.now(timezone.utc).isoformat(),'code_commit':manifest['code_commit'],
        'bundle_manifest':manifest,'model_revision':config['model_revision'],'seed':config['seed'],
        'packages':packages,'trajectories_sha256':hashlib.sha256(trajectory_path.read_bytes()).hexdigest(),
        'reviews_sha256':hashlib.sha256(review_path.read_bytes()).hexdigest(),
        'weights_receipt_sha256':hashlib.sha256((ROOT/'model_integrity.json').read_bytes()).hexdigest()}
    write(out/'identity.json',identity);write(out/'quality_approvals.json',json.loads(review_path.read_text()))
    for ex in examples:append(out/'training_examples.jsonl',ex)
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started','identity':identity})
    started=time.perf_counter();steps=[]
    def deadline():
        write(out/'deadline.json',{'status':'SFT_PROCESS_DEADLINE','completed_updates':len(steps),
            'max_wall_seconds':config['max_wall_seconds']})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'deadline_incomplete'})
        os._exit(124)
    timer=threading.Timer(config['max_wall_seconds'],deadline);timer.daemon=True;timer.start()
    from run_day3 import Monitor
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start()
    try:
        import torch
        from torch.nn import functional as F
        from transformers import AutoTokenizer,AutoModelForCausalLM,set_seed
        from peft import LoraConfig,TaskType,get_peft_model,PeftModel
        if torch.cuda.device_count()!=1:raise ValueError('Exactly one visible GPU required')
        if torch.cuda.get_device_properties(0).total_memory < config['min_gpu_memory_gib']*2**30:
            raise ValueError('This BF16 probe requires the planned 80GB-class single GPU')
        set_seed(config['seed'])
        path=ROOT/config['weights_path']
        tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
        by_turn={(ex['task_uid'],ex['turn']):ex for ex in examples}
        for record in selected:
            for turn in record['rounds']:
                prompt=tokenizer.apply_chat_template(turn['input_messages'],tools=record['tool_schemas'],
                    tokenize=False,add_generation_prompt=True,enable_thinking=False)
                ex=by_turn[(record['task_uid'],turn['turn'])]
                if hashlib.sha256(prompt.encode()).hexdigest()!=ex['input_sha256']:
                    raise ValueError('Actual trainer tokenizer prompt differs from recorded rollout')
                if tokenizer(prompt,add_special_tokens=False)['input_ids']!=encoder.inspector.tokenizer.encode(prompt,add_special_tokens=False).ids:
                    raise ValueError('Actual trainer tokenizer IDs differ')
                if args.source_format=='canonical-teacher':
                    complete=tokenizer.apply_chat_template(turn['input_messages']+[turn['assistant_message']],
                        tools=record['tool_schemas'],tokenize=False,add_generation_prompt=False,enable_thinking=False)
                    if not complete.startswith(prompt) or not complete.endswith('<|im_end|>\n'):
                        raise ValueError('Actual trainer canonical template differs')
                    target=tokenizer(complete[len(prompt):-1],add_special_tokens=False)['input_ids']
                    if target!=ex['labels'][ex['prefix_tokens']:]:
                        raise ValueError('Actual trainer canonical target IDs differ')
        def load_base():
            return AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.bfloat16,
                device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        model=get_peft_model(load_base(),LoraConfig(task_type=TaskType.CAUSAL_LM,inference_mode=False,
            r=config['lora_rank'],lora_alpha=config['lora_alpha'],lora_dropout=config['lora_dropout'],
            bias='none',target_modules=config['target_modules']))
        model.config.use_cache=False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        trainable={name:p for name,p in model.named_parameters() if p.requires_grad}
        if sum(p.numel() for p in trainable.values())!=config['expected_trainable_parameters']:
            raise ValueError('Unexpected trainable parameter count')
        if any('lora_' not in name for name in trainable):raise ValueError('Unexpected trainable base module')
        before={name:p.detach().cpu().clone() for name,p in trainable.items()}
        frozen_before=frozen_sample(model)
        optimizer=torch.optim.AdamW(list(trainable.values()),lr=config['learning_rate'],weight_decay=config['weight_decay'])
        identity.update({'gpu':torch.cuda.get_device_name(0),'trainable_parameters':sum(p.numel() for p in trainable.values()),
            'trainable_shapes':{n:list(p.shape) for n,p in trainable.items()},'frozen_sample_before':frozen_before})
        write(out/'identity.json',identity)
        torch.cuda.reset_peak_memory_stats();model.train()
        for index in range(config['steps']):
            ex=examples[index%len(examples)]
            batch={key:torch.tensor([ex[key]],dtype=torch.long,device='cuda') for key in ('input_ids','labels','attention_mask')}
            optimizer.zero_grad(set_to_none=True);torch.cuda.synchronize();step_start=time.perf_counter()
            output=model(**batch,use_cache=False);loss=output.loss
            if not loss.requires_grad or not torch.isfinite(loss).item():raise ValueError('Invalid model CE/gradient graph')
            manual_delta=None
            if index==0:
                labels=batch['labels'][:,1:];mask=labels!=-100
                manual=F.cross_entropy(output.logits[:,:-1,:].detach()[mask].float(),labels[mask])
                manual_delta=abs(manual.item()-loss.item())
                if not torch.allclose(manual,loss.detach(),atol=1e-4,rtol=1e-4):raise ValueError('Manual/model CE mismatch')
                del manual
            loss.backward()
            grads=[p.grad for p in trainable.values() if p.grad is not None]
            if not grads or not all(torch.isfinite(g).all().item() for g in grads):raise ValueError('Missing/nonfinite gradients')
            nonzero=sum(g.count_nonzero().item()>0 for g in grads)
            if not nonzero:raise ValueError('No nonzero adapter gradient')
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),config['max_grad_norm'],error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize()
            step={'step':index+1,'task_uid':ex['task_uid'],'turn':ex['turn'],'loss':loss.detach().item(),
                'manual_ce_abs_diff':manual_delta,'gradient_norm_before_clip':norm.item(),
                'nonzero_gradient_tensors':nonzero,'processed_tokens':ex['processed_tokens'],
                'supervised_tokens':ex['supervised_tokens'],'seconds':time.perf_counter()-step_start}
            steps.append(step);append(out/'steps.jsonl',step);print(json.dumps(step),flush=True)
            del output,loss,batch,grads
        peak=torch.cuda.max_memory_allocated();reserved=torch.cuda.max_memory_reserved()
        changes={name:(p.detach().cpu().float()-before[name].float()).abs().max().item() for name,p in trainable.items()}
        if not any(v>0 for v in changes.values()):raise ValueError('No changed adapter parameters')
        if frozen_sample(model)!=frozen_before:raise ValueError('Frozen parameter sample changed')
        write(out/'adapter_changes.json',changes)
        model.gradient_checkpointing_disable();model.eval()
        ex=examples[0];prefix=ex['input_ids'][:ex['prefix_tokens']]
        fixed={'input_ids':torch.tensor([prefix],device='cuda'),
               'attention_mask':torch.ones((1,len(prefix)),dtype=torch.long,device='cuda')}
        cap=min(64,config['max_context_tokens']-len(prefix))
        def probe_output(policy):
            with torch.inference_mode():
                logits=policy(**fixed,use_cache=False,logits_to_keep=1).logits[0,-1].float().cpu()
                ids=policy.generate(**fixed,max_new_tokens=cap,do_sample=False,use_cache=True,
                    pad_token_id=tokenizer.pad_token_id)[0,len(prefix):].tolist()
            return logits,ids
        expected_logits,expected_ids=probe_output(model)
        adapter_dir=out/'adapter';model.save_pretrained(adapter_dir,safe_serialization=True)
        # Free first model before loading another full 8B instance on this one GPU.
        del optimizer,trainable,before,model;gc.collect();torch.cuda.empty_cache()
        reloaded=PeftModel.from_pretrained(load_base(),adapter_dir,is_trainable=False)
        reloaded.eval();actual_logits,actual_ids=probe_output(reloaded)
        logit_ok=torch.allclose(expected_logits,actual_logits,atol=config['reload_atol'],rtol=config['reload_rtol'])
        output_ok=expected_ids==actual_ids
        write(out/'reload_check.json',{'logits_allclose':logit_ok,'greedy_ids_equal':output_ok,
            'max_logit_abs_diff':(expected_logits-actual_logits).abs().max().item(),
            'atol':config['reload_atol'],'rtol':config['reload_rtol'],
            'expected_generated_ids':expected_ids,'reloaded_generated_ids':actual_ids,
            'interpretation':'Fixed-input identity check, not Agent task success'})
        if not logit_ok or not output_ok:raise ValueError('Adapter reload gate failed')
        wall=time.perf_counter()-started
        result={'status':'SFT_INTEGRITY_PROBE_PASSED','optimizer_updates':len(steps),
            'training_tasks':len(selected),'available_per_turn_examples':len(examples),
            'sample_order':'stored approval order, then model turn; cycle if more updates than examples',
            'processed_tokens':sum(x['processed_tokens'] for x in steps),
            'supervised_tokens':sum(x['supervised_tokens'] for x in steps),
            'step_seconds':[x['seconds'] for x in steps],
            'changed_adapter_tensors':sum(x>0 for x in changes.values()),'frozen_samples_unchanged':True,
            'peak_training_allocated_gib':peak/2**30,'peak_training_reserved_gib':reserved/2**30,
            'peak_full_probe_allocated_gib':torch.cuda.max_memory_allocated()/2**30,
            'reload_passed':True,'wall_seconds':wall,'gpu_hours':wall/3600,
            'cost_estimate_rmb':wall/3600*args.hourly_rmb if args.hourly_rmb is not None else None,
            'agent_evaluation':'NOT_PERFORMED','generalization_claim':False,
            'cost_scope':'Process wall, excluding earlier preparation/idle/storage'}
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps(result,indent=2),flush=True)
    except Exception as exc:
        wall=time.perf_counter()-started
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),
            'completed_updates':len(steps),'wall_seconds':wall,
            'cost_estimate_rmb':wall/3600*args.hourly_rmb if args.hourly_rmb is not None else None})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete'})
        raise
    finally:
        timer.cancel();monitor.stop()


if __name__=='__main__':main()
