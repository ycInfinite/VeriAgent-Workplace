"""Paired development-only S1/S2 comparison after three complete authorized runs."""
import argparse,json
import numpy as np
from run_day3 import ROOT,write
from veriagent.sft_stage import read,require


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--s1',required=True);p.add_argument('--s2',required=True)
    p.add_argument('--output',required=True);a=p.parse_args();groups={};identities={}
    for condition,name in [('BASE_B1',a.base),('S1',a.s1),('S2',a.s2)]:
        path=(ROOT/'experiments'/name).resolve();require(path.is_relative_to(ROOT/'experiments'),'Run outside experiments')
        result=read(path/'result.json');identity=read(path/'identity.json')
        require(result['status']=='MATCHED_DEV_EVAL_COMPLETE' and result['condition']==condition,'Incomplete/wrong evaluation run')
        rows=[json.loads(line) for line in (path/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        require(len(rows)==48 and not any(r['infra_invalid'] for r in rows),'Paired report needs all48valid; do not hide invalid attempts')
        indexed={(r['task_uid'],r['seed']):r for r in rows};require(len(indexed)==48,'Duplicate task/seed')
        groups[condition]=indexed;identities[condition]=identity
    for field in ['data_sha256','seeds','gpu','packages','code_commit']:
        require(all(x[field]==identities['BASE_B1'][field] for x in identities.values()),'Controlled variable differs: '+field)
    for field in ['training_gpu','training_code_commit']:
        require(identities['S1']['policy_identity']['adapter'][field]==identities['S2']['policy_identity']['adapter'][field],
                'Training control differs: '+field)
    require(all(set(x)==set(groups['BASE_B1']) for x in groups.values()),'Paired task/seed set differs')
    keys=sorted(groups['BASE_B1']);uids=sorted({k[0] for k in keys})
    strata={'all':uids,'nonempty_reference':[u for u in uids if groups['BASE_B1'][(u,42)]['reference']],
            'empty_reference':[u for u in uids if not groups['BASE_B1'][(u,42)]['reference']]}
    report={'status':'DEVELOPMENT_COMPARISON_NOT_FINAL_GENERALIZATION','primary_contrast':'S2-S1 nonempty-reference task success',
            'bootstrap':'10000 paired task-cluster resamples,seed20260917; both rollout seeds stay inside each task',
            'semantic_metrics':'Require new per-call/trajectory annotations; automatic diagnostics are not semantic review',
            'checkpoint_selection':'Fixedfinal; these results do not retroactively select a checkpoint','strata':{}}
    for stratum,ids in strata.items():
        values={c:np.array([sum(g[(u,seed)]['verifier']['official_reward']==1 for seed in [42,43])/2 for u in ids]) for c,g in groups.items()}
        scores={c:float(v.mean()) for c,v in values.items()};comparisons={}
        rng=np.random.default_rng(20260917);resamples=rng.integers(0,len(ids),size=(10000,len(ids)))
        for c,b in [('S1','BASE_B1'),('S2','BASE_B1'),('S2','S1')]:
            delta=values[c]-values[b];interval=np.quantile(delta[resamples].mean(axis=1),[.025,.975])
            comparisons[c+'-'+b]={'difference':float(delta.mean()),'task_cluster_95percent_interval':interval.tolist(),
                                  'tasks_improved':int((delta>0).sum()),'tasks_worsened':int((delta<0).sum())}
        report['strata'][stratum]={'unique_tasks':len(ids),'rollouts_per_condition':len(ids)*2,'success_rates':scores,'comparisons':comparisons}
    dest=(ROOT/a.output).resolve();require(dest.is_relative_to(ROOT),'Output outside root');require(not dest.exists(),'Immutable report exists')
    dest.parent.mkdir(parents=True,exist_ok=True);write(dest,report);print(json.dumps(report))


if __name__=='__main__':main()
