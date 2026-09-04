"""Create a whitelist-only CPU-code/dev-task bundle for the user's personal GPU host."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    plan=json.loads((ROOT/'configs/model_qualification_plan.json').read_text())
    pilot=json.loads((ROOT/plan['pilot_manifest']).read_text())
    source=json.loads((ROOT/'configs/sources.json').read_text())
    rows=[json.loads(x) for x in (ROOT/'data/raw'/source['dataset_revision']/'train.jsonl').read_text().splitlines() if x.strip()]
    selected=[]
    for record in pilot['tasks']:
        assert record['pool']=='development'
        row=rows[record['source_row_index']]
        row.update({'task_uid':record['task_uid'],'source_pool':'development'})
        selected.append(row)
    paths=[ROOT/x for x in ('configs/sources.json','configs/tokenizer.json','configs/model_qualification_plan.json',
            'veriagent/__init__.py','veriagent/environment.py','veriagent/policy_protocol.py',
            'scripts/run_day3.py','scripts/gpu_preflight.py','scripts/verify_model_integrity.py')]
    base=ROOT/'vendor/Gym/resources_servers/workplace_assistant'
    paths += [base/'utils.py']+list((base/'workplace_assistant_tools').glob('*.py'))+list((base/'csv_data').rglob('*.csv'))
    manifest={'code_commit':commit,'model_revision':plan['model_revision'],'gym_commit':source['gym_commit'],
              'dataset_revision':source['dataset_revision'],'task_count':len(selected),'seed_protocol':plan['seeds'],
              'sealed_data_included':False,'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),
                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    data=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected).encode()
    manifest['dev_data_sha256']=hashlib.sha256(data).hexdigest()
    target=ROOT/'dist'/f'day3-{commit[:8]}.tar.gz';target.parent.mkdir(exist_ok=True)
    if target.exists():raise FileExistsError(target)
    with tarfile.open(target,'w:gz') as tar:
        for p in paths:tar.add(p,arcname=str(p.relative_to(ROOT)).replace('\\','/'),recursive=False)
        for name,payload in [('data/day3_dev24.jsonl',data),('bundle_manifest.json',json.dumps(manifest,indent=2).encode())]:
            info=tarfile.TarInfo(name);info.size=len(payload);tar.addfile(info,io.BytesIO(payload))
    receipt=ROOT/'evidence/day3';receipt.mkdir(exist_ok=True,parents=True)
    (receipt/f'bundle-{commit[:8]}.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'bundle':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'commit':commit,'tasks':len(selected)}))

if __name__=='__main__':main()
