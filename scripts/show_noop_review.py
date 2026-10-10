"""Lossless compact visible-message rendering for frozen83 offline manual review."""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def compact(value):
    if isinstance(value,list) and value and all(isinstance(x,dict) for x in value):
        keys=list(value[0])
        if all(list(x)==keys for x in value):return {'columns':keys,'rows':[[compact(x[k]) for k in keys] for x in value]}
    if isinstance(value,list):return [compact(x) for x in value]
    if isinstance(value,dict):return {k:compact(v) for k,v in value.items()}
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('ids',nargs='+',type=int);p.add_argument('--dedup',action='store_true');a=p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    store=ROOT/'experiments/NOOP-REVIEW-20261010-001/rendered_observations.json'
    seen=json.loads(store.read_text(encoding='utf-8')) if a.dedup and store.exists() else {}
    source=ROOT/'experiments/DEEPSEEK-SFTDATA-20260917-001/trajectories.jsonl'
    rows={r['task_id']:r for r in map(json.loads,source.read_text(encoding='utf-8').splitlines()) if not r['reference']}
    for i in a.ids:
        r=rows[i];print('TASK',i,'REWARD',r['verifier']['official_reward'],'END',r['termination'],'USER',r['initial_messages'][-1]['content'])
        for m in r['messages'][len(r['initial_messages']):]:
            if m['role']=='assistant':print('A',json.dumps(m.get('content',''),ensure_ascii=False),'CALLS',json.dumps([c['function'] for c in m.get('tool_calls',[])],ensure_ascii=False))
            else:
                try:v=json.loads(m['content'])
                except (ValueError,TypeError):v=m['content']
                key=hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if a.dedup and key in seen:print('O_ALREADY_SHOWN',key)
                else:
                    print('O',key,json.dumps(compact(v),ensure_ascii=False,separators=(',',':')))
                    seen[key]=v
    if a.dedup:store.write_text(json.dumps(seen,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')


if __name__=='__main__':main()
