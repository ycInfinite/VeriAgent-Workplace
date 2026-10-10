"""Restore one explicitly reviewed execution archive from private GitHub, no remote account token."""
import argparse,getpass,hashlib,json,shlex,subprocess,urllib.request,urllib.parse
from pathlib import Path
import paramiko
from remote_session import PinnedKey
ROOT=Path(__file__).resolve().parents[1]
REPO='ycInfinite/VeriAgent-Workplace'
ARTIFACT='evidence/sft-recovery-20261010/execution_bundle.tar.gz'
REMOTE=r'''
import json,sys,hashlib,urllib.request,urllib.parse,tarfile,io
from pathlib import Path
phase='parse'
try:
 p=json.loads(sys.stdin.read());root=Path(p['root']).resolve()
 assert root.is_relative_to(Path('/root/autodl-tmp')) and root.name=='veriagent-workplace-sft-20261010'
 u=urllib.parse.urlsplit(p['url']);assert u.scheme=='https' and u.hostname=='raw.githubusercontent.com'
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):raise RuntimeError('Unexpected redirect')
 phase='download'
 with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(p['url'],headers={'Cache-Control':'no-cache'}),timeout=90) as r:data=r.read(16000001)
 assert len(data)<=16000000 and hashlib.sha256(data).hexdigest()==p['receipt']['archive_sha256']
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\x00'+data).hexdigest()==p['blob']
 expected={e['path']:e for e in p['receipt']['members']};phase='verify_archive'
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
  assert len(t.getmembers())==len(expected) and {m.name for m in t.getmembers()}==set(expected)
  verified=[]
  for m in t.getmembers():
   target=(root/m.name).resolve();assert target.is_relative_to(root) and m.isfile() and not m.issym()
   b=t.extractfile(m).read();assert len(b)==expected[m.name]['bytes'] and hashlib.sha256(b).hexdigest()==expected[m.name]['sha256']
   if target.exists():assert target.read_bytes()==b,'Existing conflicting file'
   verified.append((target,b))
  phase='restore_verified_files'
  for target,b in verified:
   target.parent.mkdir(parents=True,exist_ok=True)
   if not target.exists():target.write_bytes(b)
 receipt={'status':'GITHUB_RECOVERY_VERIFIED','archive_git_commit':p['commit'],'execution_code_commit':p['receipt']['execution_commit'],
  'archive_sha256':p['receipt']['archive_sha256'],'archive_bytes':len(data),'verified_files':len(verified),
  'model_weights_in_archive':False,'account_credential_sent_to_remote':False,'temporary_urls_persisted':False,'root':str(root)}
 (root/'logs').mkdir(exist_ok=True)
 (root/'logs/github_recovery_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
except Exception as e:
 print(json.dumps({'status':'RECOVERY_FAILED','phase':phase,'error_type':type(e).__name__,'http_status':getattr(e,'code',None)}));sys.exit(1)
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True)
 p.add_argument('--pin',required=True);p.add_argument('--commit',required=True);p.add_argument('--receipt',required=True)
 a=p.parse_args();dest=ROOT/a.receipt
 if dest.exists():raise FileExistsError('Receipt already exists')
 commit=subprocess.check_output(['git','rev-parse',a.commit],cwd=ROOT).decode().strip()
 info=json.loads(subprocess.check_output(['git','show',commit+':evidence/sft-recovery-20261010/bundle_receipt.json'],cwd=ROOT))
 blob=subprocess.check_output(['git','rev-parse',commit+':'+ARTIFACT],cwd=ROOT).decode().strip()
 password=getpass.getpass('SSH password (not logged): ')
 r=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],cwd=ROOT,
     input='protocol=https\nhost=github.com\npath='+REPO+'.git\n\n',text=True,capture_output=True,check=True)
 fields=dict(s.split('=',1) for s in r.stdout.splitlines() if '=' in s);token=fields['password']
 req=urllib.request.Request('https://api.github.com/repos/'+REPO+'/contents/'+ARTIFACT+'?ref='+commit,
     headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Cache-Control':'no-cache','User-Agent':'VeriAgent-recovery'})
 with urllib.request.urlopen(req,timeout=30) as response:meta=json.load(response)
 assert meta['sha']==blob and meta['size']==info['archive_bytes']
 url=urllib.parse.urlsplit(meta['download_url']);assert url.hostname=='raw.githubusercontent.com' and url.path=='/'+REPO+'/'+commit+'/'+ARTIFACT
 token=None;fields.clear();r=None;req=None
 client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey(a.pin))
 client.connect(a.host,port=a.port,username='root',password=password,allow_agent=False,look_for_keys=False,timeout=20)
 password=None
 try:
  command='source /etc/network_turbo >/dev/null 2>&1 && /root/miniconda3/bin/python -c '+shlex.quote(REMOTE)
  stdin,stdout,stderr=client.exec_command(command,timeout=180,get_pty=False)
  stdin.write(json.dumps({'url':meta['download_url'],'blob':blob,'commit':commit,'receipt':info,'root':'/root/autodl-tmp/veriagent-workplace-sft-20261010'}));stdin.flush();stdin.channel.shutdown_write()
  text=stdout.read().decode();errors=stderr.read();code=stdout.channel.recv_exit_status();meta=None;errors=None
  receipt=json.loads(text)
  if code:print(json.dumps(receipt));raise RuntimeError('Recovery failed')
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
 finally:client.close()

if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'STOPPED','error_type':type(e).__name__,'details':'Sensitive diagnostics suppressed'}));raise SystemExit(1)
