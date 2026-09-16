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
import urllib.parse
import urllib.request

import paramiko
from remote_session import PinnedKey

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='ycInfinite/VeriAgent-Workplace'
TEACHER_FILES = ['configs/teacher_acquisition_plan.json', 'veriagent/teacher_data.py',
                 'veriagent/teacher_rollout.py', 'scripts/collect_teacher_probe.py']

REMOTE_CODE=r'''
import hashlib,json,os,shutil,sys,urllib.request,urllib.parse
from pathlib import Path
try:
    # The short-lived URL plan is not echoed or serialized to any file.
    os.environ['VERIAGENT_GITHUB_SYNC_PLAN']=sys.stdin.read()
    plan=json.loads(os.environ['VERIAGENT_GITHUB_SYNC_PLAN'])
    root=Path(plan['remote_root']).resolve()
    assert root.is_dir() and root.is_relative_to(Path('/root/autodl-tmp'))
    original=(root/'bundle_manifest.json').read_bytes();manifest=json.loads(original)
    for entry in manifest['files']:
        path=(root/entry['path']).resolve();assert path.is_relative_to(root)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    allowed={x['path'] for x in manifest['files'] if not x['path'].startswith(('vendor/','data/'))}
    teacher_files={'configs/teacher_acquisition_plan.json','veriagent/teacher_data.py',
                   'veriagent/teacher_rollout.py','scripts/collect_teacher_probe.py'}
    additions=set(plan.get('additional_paths',[]))
    assert not additions or additions==teacher_files
    assert {x['path'] for x in plan['files']}==allowed|additions
    staging=root/'.github-sync'/plan['commit'];staging.mkdir(parents=True,exist_ok=True)
    for entry in plan['files']:
        url=urllib.parse.urlsplit(entry['download_url'])
        assert url.scheme=='https' and url.hostname=='raw.githubusercontent.com'
        target=(staging/entry['path']).resolve();assert target.is_relative_to(staging.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            data=target.read_bytes()
        else:
            with urllib.request.urlopen(entry['download_url'],timeout=45) as response:
                data=response.read(2000001)
            assert len(data)<=2000000
        assert hashlib.sha256(data).hexdigest()==entry['sha256']
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+bytes([0])+data).hexdigest()
        assert blob==entry['git_blob_sha']
        if not target.exists():target.write_bytes(data)
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
        'account_credential_sent_to_remote':False,'temporary_urls_persisted':False,
        'dev_or_final_cases_downloaded':False,'weights_or_venv_modified':False,
        'source_files':[{k:v for k,v in x.items() if k!='download_url'} for x in plan['files']],
        'manifest_sha256':hashlib.sha256((root/'bundle_manifest.json').read_bytes()).hexdigest()}
    (root/'logs/github_sync_receipt.json').write_text(json.dumps(receipt,indent=2))
    os.environ.pop('VERIAGENT_GITHUB_SYNC_PLAN',None)
    print(json.dumps(receipt))
except Exception as exc:
    os.environ.pop('VERIAGENT_GITHUB_SYNC_PLAN',None)
    print(json.dumps({'status':'GITHUB_SYNC_FAILED','error_type':type(exc).__name__}))
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
    args=parser.parse_args()
    destination=ROOT/args.receipt
    if destination.exists():raise FileExistsError('Refusing to overwrite sync receipt')
    commit=git('rev-parse',args.commit).decode().strip()
    bundle=json.loads((ROOT/'evidence/sft-preparation/bundle-4e5f9102.json').read_text())['manifest']
    paths=[x['path'] for x in bundle['files'] if not x['path'].startswith(('vendor/','data/'))]
    if args.include_teacher:paths=sorted(set(paths)|set(TEACHER_FILES))
    # Capture existing Git authentication inside this process; never print it.
    credential=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],cwd=ROOT,
        input='protocol=https\nhost=github.com\npath='+REPOSITORY+'.git\n\n',text=True,capture_output=True,timeout=30)
    if credential.returncode:raise RuntimeError('Existing Git authentication unavailable')
    fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token=fields.get('password')
    if not token:raise RuntimeError('Existing Git authentication incomplete')
    def file_metadata(path):
        api='https://api.github.com/repos/'+REPOSITORY+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+commit
        request=urllib.request.Request(api,headers={'Authorization':'Bearer '+token,
            'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'VeriAgent-pinned-file-sync'})
        with urllib.request.urlopen(request,timeout=30) as response:info=json.load(response)
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
    password=getpass.getpass('SSH password (not logged): ')
    client.connect(args.host,port=args.port,username='root',password=password,
        look_for_keys=False,allow_agent=False,timeout=20,auth_timeout=20,banner_timeout=20)
    password=None
    try:
        command='source /etc/network_turbo >/dev/null 2>&1 && /root/miniconda3/bin/python -c '+shlex.quote(REMOTE_CODE)
        stdin,stdout,stderr=client.exec_command(command,timeout=180,get_pty=False)
        stdin.write(json.dumps({'remote_root':args.remote_root,'repository':REPOSITORY,'commit':commit,'files':files,
                               'additional_paths':TEACHER_FILES if args.include_teacher else []}));stdin.flush()
        stdin.channel.shutdown_write()
        response=stdout.read().decode();errors=stderr.read();code=stdout.channel.recv_exit_status()
        files.clear();errors=None
        if code:raise RuntimeError('Remote GitHub sync failed; no secret diagnostics printed')
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
            'details':'Suppressed to prevent credential/temporary-URL disclosure'}),flush=True)
        raise SystemExit(1)
