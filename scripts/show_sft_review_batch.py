"""Print bounded full visible traces for manual Codex review; never admit data."""
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('domain');p.add_argument('start',type=int);p.add_argument('count',type=int)
a=p.parse_args()
source=ROOT/'experiments/DEEPSEEK-SFTDATA-20260917-001'
rows={r['task_id']:r for r in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
manifest=json.loads((ROOT/'experiments/SFT-READY-20260917-001/review_manifest.json').read_text(encoding='utf-8'))
selected=[t for t in manifest['tasks'] if a.domain in t['category']][a.start:a.start+a.count]
for t in selected:
    r=rows[t['task_id']]
    print('TASK',r['task_id'],'USER',json.dumps(r['initial_messages'][-1]['content']))
    for m in r['messages'][len(r['initial_messages']):]:
        if m['role']=='assistant':
            print('A',json.dumps(m.get('content','')),'C',json.dumps([c['function'] for c in m.get('tool_calls',[])]))
        else:print('O',json.dumps(json.loads(m['content']),separators=(',',':')))
