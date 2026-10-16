"""Pull a pinned private GitHub revision on the execution host without persisting tokens.

Uses the existing local Git credential helper only against api.github.com. The
execution host receives temporary raw-file URLs through non-echoing SSH stdin;
those URLs live only in process memory/environment, never command args or files.
Only the already approved execution-file whitelist is synchronized.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import getpass
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import paramiko
from remote_session import PinnedKey

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='ycInfinite/VeriAgent-Workplace'
TEACHER_FILES = ['configs/teacher_acquisition_plan.json', 'veriagent/teacher_data.py',
                 'veriagent/teacher_rollout.py', 'scripts/collect_teacher_probe.py']
TEACHER_PROBE_FILES = ['experiments/TEACHER-ACQUIRE-20260916-001/config.json',
                       'experiments/TEACHER-ACQUIRE-20260916-001/trajectories.jsonl',
                       'experiments/TEACHER-ACQUIRE-20260916-001/probe_quality_approvals.json']
INTERACTIVE_FILES = ['configs/qwen_code_token_plan.example.json',
                     'requirements-interactive.pinned.txt',
                     'scripts/serve_workplace_interactive.py',
                     'scripts/setup_interactive_client.py',
                     'scripts/launch_interactive_client.py']
DEEPSEEK_FILES = ['configs/deepseek_acquisition_plan.json', 'veriagent/deepseek_teacher.py',
                  'scripts/collect_deepseek_probe.py']

WINDOW_FILES = ['configs/deepseek_window_acquisition.json','scripts/collect_deepseek_window.py',
                'experiments/DEEPSEEK-POOL-PREP-20260917-001/cohort.json',
                'experiments/DEEPSEEK-POOL-PREP-20260917-001/tasks.jsonl',
                'experiments/DEEPSEEK-POOL-PREP-20260917-001/tool_schemas.json']

SFT_STAGE_FILES = ['configs/sft_comparison_plan.json', 'veriagent/sft_stage.py', 'scripts/run_sft_comparison.py', 'scripts/evaluate_sft_comparison.py', 'scripts/validate_sft_stage_host.py', 'experiments/SFT-READY-20260917-001/review_manifest.json', 'experiments/SFT-READY-20260917-001/semantic_judgments.json', 'experiments/SFT-READY-20260917-001/quality_approvals.json', 'experiments/SFT-READY-20260917-001/corpus_manifest.json', 'experiments/SFT-READY-20260917-001/selection.json', 'experiments/SFT-READY-20260917-001/selection_policy.json', 'experiments/SFT-READY-20260917-001/s1_examples.jsonl.gz', 'experiments/SFT-READY-20260917-001/s2_examples.jsonl.gz', 'experiments/SFT-READY-20260917-001/eval_dev24.jsonl.gz']

SFT_SCALE_FILES = ['configs/sft_scale_plan_v2.json', 'veriagent/sft_scale.py', 'scripts/run_sft_scale.py', 'scripts/evaluate_sft_scale.py', 'scripts/validate_sft_scale_host.py', 'experiments/SFT-SCALE-PREP-20261010-002/selection.json', 'experiments/SFT-SCALE-PREP-20261010-002/s100_examples.jsonl.gz']

SFT_MIXED_FILES = ['configs/sft_mixed100_plan.json', 'veriagent/sft_mixed.py', 'scripts/run_sft_mixed.py', 'scripts/evaluate_sft_mixed.py', 'scripts/validate_sft_mixed_host.py', 'experiments/NOOP-REVIEW-20261010-001/quality_approvals.json', 'experiments/NOOP-REVIEW-20261010-001/judgments.json', 'experiments/NOOP-REVIEW-20261010-001/mixed100_selection.json', 'experiments/NOOP-REVIEW-20261010-001/mixed100_examples.jsonl.gz', 'experiments/MIX100-PREP-20261010-001/quality_approvals.json']

DPO_FILES = ['configs/dpo_probe_plan.json', 'veriagent/dpo.py', 'scripts/run_dpo_probe.py', 'scripts/check_dpo_torch.py', 'experiments/DPO-PREP-20261012-001/pairs.jsonl.gz', 'experiments/DPO-PREP-20261012-001/review.json', 'experiments/DPO-PREP-20261012-001/manifest.json']

PREFERENCE_FILES = ['configs/preference_comparison_plan.json', 'scripts/run_preference_comparison.py', 'scripts/evaluate_preference_comparison.py', 'scripts/check_preference_torch.py']

S1_FAILURE_FILES = ['configs/s1_failure_acquisition.json', 'scripts/collect_s1_failures.py', 'experiments/S1-FAILURE-PREP-20261012-002/tasks.jsonl.gz', 'experiments/S1-FAILURE-PREP-20261012-002/selection.json']

CURRENT_PREFERENCE_FILES = ['configs/current_s1_preference_plan.json', 'scripts/run_current_s1_preference.py', 'scripts/evaluate_current_s1_preference.py', 'scripts/run_current_s1_preference_pipeline.py', 'experiments/S1-PAIR-REVIEW-20261016-001/reward_gap_pairs.jsonl.gz']

PREFERENCE_EXPANSION_FILES = ['configs/s1_preference_expansion.json', 'scripts/collect_s1_preference_expansion.py', 'experiments/S1-EXPAND-PREP-20261016-001/tasks.jsonl.gz', 'experiments/S1-EXPAND-PREP-20261016-001/selection.json']

PREFERENCE29_PREFLIGHT_FILES = ['configs/preference29_preflight.json', 'scripts/preflight_preference29.py', 'experiments/S1-EXPAND-REVIEW-20261016-001/cumulative_reward_gap_pairs.jsonl.gz']

REMOTE_CODE=r'''
import hashlib,json,os,shutil,sys,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
phase='parse_plan'
failed_path=None
try:
    # The short-lived URL plan is not echoed or serialized to any file.
    os.environ['VERIAGENT_GITHUB_SYNC_PLAN']=sys.stdin.read()
    plan=json.loads(os.environ['VERIAGENT_GITHUB_SYNC_PLAN'])
    root=Path(plan['remote_root']).resolve()
    assert root.is_dir() and root.is_relative_to(Path('/root/autodl-tmp'))
    original=(root/'bundle_manifest.json').read_bytes();manifest=json.loads(original)
    phase='verify_existing'
    for entry in manifest['files']:
        path=(root/entry['path']).resolve();assert path.is_relative_to(root)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    phase='verify_whitelist'
    allowed={x['path'] for x in manifest['files'] if not x['path'].startswith(('vendor/','data/'))}
    teacher_files={'configs/teacher_acquisition_plan.json','veriagent/teacher_data.py',
                   'veriagent/teacher_rollout.py','scripts/collect_teacher_probe.py'}
    teacher_probe_files={'experiments/TEACHER-ACQUIRE-20260916-001/config.json',
                         'experiments/TEACHER-ACQUIRE-20260916-001/trajectories.jsonl',
                         'experiments/TEACHER-ACQUIRE-20260916-001/probe_quality_approvals.json'}
    interactive_files={'configs/qwen_code_token_plan.example.json','requirements-interactive.pinned.txt',
                       'scripts/serve_workplace_interactive.py','scripts/setup_interactive_client.py',
                       'scripts/launch_interactive_client.py'}
    deepseek_files={'configs/deepseek_acquisition_plan.json','veriagent/deepseek_teacher.py',
                    'scripts/collect_deepseek_probe.py'}
    window_files={'configs/deepseek_window_acquisition.json','scripts/collect_deepseek_window.py',
                  'experiments/DEEPSEEK-POOL-PREP-20260917-001/cohort.json',
                  'experiments/DEEPSEEK-POOL-PREP-20260917-001/tasks.jsonl',
                  'experiments/DEEPSEEK-POOL-PREP-20260917-001/tool_schemas.json'}
    sft_stage_files={'experiments/SFT-READY-20260917-001/semantic_judgments.json', 'experiments/SFT-READY-20260917-001/corpus_manifest.json', 'configs/sft_comparison_plan.json', 'experiments/SFT-READY-20260917-001/selection.json', 'experiments/SFT-READY-20260917-001/selection_policy.json', 'experiments/SFT-READY-20260917-001/quality_approvals.json', 'scripts/run_sft_comparison.py', 'experiments/SFT-READY-20260917-001/review_manifest.json', 'scripts/evaluate_sft_comparison.py', 'scripts/validate_sft_stage_host.py', 'experiments/SFT-READY-20260917-001/eval_dev24.jsonl.gz', 'experiments/SFT-READY-20260917-001/s2_examples.jsonl.gz', 'experiments/SFT-READY-20260917-001/s1_examples.jsonl.gz', 'veriagent/sft_stage.py'}
    sft_scale_files={'scripts/run_sft_scale.py', 'experiments/SFT-SCALE-PREP-20261010-002/selection.json', 'scripts/validate_sft_scale_host.py', 'configs/sft_scale_plan_v2.json', 'experiments/SFT-SCALE-PREP-20261010-002/s100_examples.jsonl.gz', 'veriagent/sft_scale.py', 'scripts/evaluate_sft_scale.py'}
    sft_mixed_files={'experiments/NOOP-REVIEW-20261010-001/mixed100_selection.json', 'experiments/MIX100-PREP-20261010-001/quality_approvals.json', 'veriagent/sft_mixed.py', 'scripts/run_sft_mixed.py', 'scripts/evaluate_sft_mixed.py', 'experiments/NOOP-REVIEW-20261010-001/mixed100_examples.jsonl.gz', 'experiments/NOOP-REVIEW-20261010-001/quality_approvals.json', 'experiments/NOOP-REVIEW-20261010-001/judgments.json', 'scripts/validate_sft_mixed_host.py', 'configs/sft_mixed100_plan.json'}
    dpo_files={'experiments/DPO-PREP-20261012-001/review.json', 'experiments/DPO-PREP-20261012-001/pairs.jsonl.gz', 'experiments/DPO-PREP-20261012-001/manifest.json', 'scripts/run_dpo_probe.py', 'scripts/check_dpo_torch.py', 'veriagent/dpo.py', 'configs/dpo_probe_plan.json'}
    preference_files={'scripts/run_preference_comparison.py', 'scripts/evaluate_preference_comparison.py', 'configs/preference_comparison_plan.json', 'scripts/check_preference_torch.py'}
    s1_failure_files={'experiments/S1-FAILURE-PREP-20261012-002/tasks.jsonl.gz', 'experiments/S1-FAILURE-PREP-20261012-002/selection.json', 'scripts/collect_s1_failures.py', 'configs/s1_failure_acquisition.json'}
    current_preference_files={'configs/current_s1_preference_plan.json', 'scripts/run_current_s1_preference.py', 'scripts/evaluate_current_s1_preference.py', 'scripts/run_current_s1_preference_pipeline.py', 'experiments/S1-PAIR-REVIEW-20261016-001/reward_gap_pairs.jsonl.gz'}
    preference_expansion_files={'configs/s1_preference_expansion.json', 'scripts/collect_s1_preference_expansion.py', 'experiments/S1-EXPAND-PREP-20261016-001/tasks.jsonl.gz', 'experiments/S1-EXPAND-PREP-20261016-001/selection.json'}
    preference29_preflight_files={'configs/preference29_preflight.json', 'experiments/S1-EXPAND-REVIEW-20261016-001/cumulative_reward_gap_pairs.jsonl.gz', 'scripts/preflight_preference29.py'}
    additions=set(plan.get('additional_paths',[]))
    assert (not additions or additions==teacher_files or additions==teacher_files|teacher_probe_files
            or additions==teacher_files|teacher_probe_files|interactive_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files|preference_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files|preference_files|s1_failure_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files|preference_files|s1_failure_files|current_preference_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files|preference_files|s1_failure_files|current_preference_files|preference_expansion_files
            or additions==teacher_files|teacher_probe_files|interactive_files|deepseek_files|window_files|sft_stage_files|sft_scale_files|sft_mixed_files|dpo_files|preference_files|s1_failure_files|current_preference_files|preference_expansion_files|preference29_preflight_files)
    assert {x['path'] for x in plan['files']}==allowed|additions
    staging=root/'.github-sync'/plan['commit'];staging.mkdir(parents=True,exist_ok=True)
    reused_verified=[]
    phase='download_verified_files'
    for entry in plan['files']:
        failed_path=entry['path']
        url=urllib.parse.urlsplit(entry['download_url'])
        assert url.scheme=='https' and url.hostname=='raw.githubusercontent.com'
        target=(staging/entry['path']).resolve();assert target.is_relative_to(staging.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            data=target.read_bytes()
        else:
            existing=(root/entry['path']).resolve();assert existing.is_relative_to(root)
            candidate=existing.read_bytes() if existing.is_file() else None
            if candidate is not None and hashlib.sha256(candidate).hexdigest()==entry['sha256']:
                # GitHub metadata already pins this exact blob at the requested ref.
                # Reusing identical bytes avoids unnecessary network transfers.
                data=candidate;reused_verified.append(entry['path'])
            else:
                for attempt in range(3):
                    try:
                        request=urllib.request.Request(entry['download_url'],headers={'Cache-Control':'no-cache'})
                        with urllib.request.urlopen(request,timeout=45) as response:
                            data=response.read(2000001)
                        break
                    except urllib.error.HTTPError as exc:
                        if exc.code not in (429,500,502,503,504) or attempt==2:raise
                        time.sleep(attempt+1)
                    except (urllib.error.URLError,TimeoutError):
                        if attempt==2:raise
                        time.sleep(attempt+1)
                assert len(data)<=2000000
        assert hashlib.sha256(data).hexdigest()==entry['sha256']
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+bytes([0])+data).hexdigest()
        assert blob==entry['git_blob_sha']
        if not target.exists():target.write_bytes(data)
    phase='apply_verified_files'
    changed=[]
    for entry in plan['files']:
        path=(root/entry['path']).resolve();data=(staging/entry['path']).read_bytes()
        if not path.exists() or path.read_bytes()!=data:
            if path.exists():
                backup=root/'logs/pre_github_files'/plan['commit']/entry['path']
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,backup)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data);changed.append(entry['path'])
    old_receipt=root/'logs/deployment_manifest_before_github.json'
    if not old_receipt.exists():old_receipt.write_bytes(original)
    manifest['previous_bundle_manifest_sha256']=hashlib.sha256(original).hexdigest()
    manifest['code_commit']=plan['commit'];manifest['code_transport']='GitHub fixed-ref temporary raw-file downloads'
    manifest['git_repository']='https://github.com/'+plan['repository']+'.git'
    existing={x['path'] for x in manifest['files']}
    manifest['files'].extend({'path':path} for path in sorted(additions-existing))
    for entry in manifest['files']:entry['sha256']=hashlib.sha256((root/entry['path']).read_bytes()).hexdigest()
    (root/'bundle_manifest.json').write_text(json.dumps(manifest,indent=2))
    receipt={'status':'GITHUB_SYNC_VERIFIED','repository':plan['repository'],'git_commit':plan['commit'],
        'transport':'Execution host downloads pinned files directly from GitHub',
        'private_repository':True,'synced_file_count':len(plan['files']),'changed_files':changed,
        'unchanged_files_reused_after_hash_and_git_blob_checks':reused_verified,
        'account_credential_sent_to_remote':False,'temporary_urls_persisted':False,
        'dev_or_final_cases_downloaded':False,'weights_or_venv_modified':False,
        'source_files':[{k:v for k,v in x.items() if k!='download_url'} for x in plan['files']],
        'manifest_sha256':hashlib.sha256((root/'bundle_manifest.json').read_bytes()).hexdigest()}
    (root/'logs/github_sync_receipt.json').write_text(json.dumps(receipt,indent=2))
    os.environ.pop('VERIAGENT_GITHUB_SYNC_PLAN',None)
    print(json.dumps(receipt))
except Exception as exc:
    os.environ.pop('VERIAGENT_GITHUB_SYNC_PLAN',None)
    print(json.dumps({'status':'GITHUB_SYNC_FAILED','error_type':type(exc).__name__,
                      'phase':phase,'failed_path':failed_path,'http_status':getattr(exc,'code',None)}))
    sys.exit(1)
'''


def git(*args):
    result=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True)
    return result.stdout


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',required=True);parser.add_argument('--port',required=True,type=int)
    parser.add_argument('--pin',required=True);parser.add_argument('--commit',required=True)
    parser.add_argument('--remote-root',required=True);parser.add_argument('--receipt',required=True)
    parser.add_argument('--include-teacher',action='store_true',help='Add only the four reviewed teacher execution files')
    parser.add_argument('--include-teacher-probe-data',action='store_true',help='Also verify the fixed teacher run and its two-task approval')
    parser.add_argument('--include-interactive',action='store_true',help='Add the five reviewed interactive client files; preserve existing teacher files')
    parser.add_argument('--include-deepseek',action='store_true',help='Add three reviewed ordinary DeepSeek qualification files; preserve previous deployment')
    parser.add_argument('--include-deepseek-window',action='store_true',help='Add frozen723 training payloads and one-shot window collector')
    parser.add_argument('--include-sft-stage',action='store_true',help='Add only the prepared SFT stage code and frozen reviewed data/dev-only evaluation pack')
    parser.add_argument('--include-sft-scale',action='store_true',help='Add only authorized nested100 scale files')
    parser.add_argument('--include-sft-mixed',action='store_true',help='Add only reviewed mixed100 data and execution files')
    parser.add_argument('--include-dpo',action='store_true',help='Add reviewed training-only DPO probe payload; never starts a model')
    parser.add_argument('--include-preference',action='store_true',help='Add bounded12task preference comparison runners and config')
    parser.add_argument('--include-s1-failures',action='store_true',help='Add frozen25trainingtask S1 acquisition only')
    parser.add_argument('--include-current-preference',action='store_true',help='Add only the authorized six-current-S1-pair comparison payload')
    parser.add_argument('--include-preference-expansion',action='store_true',help='Add only frozen remaining91 currentS1 collection inputs')
    parser.add_argument('--include-preference29-preflight',action='store_true')
    args=parser.parse_args()
    if args.include_preference29_preflight:args.include_preference_expansion=True
    if args.include_preference_expansion:args.include_current_preference=True
    if args.include_current_preference:args.include_s1_failures=True
    if args.include_s1_failures:args.include_preference=True
    if args.include_preference:args.include_dpo=True
    if args.include_dpo:args.include_sft_mixed=True  # Preserve the already deployed S100/MIX100 manifest.
    if args.include_sft_mixed:args.include_sft_scale=True
    if args.include_sft_scale:args.include_sft_stage=True
    if args.include_sft_stage:args.include_deepseek_window=True
    if args.include_deepseek_window:args.include_deepseek=True
    destination=ROOT/args.receipt
    if destination.exists():raise FileExistsError('Refusing to overwrite sync receipt')
    commit=git('rev-parse',args.commit).decode().strip()
    bundle=json.loads((ROOT/'evidence/sft-preparation/bundle-4e5f9102.json').read_text())['manifest']
    paths=[x['path'] for x in bundle['files'] if not x['path'].startswith(('vendor/','data/'))]
    additions=TEACHER_FILES if args.include_teacher or args.include_teacher_probe_data or args.include_interactive or args.include_deepseek else []
    if args.include_teacher_probe_data or args.include_interactive or args.include_deepseek:additions=additions+TEACHER_PROBE_FILES
    if args.include_interactive or args.include_deepseek:additions=additions+INTERACTIVE_FILES
    if args.include_deepseek:additions=additions+DEEPSEEK_FILES
    if args.include_deepseek_window:additions=additions+WINDOW_FILES
    if args.include_sft_stage:additions=additions+SFT_STAGE_FILES
    if args.include_sft_scale:additions=additions+SFT_SCALE_FILES
    if args.include_sft_mixed:additions=additions+SFT_MIXED_FILES
    if args.include_dpo:additions=additions+DPO_FILES
    if args.include_preference:additions=additions+PREFERENCE_FILES
    if args.include_s1_failures:additions=additions+S1_FAILURE_FILES
    if args.include_current_preference:additions=additions+CURRENT_PREFERENCE_FILES
    if args.include_preference_expansion:additions=additions+PREFERENCE_EXPANSION_FILES
    if args.include_preference29_preflight:additions=additions+PREFERENCE29_PREFLIGHT_FILES
    paths=sorted(set(paths)|set(additions))
    # Ask before requesting signed download URLs: waiting at the password prompt
    # after metadata fetch can let short-lived private-repo links expire.
    password=getpass.getpass('SSH password (not logged): ')
    # Capture existing Git authentication inside this process; never print it.
    credential=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],cwd=ROOT,
        input='protocol=https\nhost=github.com\npath='+REPOSITORY+'.git\n\n',text=True,capture_output=True,timeout=30)
    if credential.returncode:raise RuntimeError('Existing Git authentication unavailable')
    fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token=fields.get('password')
    if not token:raise RuntimeError('Existing Git authentication incomplete')
    def file_metadata(path):
        # Private raw-file URLs expire. A unique metadata request prevents an
        # intermediary from serving a stale signed URL for an unchanged ref.
        # The commit, returned blob SHA and remote SHA256 gates remain unchanged.
        api='https://api.github.com/repos/'+REPOSITORY+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+commit+'&cache_bust='+str(time.time_ns())
        request=urllib.request.Request(api,headers={'Authorization':'Bearer '+token,
            'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',
            'Cache-Control':'no-cache','User-Agent':'VeriAgent-pinned-file-sync'})
        # Retry only read-only GitHub metadata transport, never a model request.
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request,timeout=30) as response:info=json.load(response)
                break
            except (urllib.error.URLError,TimeoutError) as exc:
                if attempt==2:
                    exc.failed_path=path
                    raise
                time.sleep(attempt+1)
        data=git('show',commit+':'+path)
        expected_blob=git('rev-parse',commit+':'+path).decode().strip()
        if info['sha']!=expected_blob:raise ValueError('GitHub/local blob identity mismatch')
        download=urllib.parse.urlsplit(info['download_url'])
        if download.scheme!='https' or download.hostname!='raw.githubusercontent.com':raise ValueError('Unexpected download host')
        if download.path!='/'+REPOSITORY+'/'+commit+'/'+path:raise ValueError('Unpinned download path')
        return {'path':path,'sha256':hashlib.sha256(data).hexdigest(),'git_blob_sha':expected_blob,'download_url':info['download_url']}
    with ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(file_metadata,paths))
    token=None;fields.clear();credential=None
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey(args.pin))
    client.connect(args.host,port=args.port,username='root',password=password,
        look_for_keys=False,allow_agent=False,timeout=20,auth_timeout=20,banner_timeout=20)
    password=None
    try:
        command='source /etc/network_turbo >/dev/null 2>&1 && /root/miniconda3/bin/python -c '+shlex.quote(REMOTE_CODE)
        stdin,stdout,stderr=client.exec_command(command,timeout=180,get_pty=False)
        stdin.write(json.dumps({'remote_root':args.remote_root,'repository':REPOSITORY,'commit':commit,'files':files,
                               'additional_paths':additions}));stdin.flush()
        stdin.channel.shutdown_write()
        response=stdout.read().decode();errors=stderr.read();code=stdout.channel.recv_exit_status()
        files.clear();errors=None
        if code:
            exc=RuntimeError('Remote GitHub sync failed; no secret diagnostics printed')
            try:
                failure=json.loads(response)
                if failure.get('status')=='GITHUB_SYNC_FAILED':
                    exc.remote_error_type=failure.get('error_type')
                    exc.remote_phase=failure.get('phase')
                    exc.remote_http_status=failure.get('http_status')
                    exc.failed_path=failure.get('failed_path')
            except (ValueError,TypeError):
                pass
            raise exc
        receipt=json.loads(response)
        if receipt.get('status')!='GITHUB_SYNC_VERIFIED':raise RuntimeError('Missing verified receipt')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print(json.dumps({'status':receipt['status'],'commit':commit,'files':receipt['synced_file_count'],
            'receipt':args.receipt,'account_credential_sent_to_remote':False}),flush=True)
    finally:client.close()


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'SYNC_FAILED','error_type':type(exc).__name__,
            'reason_type':type(getattr(exc,'reason',None)).__name__,
            'failed_path':getattr(exc,'failed_path',None),
            'remote_error_type':getattr(exc,'remote_error_type',None),
            'remote_phase':getattr(exc,'remote_phase',None),
            'remote_http_status':getattr(exc,'remote_http_status',None),
            'details':'Suppressed to prevent credential/temporary-URL disclosure'}),flush=True)
        raise SystemExit(1)
