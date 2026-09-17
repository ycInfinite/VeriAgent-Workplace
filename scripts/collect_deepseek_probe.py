"""One fixed20 qualification; hidden remote key, no retry, no scheduler/training."""
import argparse
from datetime import datetime,timezone
import getpass
import hashlib
import importlib.metadata
import json
import os
import sys
import threading
import time
import warnings

from run_day3 import ROOT,write,append
from collect_training_probe import validate_inputs
from veriagent.teacher_data import teacher_request,CanonicalTeacherEncoder
from veriagent.teacher_rollout import teacher_trajectory
from veriagent.deepseek_teacher import DeepSeekTransport,request_body,validate_response,estimated_cost,endpoint
from veriagent.environment import WorkplaceEnv,digest


def preflight(config, deployed=True):
    required=['Research Question','Hypothesis','Independent Variable','Controlled Variables',
              'Metrics','Evidence Gate','Cost Bound','Failure Branch']
    assert all(config.get(k) for k in required)
    expected={'model':'deepseek-flash','enable_thinking':False,'max_tasks':20,'max_requests':120,
              'max_model_rounds':6,'max_context_tokens':8192,'max_output_tokens_per_model_call':768,
              'max_output_tokens_per_trajectory':2048,'max_wall_seconds':1800,'retries':0,'seed':None}
    assert all(config.get(k)==v for k,v in expected.items()),'Scope mismatch'
    endpoint(config['base_url'])
    cohort=json.loads((ROOT/config['cohort_manifest']).read_text(encoding='utf-8'))
    rows=[json.loads(l) for l in (ROOT/config['data_path']).read_text(encoding='utf-8').splitlines() if l.strip()]
    validate_inputs(config,cohort,rows)
    assert [r['task_uid'] for r in rows]==[t['task_uid'] for t in cohort['tasks']], 'Fixed order mismatch'
    tasks={t['task_uid']:t for t in cohort['tasks']}
    encoder=CanonicalTeacherEncoder(8192)
    assert encoder.checked.model_revision==config['student_revision']
    coverage=[]
    for row in rows:
        r=teacher_request(row,tasks[row['task_uid']],cohort['B1_addition'])
        text=encoder.inspector.render(r['messages'],r['tools'],generate=True)
        n=len(encoder.inspector.tokenizer.encode(text,add_special_tokens=False).ids)
        coverage.append({'task_id':row['id'],'student_initial_tokens':n,'fits':n<8192})
    assert all(x['fits'] for x in coverage),'Coverage failed; no truncation'
    build=None
    if deployed:
        build=json.loads((ROOT/'bundle_manifest.json').read_text())
        entries={e['path']:e for e in build['files']}
        for p in ['veriagent/deepseek_teacher.py','veriagent/teacher_rollout.py',
                  'scripts/collect_deepseek_probe.py','configs/deepseek_acquisition_plan.json']:
            assert p in entries,'Missing deployed execution file'
        for entry in entries.values():
            p=(ROOT/entry['path']).resolve()
            assert p.is_relative_to(ROOT)
            assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],'Deployment hash mismatch'
        assert build.get('code_transport')=='GitHub fixed-ref temporary raw-file downloads'
    return build,cohort,rows,tasks,coverage


def summarize(records, responses):
    valid=[r for r in records if not r['infra_invalid']]
    calls=[c for r in valid for c in r['call_diagnostics']]
    costs=[]
    for response,stamp in responses:
        try:costs.append(estimated_cost(response,stamp))
        except Exception:pass
    attempts=sum(r['api_attempts'] for r in records)
    return {'attempted_rollouts':len(records),'valid_rollouts':len(valid),
            'infra_invalid_rollouts':len(records)-len(valid),
            'verified_successes':sum(r['verifier']['official_reward']==1 for r in valid),
            'success_rate':sum(r['verifier']['official_reward']==1 for r in valid)/len(valid) if valid else None,
            'tool_calls':len(calls),'executable_tool_calls':sum(c['executable_gate'] for c in calls),
            'api_attempts':attempts,'captured_responses':len(responses),
            'requests_with_unknown_usage_or_cost':attempts-len(costs),
            'known_usage_estimated_rmb':sum(c['estimated_rmb'] for c in costs),
            'total_model_cost_estimate_rmb':sum(c['estimated_rmb'] for c in costs) if attempts==len(costs) else None,
            'provider_input_tokens':sum(c['input_tokens'] for c in costs),
            'provider_output_tokens':sum(c['output_tokens'] for c in costs),
            'cache_hit_tokens':sum(c['cache_hit_tokens'] for c in costs),
            'cache_miss_tokens':sum(c['cache_miss_tokens'] for c in costs),
            'cost_caveat':'Official tariff at local response time; not invoice; CPU/storage excluded',
            'training_approved_trajectories':0,'parameter_updates':0,'gpu_hours':0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--prompt-key',action='store_true')
    args=parser.parse_args()
    config=json.loads((ROOT/'configs/deepseek_acquisition_plan.json').read_text())
    build,cohort,rows,tasks,coverage=preflight(config)
    print(json.dumps({'status':'PREFLIGHT_PASSED','tasks':len(rows),'coverage':coverage,
                      'code_commit':build['code_commit']}),flush=True)
    if args.preflight_only:return
    if os.name!='posix' or not sys.stdin.isatty() or not args.prompt_key:
        raise RuntimeError('Use hidden credential input in the remote Linux terminal')
    out=ROOT/'experiments'/config['experiment_id']
    out.mkdir(parents=True,exist_ok=False)
    write(out/'config.json',config);write(out/'coverage.json',coverage)
    write(out/'initial_state.json',WorkplaceEnv().initial_state)
    identity={'experiment_id':config['experiment_id'],'code_commit':build['code_commit'],
              'deployment':build,'started_at':datetime.now(timezone.utc).isoformat(),
              'requested_model':'deepseek-flash','documented_model_version':'DeepSeek-V4.1-Flash',
              'model_revision':None,'seed':None,'seed_note':'No provider seed parameter sent',
              'source_pool':'training_candidate','task_ids':[r['id'] for r in rows],
              'cohort_sha256':hashlib.sha256((ROOT/config['cohort_manifest']).read_bytes()).hexdigest(),
              'data_sha256':hashlib.sha256((ROOT/config['data_path']).read_bytes()).hexdigest(),
              'student_revision':config['student_revision'],'credential_persisted':False,
              'packages':{n:importlib.metadata.version(n) for n in ['pandas','numpy','tokenizers','jsonschema']}}
    write(out/'identity.json',identity)
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'started','identity':identity})
    records=[];responses=[];started=time.monotonic();timer=None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            os.environ[config['api_key_environment']]=getpass.getpass('DeepSeek API key (hidden; remote process only): ')
        transport=DeepSeekTransport(config)
        started=time.monotonic()
        def deadline():
            write(out/'deadline.json',{'status':'PROCESS_DEADLINE','inflight_charge_unknown':True,
                                     'completed_trajectories':len(records)})
            os._exit(124)
        timer=threading.Timer(1800,deadline);timer.daemon=True;timer.start()
        request_count=0
        def sink(event):
            nonlocal request_count
            stamp=datetime.now(timezone.utc).isoformat()
            append(out/'api_events.jsonl',{**event,'observed_at':stamp})
            if event['event']=='request_started':
                request_count+=1
                if request_count>120:raise RuntimeError('Request bound exceeded')
            if event['event']=='response':responses.append((event['body'],stamp))
        for row in rows:
            record=teacher_trajectory(row,tasks[row['task_uid']],cohort,config,transport,
                lambda:1800-(time.monotonic()-started),sink,producer='DEEPSEEK_REAL_API',
                body_builder=request_body,response_validator=validate_response)
            record['experiment_id']=config['experiment_id']
            records.append(record);append(out/'trajectories.jsonl',record)
            write(out/'progress.json',summarize(records,responses))
            print(json.dumps({'completed':len(records),'task_id':row['id'],
                              'reward':record['verifier']['official_reward'],
                              'termination':record['termination'],'infra_invalid':record['infra_invalid']}),flush=True)
            if record['infra_invalid']:raise RuntimeError('Infrastructure/contract failure; no retry')
        result={**summarize(records,responses),'status':'ACQUIRED_REQUIRES_FULL_QUALITY_REVIEW',
                'wall_seconds':time.monotonic()-started}
        write(out/'result.json',result)
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'completed'})
        print(json.dumps(result),flush=True)
    except Exception as exc:
        write(out/'result.json',{**summarize(records,responses),'status':'INCOMPLETE_REQUIRES_REVIEW',
                               'error_type':type(exc).__name__,'wall_seconds':time.monotonic()-started})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'invalid_or_incomplete'})
        raise
    finally:
        if timer:timer.cancel()
        os.environ.pop(config['api_key_environment'],None)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'STOPPED','error_type':type(exc).__name__,'details':'Sensitive diagnostics suppressed; no retry'}),flush=True)
        raise SystemExit(1)
