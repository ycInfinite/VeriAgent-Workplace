"""Real Qwen3 inference with real official tools. No optimizer, gradient or training."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from veriagent.environment import WorkplaceEnv,snapshot,digest,canonical
from veriagent.policy_protocol import parse_tool_calls,identifier_candidates
from resources_servers.workplace_assistant.utils import execute_actions_and_reset_state

def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def append(path,value):
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(value,ensure_ascii=False,default=str)+'\n');f.flush()

class Monitor:
    def __init__(self,path):self.path=path;self.stop_event=threading.Event();self.thread=None
    def start(self):
        def loop():
            while not self.stop_event.is_set():
                try:
                    p=subprocess.run(['nvidia-smi','--query-gpu=timestamp,name,memory.used,utilization.gpu,power.draw',
                                      '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
                    append(self.path,{'time_utc':datetime.now(timezone.utc).isoformat(),'sample':p.stdout.strip(),'returncode':p.returncode})
                except Exception as exc:append(self.path,{'monitor_error_type':type(exc).__name__})
                self.stop_event.wait(1)
        self.thread=threading.Thread(target=loop,daemon=True);self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=6)

def weight_sample(model):
    h=hashlib.sha256()
    for name,p in model.named_parameters():
        h.update(name.encode());h.update(p.detach().reshape(-1)[:32].contiguous().view(__import__('torch').uint8).cpu().numpy().tobytes())
    return h.hexdigest()

def inference_trajectory(model,tokenizer,row,config,seed,condition):
    import torch
    from transformers import set_seed
    from jsonschema import Draft202012Validator
    set_seed(seed)
    env=WorkplaceEnv();messages=deepcopy(row['responses_create_params']['input'])
    if condition=='B1':messages[0]['content']+='\n\n'+config['B1_addition']
    schemas=deepcopy(row['responses_create_params']['tools'])
    validators={s['name']:Draft202012Validator(s['parameters']) for s in schemas}
    initial_messages=deepcopy(messages)
    result={'task_id':row['id'],'task_uid':row['task_uid'],'source_pool':'development',
            'condition':condition,'seed':seed,'producer':'Qwen/Qwen3-8B_REAL_MODEL',
            'model_revision':config['model_revision'],'initial_messages':initial_messages,'tool_schemas':schemas,
            'rounds':[],'call_diagnostics':[],'parse_errors':[],'infra_invalid':False,
            'input_tokens':0,'output_tokens':0,'initial_state_sha256':digest(env.initial_state),
            'initial_state_artifact':'initial_state.json','training_eligible':False}
    torch.cuda.reset_peak_memory_stats();started=time.perf_counter();termination='round_limit'
    known_call_history=[]
    try:
        for turn in range(1,config['max_model_rounds']+1):
            if time.perf_counter()-started>180:
                termination='trajectory_wall_limit';break
            prompt=tokenizer.apply_chat_template(messages,tools=schemas,tokenize=False,
                     add_generation_prompt=True,enable_thinking=False)
            encoded=tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda')
            input_count=encoded['input_ids'].shape[1]
            remaining=config['max_output_tokens_per_trajectory']-result['output_tokens']
            context_remaining=config['max_context_tokens']-input_count
            if context_remaining<=0:
                result['context_limit_attempt']={'turn':turn,'input_tokens':input_count,
                                                 'max_context_tokens':config['max_context_tokens']}
                termination='context_limit';break
            if remaining<=0:
                termination='trajectory_output_limit';break
            cap=min(config['max_output_tokens_per_model_call'],remaining,context_remaining)
            visible_text=json.dumps([m for m in messages if m['role'] in ('user','tool')],ensure_ascii=False)
            eos_ids=model.generation_config.eos_token_id
            eos_set=set(eos_ids if isinstance(eos_ids,list) else [eos_ids])
            call_started=time.perf_counter();torch.cuda.synchronize()
            with torch.inference_mode():
                generated=model.generate(**encoded,max_new_tokens=cap,do_sample=True,
                    temperature=config['temperature'],top_p=config['top_p'],top_k=0,
                    repetition_penalty=1.0,use_cache=True,max_time=90,
                    pad_token_id=tokenizer.pad_token_id,eos_token_id=eos_ids)
            torch.cuda.synchronize();elapsed=time.perf_counter()-call_started
            ids=generated[0,input_count:].tolist()
            raw=tokenizer.decode(ids,skip_special_tokens=False)
            ended=bool(ids and ids[-1] in eos_set)
            round_record={'turn':turn,'input_tokens':input_count,'output_tokens':len(ids),'output_token_ids':ids,
                          'raw_generation':raw,'input_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                          'model_latency_seconds':elapsed,'output_cap':cap,'eos_reached':ended,
                          'input_messages':deepcopy(messages)}
            result['rounds'].append(round_record);result['input_tokens']+=input_count;result['output_tokens']+=len(ids)
            calls,parse_errors,content=parse_tool_calls(raw)
            if not ended:
                # Keep incomplete output for attribution; never execute truncated generations.
                messages.append({'role':'assistant','content':raw})
                result['parse_errors'].extend({'turn':turn,**e} for e in parse_errors)
                termination='generation_incomplete';break
            result['parse_errors'].extend({'turn':turn,**e} for e in parse_errors)
            assistant={'role':'assistant','content':content}
            if calls:
                assistant['tool_calls']=[{'id':f't{turn}_c{i}','type':'function',
                    'function':{'name':c['name'],'arguments':c['parsed_arguments']}} for i,c in enumerate(calls)]
            messages.append(assistant)
            if not calls and not parse_errors:
                termination='assistant_final';break
            for index,call in enumerate(calls):
                name=call['name'];args=call['parsed_arguments']
                schema_errors=[] if name not in validators else [e.message for e in validators[name].iter_errors(args)]
                before=snapshot(env.tools)
                repeat=any(h['name']==name and h['arguments']==canonical(args) and h['state']==digest(before)
                           for h in known_call_history)
                loop=False
                if len(known_call_history)>=2:
                    loop=all(h['name']==name and h['arguments']==canonical(args) and h['state']==digest(before)
                             for h in known_call_history[-2:])
                known_call_history.append({'name':name,'arguments':canonical(args),'state':digest(before)})
                # Diagnostic validation does not rewrite official kwargs/return semantics.
                event=env.step({'name':name,'arguments':call['arguments']})
                finding={'turn':turn,'call_index':index,'step':event['step'],'name':name,'arguments':args,
                         'known_tool':name in validators,'schema_errors':schema_errors,
                         'executable_gate':name in validators and not schema_errors and event['exception'] is None,
                         'identifiers':identifier_candidates(args,visible_text),
                         'same_call_same_state_before':repeat,'three_call_loop':loop,
                         'tool_exception':event['exception']}
                result['call_diagnostics'].append(finding)
                messages.append({'role':'tool','tool_call_id':f't{turn}_c{index}',
                                 'content':json.dumps(event['observation'],ensure_ascii=False,default=str)})
            if parse_errors:
                messages.append({'role':'user','content':'Environment parser feedback: invalid tool-call JSON or delimiters. '
                                 'Only successfully parsed calls were executed. Use the documented tool-call format.'})
            del encoded,generated
    except torch.cuda.OutOfMemoryError:
        result['infra_invalid']=True;result['infra_failure_kind']='cuda_oom';termination='infra_failure'
        torch.cuda.empty_cache()
    except Exception as exc:
        result['infra_invalid']=True;result['infra_failure_kind']=type(exc).__name__;termination='infra_failure'
        result['infra_traceback']=traceback.format_exc()
    try:
        result['verifier']=env.verify(row['ground_truth'])
        capture=io.StringIO()
        with redirect_stdout(capture):
            replay=execute_actions_and_reset_state([e['tool_call'] for e in env.events])
        result['online_replay_equal']=snapshot(replay)==snapshot(env.tools)
        if not result['online_replay_equal']:
            result['infra_invalid']=True;result['infra_failure_kind']='online_replay_mismatch'
    except Exception as exc:
        result['verifier']={'official_reward':None,'error_type':type(exc).__name__}
        result['infra_invalid']=True;result['infra_failure_kind']='verifier_exception'
    result.update({'messages':messages,'events':env.events,'termination':termination,
                   'reference_action_count':len(row['ground_truth']),
                   'reference':row['ground_truth'],'final_state_sha256':digest(snapshot(env.tools)),
                   'tool_steps':len(env.events),'model_rounds':len(result['rounds']),
                   'trajectory_latency_seconds':time.perf_counter()-started,
                   'peak_torch_allocated_bytes':torch.cuda.max_memory_allocated(),
                   'peak_torch_reserved_bytes':torch.cuda.max_memory_reserved()})
    return result

def summarize(records):
    valid=[r for r in records if not r['infra_invalid']]
    calls=[c for r in valid for c in r['call_diagnostics']]
    parse_errors=sum(len(r['parse_errors']) for r in valid)
    ids=[c for c in calls if c['identifiers']]
    count=len(valid)
    return {'attempted_rollouts':len(records),'valid_rollouts':count,'infra_invalid_rollouts':len(records)-count,
            'verified_successes':sum(r['verifier']['official_reward']==1 for r in valid),
            'success_rate':sum(r['verifier']['official_reward']==1 for r in valid)/count if count else None,
            'strata':{s:{'n':len(rows),'successes':sum(r['verifier']['official_reward']==1 for r in rows)}
                      for s,rows in [('nonempty_reference',[r for r in valid if r['reference_action_count']]),
                                     ('empty_reference',[r for r in valid if not r['reference_action_count']])]},
            'tool_calls':len(calls),'parse_error_attempts':parse_errors,
            'executable_tool_calls':sum(c['executable_gate'] for c in calls),
            'executable_tool_call_rate':sum(c['executable_gate'] for c in calls)/(len(calls)+parse_errors) if len(calls)+parse_errors else None,
            'unknown_tool_calls':sum(not c['known_tool'] for c in calls),
            'schema_invalid_calls':sum(bool(c['schema_errors']) for c in calls),
            'identifier_bearing_calls':len(ids),
            'ungrounded_identifier_candidate_calls':sum(any(not x['observed_in_policy_context'] for x in c['identifiers']) for c in ids),
            'repeated_same_state_call_candidates':sum(c['same_call_same_state_before'] for c in calls),
            'retry_loop_trajectories':sum(any(c['three_call_loop'] for c in r['call_diagnostics']) for r in valid),
            'premature_termination_candidates':sum(r['termination']=='assistant_final' and r['verifier']['official_reward']==0 for r in valid),
            'termination_counts':dict(Counter(r['termination'] for r in records)),
            'input_tokens':sum(r['input_tokens'] for r in records),'output_tokens':sum(r['output_tokens'] for r in records),
            'average_tool_steps':sum(r['tool_steps'] for r in valid)/count if count else None,
            'average_trajectory_seconds':sum(r['trajectory_latency_seconds'] for r in valid)/count if count else None,
            'peak_torch_allocated_gib':max((r['peak_torch_allocated_bytes'] for r in records),default=0)/2**30,
            'candidate_metrics_require_semantic_review':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--condition',choices=['SMOKE','B0','B1'],required=True)
    p.add_argument('--hourly-rmb',type=float,required=True);p.add_argument('--cost-cap-rmb',type=float,default=30)
    p.add_argument('--max-wall-seconds',type=int,default=3600);args=p.parse_args()
    if args.hourly_rmb<=0 or args.max_wall_seconds*args.hourly_rmb/3600>args.cost_cap_rmb:
        raise ValueError('Wall-time envelope exceeds supplied cost approval')
    out=ROOT/'experiments'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    config=json.loads((ROOT/'configs/model_qualification_plan.json').read_text())
    config.update({'condition':args.condition,'backend':'transformers','torch_dtype':'bfloat16','attention':'sdpa',
        'hourly_rmb':args.hourly_rmb,'cost_cap_rmb':args.cost_cap_rmb,'max_wall_seconds':args.max_wall_seconds,
        'Cost Bound':f'{args.max_wall_seconds/3600:.2f} GPU-h x RMB {args.hourly_rmb}/h; cap RMB {args.cost_cap_rmb}',
        'B1_trigger':'B0 >=46 valid; nonempty-reference success below 80%; at least 3 tasks with reviewed policy failures; no unresolved systemic infrastructure fault',
        'native_parallel_call_handling':'All well-formed calls in a model turn execute sequentially; no automatic name/argument repair',
        'generation_top_k':0,'generation_repetition_penalty':1.0,'trajectory_wall_seconds':180,'model_call_wall_seconds':90})
    config['hourly_rate_source']='User-confirmed exact instance price in this Day 3 session (2026-09-04)'
    if args.condition=='SMOKE':
        config['Research Question']='Can this single GPU load the fixed BF16 policy and complete a real tool/observation/verifier loop?'
        config['Hypothesis']='The 8B policy fits with 8K context and produces auditable real tool interactions on three fixed dev tasks'
        config['Evidence Gate']='Model loads, logs are complete, at least one real tool interaction, and no systemic infrastructure failure'
    elif args.condition=='B1':
        config['Research Question']='Does the preregistered general prompt improve the same 24 tasks relative to paired B0 seed 42?'
        config['Hypothesis']='General grounding/completion instructions reduce reviewed policy failures without task-specific workflows'
        config['Independent Variable']='Only the preregistered B1 general instruction; same policy weights and seed 42'
    write(out/'config.json',config)
    build=json.loads((ROOT/'bundle_manifest.json').read_text())
    integrity=json.loads((ROOT/'model_integrity.json').read_text())
    if integrity['revision']!=config['model_revision'] or not integrity['all_match']:
        raise RuntimeError('Pinned model weight integrity has not passed')
    packages={}
    for name in ('torch','transformers','accelerate','tokenizers','pandas','numpy','jsonschema'):
        packages[name]=importlib.metadata.version(name)
    identity={'experiment_id':args.run_id,'started_at':datetime.now(timezone.utc).isoformat(),
              'code_commit':build['code_commit'],'bundle_manifest':build,'model_revision':config['model_revision'],
              'seeds':[42] if args.condition!='B0' else config['seeds'],'packages':packages,
              'kind':'REAL_MODEL_GPU_QUALIFICATION_NO_PARAMETER_UPDATE','weights_manifest':'model_integrity.json',
              'weights_manifest_sha256':hashlib.sha256((ROOT/'model_integrity.json').read_bytes()).hexdigest()}
    write(out/'identity.json',identity)
    if not (ROOT/'experiments').exists():(ROOT/'experiments').mkdir()
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started','identity':identity})
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start();records=[];start=time.perf_counter()
    try:
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
        load_start=time.perf_counter()
        model_path=ROOT/'models/Qwen3-8B'
        tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,dtype=torch.bfloat16,
                   device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        model.eval();model.requires_grad_(False)
        sampled_before=weight_sample(model)
        identity.update({'load_seconds':time.perf_counter()-load_start,'parameter_count':sum(p.numel() for p in model.parameters()),
                         'trainable_parameter_count':sum(p.numel() for p in model.parameters() if p.requires_grad),
                         'device':torch.cuda.get_device_name(0),'sampled_weights_before':sampled_before,'adapters':[]})
        write(out/'identity.json',identity)
        rows=[json.loads(x) for x in (ROOT/'data/day3_dev24.jsonl').read_text().splitlines() if x.strip()]
        if args.condition=='SMOKE':rows=[r for r in rows if r['id'] in (0,1,205)]
        write(out/'initial_state.json',WorkplaceEnv().initial_state)
        for seed in identity['seeds']:
            for row in rows:
                if time.perf_counter()-start+180>args.max_wall_seconds:
                    raise TimeoutError('Run wall-time envelope reached before next trajectory')
                record=inference_trajectory(model,tokenizer,row,config,seed,'B1' if args.condition=='B1' else 'B0')
                records.append(record);append(out/'trajectories.jsonl',record)
                progress=summarize(records);write(out/'progress.json',progress)
                print(json.dumps({'task_id':row['id'],'seed':seed,'reward':record['verifier']['official_reward'],
                                  'termination':record['termination'],'tokens':record['output_tokens'],
                                  'steps':record['tool_steps'],'completed':len(records),'infra_invalid':record['infra_invalid']}),flush=True)
                if record['infra_invalid']:raise RuntimeError('Infrastructure-invalid trajectory; stop to diagnose')
        result=summarize(records);result['sampled_weights_unchanged']=sampled_before==weight_sample(model)
        result['run_wall_seconds']=time.perf_counter()-start;result['gpu_hours']=result['run_wall_seconds']/3600
        result['cost_estimate_rmb']=result['gpu_hours']*args.hourly_rmb
        result['cost_per_verified_success']=result['cost_estimate_rmb']/result['verified_successes'] if result['verified_successes'] else None
        result['cost_scope']='Run wall time including model load; excludes earlier instance uptime/download/install/storage'
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps({'event':'RUN_COMPLETED','result':result}),flush=True)
    except Exception as exc:
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),
             'wall_seconds':time.perf_counter()-start,'preserved_trajectories':len(records),
             'classification':'RUN_INCOMPLETE_OR_INFRA_INVALID; retain any individually valid trajectory records'})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete','error_type':type(exc).__name__})
        raise
    finally:monitor.stop()

if __name__=='__main__':main()
