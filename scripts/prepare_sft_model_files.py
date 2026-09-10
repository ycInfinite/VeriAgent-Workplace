"""Download only pinned public Qwen weights/tokenizer; never instantiate a model."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime,timezone

os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'
from huggingface_hub import snapshot_download

ROOT=Path(__file__).resolve().parents[1]

def main():
    cfg=json.loads((ROOT/'configs/sft_acquisition_plan.json').read_text())
    target=ROOT/cfg['weights_path']
    target.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(target).free < 19*2**30 and not (target/'model.safetensors.index.json').exists():
        raise RuntimeError('Insufficient disk for bounded model preparation')
    print(json.dumps({'event':'download_started','revision':cfg['model_revision'],
        'model_loaded':False,'time_utc':datetime.now(timezone.utc).isoformat()}),flush=True)
    snapshot_download(repo_id=cfg['model_id'],revision=cfg['model_revision'],token=False,
        local_dir=target,max_workers=2,
        allow_patterns=['*.safetensors','config.json','generation_config.json',
                        'tokenizer.json','tokenizer_config.json','model.safetensors.index.json'])
    tokenizer=json.loads((ROOT/'configs/tokenizer.json').read_text())
    tokenizer_dir=ROOT/tokenizer['tokenizer_path']
    tokenizer_dir.mkdir(parents=True,exist_ok=True)
    checks=[]
    for entry in tokenizer['files']:
        source=target/entry['name'];actual=hashlib.sha256(source.read_bytes()).hexdigest()
        if actual!=entry['sha256']:raise RuntimeError('Pinned auxiliary hash mismatch: '+entry['name'])
        copied=tokenizer_dir/entry['name']
        if copied.exists() and hashlib.sha256(copied.read_bytes()).hexdigest()!=actual:
            raise RuntimeError('Conflicting tokenizer copy; do not overwrite')
        if not copied.exists():shutil.copyfile(source,copied)
        checks.append({'file':entry['name'],'sha256':actual,'match':True})
    (ROOT/'model_aux_integrity.json').write_text(json.dumps({'revision':cfg['model_revision'],
        'files':checks,'all_match':True,'model_loaded':False},indent=2))
    print(json.dumps({'event':'download_finished','auxiliary_files_verified':len(checks),
        'model_loaded':False,'time_utc':datetime.now(timezone.utc).isoformat()}),flush=True)

if __name__=='__main__':main()
