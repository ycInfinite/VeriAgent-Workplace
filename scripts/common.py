import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SOURCES = json.loads((ROOT/'configs/sources.json').read_text())

def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def load_rows(split):
    p = ROOT/'data/raw'/SOURCES['dataset_revision']/f'{split}.jsonl'
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def code_identity():
    # A process-local safe-directory setting; no global Git configuration change.
    cmd = ['git','-c','safe.directory=*']
    p = subprocess.run(cmd+['rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True)
    status = subprocess.run(cmd+['status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True,capture_output=True)
    return {'commit':p.stdout.strip() if p.returncode==0 else None,
            'git_error':p.stderr.strip() if p.returncode else None,
            'tracked_dirty':bool(status.stdout.strip()),
            'script_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                             for folder in ('scripts','veriagent') for f in (ROOT/folder).glob('*.py')}}

def registry(event):
    p=ROOT/'experiments/registry.jsonl'
    p.parent.mkdir(exist_ok=True)
    with p.open('a',encoding='utf-8') as f:
        f.write(json.dumps(event,ensure_ascii=False,default=str)+'\n')

class Run:
    def __init__(self, run_id, config):
        required = ['Research Question','Hypothesis','Independent Variable','Controlled Variables',
                    'Metrics','Evidence Gate','Cost Bound','Failure Branch']
        if any(k not in config for k in required):
            raise ValueError('Incomplete experiment card')
        self.id=run_id
        self.path=ROOT/'experiments'/run_id
        self.path.mkdir(parents=True,exist_ok=False)
        self.config=config
        write_json(self.path/'config.json',config)
        identity={'experiment_id':run_id,'started_at':datetime.now(timezone.utc).isoformat(),
                  'code':code_identity(),'sources':SOURCES,'python':platform.python_version(),
                  'policy_model':None,'seed':config.get('seed'), 'gpu_hours':0,'paid_cost_rmb':0,
                  'kind':config.get('experiment_kind','CPU_ENVIRONMENT_AUDIT_NOT_MODEL_EVAL')}
        write_json(self.path/'identity.json',identity)
        registry({'experiment_id':run_id,'event':'started','identity':identity})

    def append(self,name,value):
        with (self.path/name).open('a',encoding='utf-8') as f:
            f.write(json.dumps(value,ensure_ascii=False,default=str)+'\n')

    def finish(self,result,status='completed'):
        write_json(self.path/'result.json',result)
        registry({'experiment_id':self.id,'event':status,'result_path':str((self.path/'result.json').relative_to(ROOT)),
                  'completed_at':datetime.now(timezone.utc).isoformat()})

def card(question,hypothesis,variable,metrics,gate,**extra):
    return {'Research Question':question,'Hypothesis':hypothesis,'Independent Variable':variable,
            'Controlled Variables':['pinned upstream code','pinned data','fresh per-rollout state','CPU runtime'],
            'Metrics':metrics,'Evidence Gate':gate,'Cost Bound':'CPU only; GPU=0; paid API=0',
            'Failure Branch':'Keep raw evidence, mark invalid when applicable, stop GPU progression',**extra}
