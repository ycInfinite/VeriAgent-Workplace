"""Download only public Qwen3 tokenizer/config artifacts, never weights."""
import hashlib
import json
from pathlib import Path
from fetch_official import get, ROOT

repo = 'Qwen/Qwen3-8B'
config_path = ROOT / 'configs/tokenizer.json'
existing = json.loads(config_path.read_text()) if config_path.exists() else None
if existing:
    repo = existing['model_id']
    revision = existing['model_revision']
else:
    meta = json.loads(get('https://huggingface.co/api/models/' + repo))
    revision = meta['sha']
target = ROOT / 'data/tokenizer' / revision
target.mkdir(parents=True, exist_ok=True)
records = []
for name in ('tokenizer.json','tokenizer_config.json','config.json','generation_config.json'):
    url = f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
    p = target / name
    b = p.read_bytes() if p.exists() else get(url)
    actual_sha = hashlib.sha256(b).hexdigest()
    if existing:
        expected = next(x['sha256'] for x in existing['files'] if x['name']==name)
        if actual_sha != expected:
            raise RuntimeError(f'Pinned tokenizer integrity mismatch: {name}')
    if not p.exists():
        with p.open('xb') as f:
            f.write(b)
    records.append({'name':name,'url':url,'bytes':len(b),'sha256':actual_sha})
out = {'model_id':repo,'model_revision':revision,'weights_downloaded':False,
       'tokenizer_path':str(target.relative_to(ROOT)).replace('\\','/'),'files':records}
if not existing:
    config_path.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'revision':revision,'bytes':sum(r['bytes'] for r in records),'weights_downloaded':False}))
