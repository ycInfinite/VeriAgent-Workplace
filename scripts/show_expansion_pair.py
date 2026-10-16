"""Lossless compact display of frozen91 teacher/S1 trajectories, no model calls."""
import argparse,gzip,json,sys
from common import ROOT
from show_noop_review import compact
from veriagent.sft_data import content_sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('ids',nargs='+',type=int)
    p.add_argument('--side',choices=['both','teacher','S1'],default='both');p.add_argument('--dedup',action='store_true');a=p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    with gzip.open(ROOT/'experiments/S1-EXPAND-PREP-20261016-001/teacher_records.jsonl.gz','rt',encoding='utf-8') as f:teachers={x['task_id']:x for x in map(json.loads,f)}
    path=ROOT/'experiments/S1-EXPAND-ACQUIRE-20261016-001/trajectories.jsonl'
    students={x['task_id']:x for x in map(json.loads,path.read_text(encoding='utf-8').splitlines())} if path.exists() else {}
    store=ROOT/'reports/preference-expansion-20261016/rendered_observations.json'
    seen=json.loads(store.read_text(encoding='utf-8')) if a.dedup and store.exists() else {}
    for tid in a.ids:
        for side,rows in [('teacher',teachers),('S1',students)]:
            if a.side not in ['both',side]:continue
            x=rows[tid];assert x['source_pool']=='training_candidate'
            print('TASK',tid,side,'REWARD',x['verifier']['official_reward'],'END',x['termination'],'USER',x['initial_messages'][-1]['content'])
            for m in x['messages'][len(x['initial_messages']):]:
                if m['role']=='assistant':print('A',json.dumps(m.get('content',''),ensure_ascii=False),'CALLS',json.dumps([c['function'] for c in m.get('tool_calls',[])],ensure_ascii=False))
                else:
                    try:value=json.loads(m['content'])
                    except (ValueError,TypeError):value=m['content']
                    h=content_sha256(value)
                    if a.dedup and h in seen:print('O_ALREADY_DISPLAYED_THIS_AUDIT',h)
                    else:print('O',h,json.dumps(compact(value),ensure_ascii=False,separators=(',',':')));seen[h]=value
    if a.dedup:
        store.parent.mkdir(parents=True,exist_ok=True);store.write_text(json.dumps(seen,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')


if __name__=='__main__':main()
