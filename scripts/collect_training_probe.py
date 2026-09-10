"""Bounded real-policy acquisition on a fixed training-only cohort; no training."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
import threading
import time
import traceback

from run_day3 import ROOT, Monitor, append, write, weight_sample, inference_trajectory, summarize
from veriagent.environment import WorkplaceEnv
from veriagent.sft_data import content_sha256


def validate_inputs(config, cohort, rows):
    expected = {x['task_uid']: x for x in cohort['tasks']}
    if len(rows) != config['max_tasks'] or len(expected) != len(rows):
        raise ValueError('Fixed cohort count mismatch')
    if {x['task_uid'] for x in rows} != set(expected):
        raise ValueError('Fixed cohort membership mismatch')
    for row in rows:
        meta = expected[row['task_uid']]
        if meta['pool'] != 'training_candidate' or row['source_pool'] != 'training_candidate':
            raise ValueError('Non-training task in acquisition input')
        if row['id'] != meta['source_id']:
            raise ValueError('Task source ID mismatch')
        messages = deepcopy(row['responses_create_params']['input'])
        messages[0]['content'] += '\n\n' + cohort['B1_addition']
        if content_sha256(messages) != meta['initial_messages_sha256']:
            raise ValueError('Task/prompt content mismatch')
        if content_sha256(row['responses_create_params']['tools']) != meta['tool_schemas_sha256']:
            raise ValueError('Tool schema mismatch')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--hourly-rmb', type=float, required=True)
    args = parser.parse_args()
    config = json.loads((ROOT/'configs/sft_acquisition_plan.json').read_text())
    if not math.isfinite(args.hourly_rmb) or args.hourly_rmb <= 0:
        raise ValueError('A finite, positive actual hourly price is required')
    envelope = config['max_wall_seconds'] * args.hourly_rmb / 3600
    if envelope > config['cost_cap_rmb'] or config['cost_cap_rmb'] > 30:
        raise ValueError('Process estimate exceeds RMB 30; do not launch automatically')
    cohort = json.loads((ROOT/config['cohort_manifest']).read_text())
    rows = [json.loads(x) for x in (ROOT/config['data_path']).read_text().splitlines() if x.strip()]
    validate_inputs(config, cohort, rows)
    build = json.loads((ROOT/'bundle_manifest.json').read_text())
    for entry in build['files']:
        if hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Uploaded bundle content mismatch: '+entry['path'])
    integrity = json.loads((ROOT/'model_integrity.json').read_text())
    if integrity.get('revision') != config['model_revision'] or not integrity.get('all_match'):
        raise ValueError('Fixed weight integrity gate missing')
    out = ROOT/'experiments'/args.run_id
    out.mkdir(parents=True, exist_ok=False)
    config.update({'hourly_rmb':args.hourly_rmb, 'process_cost_envelope_rmb':envelope,
                   'B1_addition':cohort['B1_addition'], 'status':'RUNNING'})
    write(out/'config.json', config)
    identity = {'experiment_id':args.run_id, 'started_at':datetime.now(timezone.utc).isoformat(),
        'kind':'REAL_MODEL_TRAINING_DATA_ACQUISITION_NO_PARAMETER_UPDATE',
        'code_commit':build['code_commit'], 'bundle_manifest':build,
        'model_revision':config['model_revision'], 'seed':config['seed'],
        'cohort_sha256':hashlib.sha256((ROOT/config['cohort_manifest']).read_bytes()).hexdigest(),
        'weights_manifest_sha256':hashlib.sha256((ROOT/'model_integrity.json').read_bytes()).hexdigest(),
        'packages':{x:importlib.metadata.version(x) for x in
                    ('torch','transformers','tokenizers','pandas','numpy','jsonschema')}}
    write(out/'identity.json',identity)
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started','identity':identity})
    records=[]; started=time.perf_counter()
    def deadline():
        write(out/'deadline.json',{'status':'PROCESS_DEADLINE_REACHED',
            'max_wall_seconds':config['max_wall_seconds'],'retained_rollouts':len(records),
            'note':'Process exits and releases GPU; provider billing requires separate instance shutdown'})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'deadline_incomplete'})
        os._exit(124)
    timer=threading.Timer(config['max_wall_seconds'],deadline);timer.daemon=True;timer.start()
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start()
    try:
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        if torch.cuda.device_count()!=1:
            raise ValueError('Expose exactly one GPU')
        path=ROOT/config['weights_path']
        tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.bfloat16,
            device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        model.eval();model.requires_grad_(False)
        before=weight_sample(model)
        identity.update({'gpu':torch.cuda.get_device_name(0),'sampled_weights_before':before,
            'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad)})
        write(out/'identity.json',identity)
        write(out/'initial_state.json',WorkplaceEnv().initial_state)
        for row in rows:
            if time.perf_counter()-started+300 > config['max_wall_seconds']:
                raise TimeoutError('Insufficient remaining process envelope for another rollout')
            record=inference_trajectory(model,tokenizer,row,config,config['seed'],'B1',source_pool='training_candidate')
            record.update({'experiment_id':args.run_id,'experiment_phase':'SFT_TRAINING_DATA_ACQUISITION'})
            records.append(record);append(out/'trajectories.jsonl',record)
            write(out/'progress.json',summarize(records))
            print(json.dumps({'task_id':row['id'],'completed':len(records),
                'reward':record['verifier']['official_reward'],'termination':record['termination']}),flush=True)
            if record['infra_invalid']:
                raise RuntimeError('Infrastructure-invalid rollout; stop for review')
        result=summarize(records)
        result.update({'status':'ACQUIRED_REQUIRES_EXPLICIT_QUALITY_REVIEW',
            'sampled_weights_unchanged':before==weight_sample(model),'parameter_updates':0,
            'wall_seconds':time.perf_counter()-started,'training_approved_trajectories':0})
        if not result['sampled_weights_unchanged']:
            raise RuntimeError('Policy sample changed during inference-only acquisition')
        result['gpu_hours']=result['wall_seconds']/3600
        result['cost_estimate_rmb']=result['gpu_hours']*args.hourly_rmb
        result['cost_scope']='Process wall only; excludes preparation, idle uptime and storage'
        write(out/'result.json',result)
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps(result,indent=2),flush=True)
    except Exception as exc:
        wall=time.perf_counter()-started
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),
            'retained_rollouts':len(records),'wall_seconds':wall,'cost_estimate_rmb':wall/3600*args.hourly_rmb})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete'})
        raise
    finally:
        timer.cancel();monitor.stop()


if __name__=='__main__':
    main()
