"""Whitelist-only bundle for the fixed training acquisition cohort; no GPU use."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

from common import ROOT, load_rows, write_json
from collect_training_probe import validate_inputs


def main():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    config=json.loads((ROOT/'configs/sft_acquisition_plan.json').read_text())
    cohort=json.loads((ROOT/config['cohort_manifest']).read_text())
    preparation=json.loads((ROOT/'experiments'/config['preparation_run']/'result.json').read_text())
    if preparation['status']!='CPU_PREPARATION_PASSED_GPU_COLLECTION_AND_TRAINER_PENDING':
        raise ValueError('CPU preparation gate has not passed')
    raw=load_rows('train');selected=[]
    for metadata in cohort['tasks']:
        if metadata['pool']!='training_candidate' or metadata['source_split']!='train':
            raise ValueError('Non-training member in cohort')
        row=deepcopy(raw[metadata['source_row_index']])
        row.update({'task_uid':metadata['task_uid'],'source_pool':'training_candidate'})
        selected.append(row)
    validate_inputs(config,cohort,selected)
    relative=[
        'configs/sources.json','configs/tokenizer.json','configs/sft_acquisition_plan.json',
        'veriagent/__init__.py','veriagent/environment.py','veriagent/policy_protocol.py',
        'veriagent/token_mask.py','veriagent/sft_data.py',
        'scripts/run_day3.py','scripts/collect_training_probe.py','scripts/verify_model_integrity.py',
        'scripts/prepare_sft_model_files.py','scripts/validate_sft_no_card.py',
        'scripts/run_sft_probe.py','configs/sft_probe_plan.json','requirements-sft-probe.pinned.txt',
        'scripts/gpu_preflight.py','requirements-day3-remote.pinned.txt','requirements-sft-acquisition.pinned.txt',
        config['cohort_manifest'],
    ]
    upstream=ROOT/'vendor/Gym/resources_servers/workplace_assistant'
    paths=[ROOT/x for x in relative]+[upstream/'utils.py']
    paths+=list((upstream/'workplace_assistant_tools').glob('*.py'))
    paths+=list((upstream/'csv_data').rglob('*.csv'))
    source=json.loads((ROOT/'configs/sources.json').read_text())
    data=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected).encode()
    entries=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),
              'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    entries.append({'path':config['data_path'],'sha256':hashlib.sha256(data).hexdigest()})
    manifest={'code_commit':commit,'model_revision':config['model_revision'],
        'gym_commit':source['gym_commit'],'dataset_revision':source['dataset_revision'],
        'purpose':'TRAINING_POOL_REAL_POLICY_ACQUISITION_NOT_PARAMETER_UPDATE',
        'task_count':len(selected),'source_pool':'training_candidate','seed':config['seed'],
        'contains_dev_tasks':False,'contains_final_tasks':False,'contains_bfcl_cases':False,
        'contains_model_weights':False,'contains_credentials':False,'files':entries}
    target=ROOT/'dist'/f'sft-acquisition-{commit[:8]}.tar.gz'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(target)
    with tarfile.open(target,'w:gz') as tar:
        for p in paths:
            tar.add(p,arcname=str(p.relative_to(ROOT)).replace('\\','/'),recursive=False)
        for name,payload in [(config['data_path'],data),('bundle_manifest.json',json.dumps(manifest,indent=2).encode())]:
            info=tarfile.TarInfo(name);info.size=len(payload);tar.addfile(info,io.BytesIO(payload))
    receipt={'bundle':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'manifest':manifest}
    write_json(ROOT/'evidence/sft-preparation'/f'bundle-{commit[:8]}.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('bundle','bytes','sha256')},indent=2))


if __name__=='__main__':main()
