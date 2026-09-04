"""Interactive SSH/SFTP transport. Password entered via getpass; never persisted.

This operational helper is not an agent tool and is never exposed to the model.
"""
import argparse
import base64
import getpass
import hashlib
import json
from pathlib import Path
import sys
import time
import paramiko

ROOT=Path(__file__).resolve().parents[1]

class PinnedKey(paramiko.MissingHostKeyPolicy):
    def __init__(self,pin):self.pin=pin
    def missing_host_key(self,client,hostname,key):
        actual='SHA256:'+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
        if actual!=self.pin:raise RuntimeError('SSH host fingerprint mismatch')

def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True)
    p.add_argument('--pin',required=True);args=p.parse_args()
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey(args.pin))
    password=getpass.getpass('SSH password (not logged): ')
    client.connect(args.host,port=args.port,username='root',password=password,
                   look_for_keys=False,allow_agent=False,timeout=20,auth_timeout=20,banner_timeout=20)
    password=None
    client.get_transport().set_keepalive(20)
    print(json.dumps({'event':'connected','credentials_persisted':False}),flush=True)
    for line in sys.stdin:
        try:
            req=json.loads(line)
            op=req['op']
            if op=='close':break
            if op in ('put','get'):
                local=(ROOT/req['local']).resolve()
                if not local.is_relative_to(ROOT):raise ValueError('Local path outside workspace')
                with client.open_sftp() as sftp:
                    if op=='put':sftp.put(str(local),req['remote'])
                    else:
                        local.parent.mkdir(parents=True,exist_ok=True)
                        if local.exists():raise FileExistsError('Refusing to overwrite downloaded evidence')
                        sftp.get(req['remote'],str(local))
                print(json.dumps({'op':op,'ok':True,'local':req['local']}),flush=True)
            elif op=='exec':
                _,stdout,stderr=client.exec_command(req['command'],timeout=req.get('timeout',60))
                channel=stdout.channel;output=[];errors=[];started=time.monotonic()
                while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
                    if channel.recv_ready():output.append(channel.recv(65536))
                    if channel.recv_stderr_ready():errors.append(channel.recv_stderr(65536))
                    if time.monotonic()-started>req.get('timeout',60):
                        channel.close();raise TimeoutError('Remote command exceeded timeout')
                    time.sleep(.02)
                limit=req.get('max_chars',12000)
                out=b''.join(output).decode(errors='replace');err=b''.join(errors).decode(errors='replace')
                print(json.dumps({'op':op,'exit_code':channel.recv_exit_status(),'stdout':out[-limit:],
                                  'stderr':err[-limit:],'stdout_chars':len(out),'stderr_chars':len(err)},ensure_ascii=False),flush=True)
            else:raise ValueError('Unsupported operation')
        except Exception as exc:
            print(json.dumps({'error_type':type(exc).__name__,'error':'Operation failed; credentials suppressed'}),flush=True)
    client.close()

if __name__=='__main__':main()
