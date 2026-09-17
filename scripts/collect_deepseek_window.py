"""One-shot, CPU-only teacher collection. Secret exists only in remote process memory.

The arm command forks once, detaches from SSH, then waits for the frozen UTC
window. No cron, retries, training, automatic data admission or resume.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
import signal
import sys
import threading
import time
import warnings

from run_day3 import ROOT, append, write
from collect_deepseek_probe import summarize
from veriagent.deepseek_teacher import DeepSeekTransport, endpoint, request_body, validate_response
from veriagent.environment import WorkplaceEnv
from veriagent.teacher_data import CanonicalTeacherEncoder, teacher_request
from veriagent.teacher_rollout import APIError, teacher_trajectory

CONFIG = 'configs/deepseek_window_acquisition.json'


def utcnow():
    return datetime.now(timezone.utc)


def window(config, now=None):
    now = now or utcnow()
    start = datetime.fromisoformat(config['start_at_utc'])
    end = datetime.fromisoformat(config['stop_at_utc'])
    assert start.tzinfo and end.tzinfo and (end-start).total_seconds() == 7200
    return (start-now).total_seconds(), (end-now).total_seconds()


def atomic_write(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    write(temp, value)
    os.replace(temp, path)


def preflight(config, deployed=True):
    for name in ['Research Question','Hypothesis','Independent Variable','Controlled Variables',
                 'Metrics','Evidence Gate','Cost Bound','Failure Branch']:
        assert config.get(name)
    expected = {'experiment_id':'DEEPSEEK-SFTDATA-20260917-001', 'model':'deepseek-flash',
                'enable_thinking':False,'max_tasks':723,'max_requests':4338,
                'max_model_rounds':6,'max_context_tokens':8192,'max_output_tokens_per_model_call':768,
                'max_output_tokens_per_trajectory':2048,'retries':0,'seed':None,
                'start_at_utc':'2026-09-17T04:00:00+00:00','stop_at_utc':'2026-09-17T06:00:00+00:00'}
    assert all(config.get(k)==v for k,v in expected.items()), 'Frozen scope mismatch'
    endpoint(config['base_url'])
    for path, sha in config['payload_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha, 'Payload changed'
    cohort = json.loads((ROOT/config['cohort_manifest']).read_text(encoding='utf-8'))
    bank = json.loads((ROOT/config['schema_path']).read_text(encoding='utf-8'))
    packed = [json.loads(l) for l in (ROOT/config['data_path']).read_text(encoding='utf-8').splitlines() if l.strip()]
    rows=[]
    for p in packed:
        row=deepcopy(p)
        row['responses_create_params']['tools']=bank[row.pop('tool_schema_ref')]
        rows.append(row)
    assert cohort['training_pool_total']==743 and len(cohort['excluded_task_uids'])==20
    assert len(rows)==723 and len({r['task_uid'] for r in rows})==723
    assert [r['task_uid'] for r in rows]==[t['task_uid'] for t in cohort['tasks']]
    assert not set(cohort['excluded_task_uids']) & {r['task_uid'] for r in rows}
    tasks={t['task_uid']:t for t in cohort['tasks']}
    encoder=CanonicalTeacherEncoder(8192)
    assert encoder.checked.model_revision==config['student_revision']
    coverage=[]
    for row in rows:
        task=tasks[row['task_uid']]
        assert task['pool']=='training_candidate' and task['source_split']=='train'
        req=teacher_request(row,task,cohort['B1_addition'])
        prompt=encoder.inspector.render(req['messages'],req['tools'],generate=True)
        n=len(encoder.inspector.tokenizer.encode(prompt,add_special_tokens=False).ids)
        assert n==task['initial_input_tokens'] and n<8192
        assert hashlib.sha256(prompt.encode()).hexdigest()==task['initial_prompt_sha256']
        coverage.append({'task_id':row['id'],'tokens':n,'fits':True})
    build=None
    if deployed:
        build=json.loads((ROOT/'bundle_manifest.json').read_text())
        entries={e['path']:e for e in build['files']}
        assert all(p in entries for p in [CONFIG,'scripts/collect_deepseek_window.py',*config['payload_sha256']])
        for entry in entries.values():
            path=(ROOT/entry['path']).resolve()
            assert path.is_relative_to(ROOT) and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        assert build['code_transport']=='GitHub fixed-ref temporary raw-file downloads'
    return build,cohort,rows,tasks,coverage


def run_worker(config, build, cohort, rows, tasks, out):
    records=[];responses=[];request_count=0;active=None;timer=None
    armed=utcnow().isoformat();started=None
    key_env=config['api_key_environment']
    progress_lock=threading.RLock()

    def calculate_status(status, error_type=None, inflight_unknown=False):
        completed={r['task_uid'] for r in records}
        result={**summarize(records,responses),'status':status,'armed_at':armed,
                'started_at':started,'observed_at':utcnow().isoformat(),
                'request_events':request_count,'active_task_uid':active,
                'inflight_charge_unknown':inflight_unknown,
                'requests_without_captured_response':request_count-len(responses),
                'error_type':error_type,'source_task_count':723}
        if inflight_unknown or request_count != len(responses):
            result['total_model_cost_estimate_rmb']=None
        atomic_write(out/'progress.json',result)
        atomic_write(out/'remaining.json',{'never_attempted':[r['task_uid'] for r in rows
            if r['task_uid'] not in completed and r['task_uid']!=active],
            'incomplete_active_task':active if active not in completed else None,
            'automatic_resume_allowed':False})
        return result

    def persist(status,error_type=None,inflight_unknown=False):
        with progress_lock:
            return calculate_status(status,error_type,inflight_unknown)

    def deadline():
        # If a request is in flight the raw request event survives; never hide its cost.
        value=persist('WINDOW_DEADLINE',inflight_unknown=request_count!=len(responses))
        write(out/'deadline.json',value)
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'window_deadline'})
        os.environ.pop(key_env,None)
        os._exit(124)

    try:
        DeepSeekTransport(config)  # Local credential validation only, no network.
        atomic_write(out/'armed.json',{'status':'ARMED_WAITING','pid':os.getpid(),'armed_at':armed,
            'start_at_utc':config['start_at_utc'],'stop_at_utc':config['stop_at_utc'],
            'code_commit':build['code_commit'],'model_calls_before_start':0,'credential_persisted':False})
        persist('ARMED_WAITING')
        timer=threading.Timer(max(0,window(config)[1]),deadline);timer.daemon=True;timer.start()
        while window(config)[0]>0:
            time.sleep(max(0,min(30,window(config)[0])))
        # Deployment must stay identical while this process is waiting.
        current=json.loads((ROOT/CONFIG).read_text())
        assert current==config
        for entry in build['files']:
            assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256']
        if window(config)[1]<=1:raise APIError('window_expired')
        started=utcnow().isoformat()
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'started','at':started})
        base_transport=DeepSeekTransport(config)

        def transport(body, timeout):
            before,remaining=window(config)
            if before>0 or remaining<=1:raise APIError('outside_authorized_window')
            return base_transport(body,min(timeout,remaining))

        def sink(event):
            nonlocal request_count
            stamp=utcnow().isoformat()
            if event['event']=='request_started':
                before,remaining=window(config)
                if before>0 or remaining<=1:raise APIError('outside_authorized_window')
                if request_count>=config['max_requests']:raise APIError('request_bound')
                request_count+=1
            append(out/'api_events.jsonl',{**event,'observed_at':stamp})
            if event['event']=='response':
                responses.append(({'usage':event['body'].get('usage',{})},stamp))

        for row in rows:
            if window(config)[1]<=1:break
            active=row['task_uid'];persist('RUNNING')
            record=teacher_trajectory(row,tasks[active],cohort,config,transport,
                lambda:window(config)[1],sink,producer='DEEPSEEK_REAL_API',
                body_builder=request_body,response_validator=validate_response)
            record.update({'experiment_id':config['experiment_id'],
                'empty_reference_requires_semantic_review':tasks[active]['reference_action_count']==0})
            append(out/'trajectories.jsonl',record)
            # Keep only statistics in memory; full raw evidence is append-only on disk.
            records.append({k:record[k] for k in ['task_uid','infra_invalid','call_diagnostics','verifier','api_attempts']})
            active=None
            persist('RUNNING')
            if record['infra_invalid']:raise APIError('infrastructure_or_contract_failure')
        status='ACQUIRED_REQUIRES_FULL_QUALITY_REVIEW' if len(records)==723 else 'WINDOW_ENDED_PARTIAL'
        value=persist(status)
        atomic_write(out/'result.json',value)
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':status})
    except Exception as exc:
        value=persist('INCOMPLETE_REQUIRES_REVIEW',type(exc).__name__,request_count!=len(responses))
        atomic_write(out/'result.json',value)
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'invalid_or_incomplete','error_type':type(exc).__name__})
    finally:
        if timer:timer.cancel()
        os.environ.pop(key_env,None)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--arm',action='store_true')
    args=parser.parse_args()
    config=json.loads((ROOT/CONFIG).read_text())
    build,cohort,rows,tasks,coverage=preflight(config)
    print(json.dumps({'status':'PREFLIGHT_PASSED','tasks':len(rows),
                      'max_initial_tokens':max(c['tokens'] for c in coverage),'commit':build['code_commit']}),flush=True)
    if args.preflight_only:return
    assert args.arm and os.name=='posix' and sys.stdin.isatty(), 'Remote hidden TTY input required'
    assert window(config)[0]>0, 'Must arm before the frozen start; no late automatic resumption'
    out=ROOT/'experiments'/config['experiment_id']
    out.mkdir(parents=True,exist_ok=False)  # Duplicate execution guard, including failed arms.
    write(out/'config.json',config);write(out/'coverage.json',coverage)
    write(out/'initial_state.json',WorkplaceEnv().initial_state)
    write(out/'identity.json',{'experiment_id':config['experiment_id'],'code_commit':build['code_commit'],
        'deployment':build,'model_revision':None,'requested_model':config['model'],
        'documented_version':config['documented_version'],'seed':None,
        'student_revision':config['student_revision'],'payload_sha256':config['payload_sha256'],
        'credential_persisted':False,'armed_from':'remote_hidden_TTY','no_gpu':True})
    append(ROOT/'experiments/registry.jsonl',{'experiment_id':config['experiment_id'],'event':'arm_attempt'})
    key_env=config['api_key_environment']
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            os.environ[key_env]=getpass.getpass('DeepSeek API key (hidden; remote process only): ')
        DeepSeekTransport(config)
        sys.stdout.flush();sys.stderr.flush()
        pid=os.fork()
        if pid:
            os.environ.pop(key_env,None)
            print(json.dumps({'status':'WORKER_FORKED','pid':pid,'experiment_id':config['experiment_id']}),flush=True)
            return
        os.setsid()
        signal.signal(signal.SIGHUP,signal.SIG_IGN)
        # No shell history or console captures. All descriptors point to /dev/null.
        fd=os.open('/dev/null',os.O_RDWR)
        for target in (0,1,2):os.dup2(fd,target)
        if fd>2:os.close(fd)
        run_worker(config,build,cohort,rows,tasks,out)
        os._exit(0)
    except Exception as exc:
        os.environ.pop(key_env,None)
        write(out/'arming_failure.json',{'error_type':type(exc).__name__,'secret_persisted':False})
        raise


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'STOPPED','error_type':type(exc).__name__,'details':'Sensitive diagnostics suppressed'}),flush=True)
        raise SystemExit(1)
