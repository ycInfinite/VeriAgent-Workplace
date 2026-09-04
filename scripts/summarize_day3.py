"""Offline, read-only analysis of real rollout evidence; candidates need human review."""
import argparse
from collections import defaultdict,Counter
import csv
import json
from pathlib import Path
import random
import statistics

ROOT=Path(__file__).resolve().parents[1]

def load(run_id):
    p=ROOT/'experiments'/run_id
    records=[json.loads(x) for x in (p/'trajectories.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    return p,records

def quantile(values,q):
    s=sorted(values);i=(len(s)-1)*q;lo=int(i);hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(i-lo)

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--b0',required=True);p.add_argument('--b1');p.add_argument('--out',required=True)
    args=p.parse_args();out=(ROOT/args.out).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output outside workspace')
    out.mkdir(parents=True,exist_ok=False)
    path,base=load(args.b0);valid=[r for r in base if not r['infra_invalid']]
    bytask=defaultdict(list)
    for r in valid:bytask[r['task_id']].append(r)
    means=[statistics.mean(r['verifier']['official_reward'] for r in rs) for rs in bytask.values()]
    rng=random.Random(20260904)
    bootstrap=[statistics.mean(rng.choices(means,k=len(means))) for _ in range(5000)] if means else []
    result={'base_run':args.b0,'attempted':len(base),'valid':len(valid),'unique_tasks':len(bytask),
            'macro_pass_at_1':statistics.mean(means) if means else None,
            'task_cluster_bootstrap_95pct':[quantile(bootstrap,.025),quantile(bootstrap,.975)] if bootstrap else None,
            'bootstrap_scope':'Resamples 24 task clusters, retaining their two seeds. Exploratory cohort uncertainty, not proof of population generalization.',
            'per_seed':{str(seed):{'n':len(rs),'successes':sum(r['verifier']['official_reward']==1 for r in rs)}
                        for seed in (42,43) for rs in [[r for r in valid if r['seed']==seed]]},
            'tasks_with_any_nonempty_success':sum(any(r['reference_action_count'] and r['verifier']['official_reward']==1 for r in rs) for rs in bytask.values()),
            'tasks_with_any_nonempty_failure':sum(any(r['reference_action_count'] and r['verifier']['official_reward']==0 for r in rs) for rs in bytask.values()),
            'noop_rollouts_without_tools':sum(not r['reference_action_count'] and not r['tool_steps'] for r in valid),
            'semantic_review_status':'PENDING; do not equate candidate heuristics to confirmed rates'}
    review=[]
    for r in base:
        item={'task_id':r['task_id'],'seed':r['seed'],'condition':r['condition'],
              'task':r['initial_messages'][-1]['content'],'reward':r['verifier']['official_reward'],
              'termination':r['termination'],'infra_invalid':r['infra_invalid'],
              'context_limit_attempt':r.get('context_limit_attempt'),
              'reference':r['reference'],'calls':[],'parse_errors':r['parse_errors'],
              'final_text':next((m.get('content','') for m in reversed(r['messages']) if m['role']=='assistant'),'')}
        for c in r['call_diagnostics']:
            event=r['events'][c['step']-1]
            item['calls'].append({**c,'observation':event['observation'],'state_changed_tables':list(event['state_changes'])})
        review.append(item)
    write(out/'review_packets.json',review)
    with (out/'task_outcomes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['task_id','seed','reward','termination','steps','input_tokens','output_tokens','seconds','infra_invalid'])
        for r in base:writer.writerow([r['task_id'],r['seed'],r['verifier']['official_reward'],r['termination'],r['tool_steps'],r['input_tokens'],r['output_tokens'],r['trajectory_latency_seconds'],r['infra_invalid']])
    if args.b1:
        _,extra=load(args.b1)
        b0_map={r['task_id']:r for r in valid if r['seed']==42}
        pairs=[(b0_map[r['task_id']],r) for r in extra if not r['infra_invalid'] and r['task_id'] in b0_map]
        deltas=[b['verifier']['official_reward']-a['verifier']['official_reward'] for a,b in pairs]
        result['paired_B1_vs_B0_seed42']={'n':len(pairs),'success_delta':sum(deltas)/len(deltas) if deltas else None,
            'improved_task_ids':[b['task_id'] for a,b in pairs if b['verifier']['official_reward']>a['verifier']['official_reward']],
            'regressed_task_ids':[b['task_id'] for a,b in pairs if b['verifier']['official_reward']<a['verifier']['official_reward']]}
    write(out/'summary.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
