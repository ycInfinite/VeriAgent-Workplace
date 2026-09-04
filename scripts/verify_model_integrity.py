"""Stream-check public model weight LFS SHA256 against pinned official Hub metadata."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from huggingface_hub import HfApi,get_hf_file_metadata,hf_hub_url

ROOT=Path(__file__).resolve().parents[1]

def main():
    cfg=json.loads((ROOT/'configs/model_qualification_plan.json').read_text())
    info=HfApi().model_info(cfg['model_id'],revision=cfg['model_revision'],files_metadata=True,token=False)
    if info.sha!=cfg['model_revision']:raise RuntimeError('Model revision mismatch')
    records=[]
    for item in info.siblings:
        if not item.rfilename.endswith('.safetensors'):continue
        p=ROOT/'models/Qwen3-8B'/item.rfilename
        h=hashlib.sha256()
        with p.open('rb') as f:
            while chunk:=f.read(8*1024*1024):h.update(chunk)
        if item.lfs is not None:
            expected=item.lfs.sha256 if hasattr(item.lfs,'sha256') else item.lfs['sha256']
            source='Hub file-list LFS SHA256'
        else:
            meta=get_hf_file_metadata(hf_hub_url(cfg['model_id'],filename=item.rfilename,
                                      revision=cfg['model_revision']),token=False)
            if meta.commit_hash!=cfg['model_revision'] or meta.size!=p.stat().st_size:
                raise RuntimeError('File HEAD revision/size mismatch')
            expected=meta.etag
            if not expected or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
                raise RuntimeError('No independently supplied content SHA256')
            source='Pinned file HEAD linked ETag SHA256'
        actual=h.hexdigest()
        records.append({'file':item.rfilename,'bytes':p.stat().st_size,'sha256':actual,'expected_sha256':expected,
                        'expected_hash_source':source,'match':actual==expected})
        if actual!=expected:raise RuntimeError('Weight integrity mismatch')
    if not records:raise RuntimeError('No weight files verified')
    result={'model_id':cfg['model_id'],'revision':info.sha,'verified_at':datetime.now(timezone.utc).isoformat(),
            'files':records,'total_bytes':sum(x['bytes'] for x in records),'all_match':True}
    target=ROOT/'model_integrity.json'
    if target.exists():raise FileExistsError('Integrity receipt already exists')
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'weight_files':len(records),'bytes':result['total_bytes'],'all_match':True}))

if __name__=='__main__':main()
