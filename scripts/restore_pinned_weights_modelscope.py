"""Transport-only fallback: official Qwen mirror, exact pre-registered SHA256 required."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,os,re,time,urllib.request,urllib.parse

ROOT=Path(__file__).resolve().parents[1]

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    cfg=json.loads((ROOT/'configs/sft_comparison_plan.json').read_text())
    target=ROOT/cfg['weights_path'];target.mkdir(parents=True,exist_ok=True)
    weights={n:h for n,h in cfg['weight_and_tokenizer_sha256'].items() if n.endswith('.safetensors')}
    started=time.time()
    def one(item):
        name,expected=item;dest=target/name;part=target/(name+'.modelscope.part')
        if dest.exists():
            if digest(dest)!=expected:raise ValueError('Conflicting final shard')
            return {'file':name,'sha256':expected,'reused_final':True}
        partials=list((target/'.cache/huggingface/download').glob('*.'+expected+'.incomplete'))
        if not part.exists() and partials:os.link(partials[0],part)
        for attempt in range(3):
            offset=part.stat().st_size if part.exists() else 0
            url='https://modelscope.cn/api/v1/models/Qwen/Qwen3-8B/repo?'+urllib.parse.urlencode({'Revision':'master','FilePath':name})
            try:
                req=urllib.request.Request(url,headers={'Range':f'bytes={offset}-','User-Agent':'VeriAgent-public-pinned-weight-recovery'})
                with urllib.request.urlopen(req,timeout=45) as response:
                    match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                    if response.status!=206 or not match or int(match[1])!=offset:raise ValueError('Bad range response')
                    total=int(match[3]);assert offset<=total<=5*2**30
                    with part.open('ab') as f:
                        while block:=response.read(1024*1024):
                            f.write(block)
                            if f.tell()>total:raise ValueError('Unexpected oversized response')
                if part.stat().st_size!=total:raise OSError('Incomplete range')
                break
            except (OSError,urllib.error.URLError):
                if attempt==2:raise
                time.sleep(attempt+1)
        actual=digest(part)
        if actual!=expected:raise ValueError('Mirror differs from frozen HF revision; never use it')
        os.replace(part,dest)
        result={'file':name,'bytes':dest.stat().st_size,'sha256':actual,'frozen_revision_hash_match':True}
        print(json.dumps(result),flush=True);return result
    status=ROOT/'logs/modelscope_restore_status.json'
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(one,weights.items()))
        value={'status':'ALL5_SHARDS_MATCH_FROZEN_HF_HASHES','files':results,'seconds':time.time()-started,
               'transport':'Qwen official ModelScope public mirror master; content identity constrained by existing frozen HF hashes',
               'model_revision':cfg['model_revision'],'model_loaded':False,'parameter_updates':0}
        status.write_text(json.dumps(value,indent=2));print(json.dumps(value),flush=True)
    except Exception as e:
        status.write_text(json.dumps({'status':'RESTORE_FAILED','error_type':type(e).__name__,'seconds':time.time()-started}))
        print(json.dumps({'status':'RESTORE_FAILED','error_type':type(e).__name__}),flush=True);raise SystemExit(1)

if __name__=='__main__':main()
