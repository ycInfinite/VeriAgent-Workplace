"""Fetch bounded public CPU-audit inputs; never model weights or BFCL cases."""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'configs/sources.json').read_text())

def get(url: str) -> bytes:
    error = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'VeriAgent-Q0-public-source-audit'})
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read(35_000_001)
            if len(payload) > 35_000_000:
                raise ValueError('Per-file 35 MB download bound exceeded')
            return payload
        except Exception as exc:
            error = exc
            time.sleep(attempt + 1)
    raise RuntimeError(f'Public fetch failed: {url}: {error}')

def main():
    commit = CONFIG['gym_commit']
    existing_path = ROOT / 'evidence/sources/manifest.json'
    existing = json.loads(existing_path.read_text()) if existing_path.exists() else None
    if existing and existing['config'] != CONFIG:
        raise RuntimeError('Source identity changed: use a new audited snapshot instead of overwriting the manifest')
    expected_hashes = {x['path']:x['sha256'] for x in existing['files']} if existing else {}
    tree_url = f"https://api.github.com/repos/{CONFIG['gym_repo']}/git/trees/{commit}?recursive=1"
    tree_bytes = get(tree_url)
    tree = json.loads(tree_bytes)
    if tree.get('truncated'):
        raise RuntimeError('Incomplete upstream tree')
    files = []
    for entry in tree['tree']:
        p = entry['path']
        if entry['type'] != 'blob':
            continue
        take = (
            p.startswith('nemo_gym/') and p.endswith(('.py','.json','.yaml','.toml'))
            or p.startswith('resources_servers/workplace_assistant/') and '/notebooks/' not in p
            or p in ('pyproject.toml','LICENSE','README.md','responses_api_agents/simple_agent/app.py',
                     'environments/workplace_assistant/prepare.py','environments/workplace_assistant/config.yaml',
                     'fern/versions/latest/pages/training-tutorials/offline-training-w-rollouts.mdx',
                     'fern/versions/latest/pages/training-tutorials/nemo-rl-grpo/multi-node-training.mdx')
        )
        if take:
            if entry.get('size', 0) > 2_000_000:
                raise RuntimeError(f'Unexpected large source file: {p}')
            files.append((f'https://raw.githubusercontent.com/{CONFIG["gym_repo"]}/{commit}/{p}',
                          ROOT / 'vendor/Gym' / p, entry['sha']))
    if sum(e.get('size',0) for e in tree['tree'] if e['type']=='blob' and e['path'].startswith('nemo_gym/')) > 15_000_000:
        raise RuntimeError('Core source budget exceeded')
    rev = CONFIG['dataset_revision']
    for split in ('train','validation'):
        files.append((f'https://huggingface.co/datasets/{CONFIG["dataset_repo"]}/resolve/{rev}/{split}.jsonl',
                      ROOT / 'data/raw' / rev / f'{split}.jsonl', None))
    files.append((f'https://huggingface.co/datasets/{CONFIG["dataset_repo"]}/resolve/{rev}/README.md',
                  ROOT / 'data/raw' / rev / 'README.md', None))
    for path in ('README.md','TEST_CATEGORIES.md','pyproject.toml'):
        url = f'https://raw.githubusercontent.com/{CONFIG["bfcl_repo"]}/{CONFIG["bfcl_commit"]}/berkeley-function-call-leaderboard/{path}'
        files.append((url, ROOT / 'vendor/BFCL-docs' / path, None))
    def fetch(item):
        url, target, blob_sha = item
        payload = target.read_bytes() if target.exists() else get(url)
        relative = str(target.relative_to(ROOT)).replace('\\','/')
        actual_sha = hashlib.sha256(payload).hexdigest()
        if relative in expected_hashes and actual_sha != expected_hashes[relative]:
            raise RuntimeError(f'Pinned source integrity mismatch: {relative}')
        if blob_sha:
            actual = hashlib.sha1(f'blob {len(payload)}\0'.encode() + payload).hexdigest()
            if actual != blob_sha:
                raise RuntimeError(f'Git blob integrity mismatch: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open('xb') as f:
                f.write(payload)
        return {'url':url, 'path':relative,
                'bytes':len(payload), 'sha256':actual_sha, 'git_blob_sha':blob_sha}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(fetch, files))
    out = ROOT / 'evidence/sources'
    out.mkdir(parents=True, exist_ok=True)
    result = {'config':CONFIG,'files':sorted(manifest,key=lambda x:x['path'])}
    if existing and result != existing:
        raise RuntimeError('Pinned source inventory changed; preserve previous evidence and investigate')
    if not existing:
        (out / 'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        (out / 'gym-tree.json').write_bytes(tree_bytes)
    print(json.dumps({'files':len(manifest),'bytes':sum(x['bytes'] for x in manifest),'manifest':'evidence/sources/manifest.json'}))

if __name__ == '__main__':
    main()
