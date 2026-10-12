"""Matched exposed-dev outcomes; never selects checkpoints or changes labels."""
import argparse,json,hashlib
import numpy as np
from common import ROOT
from veriagent.sft_stage import read,require,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args()
    cfg=read(ROOT/'configs/preference_comparison_plan.json');groups={};identities={};results={}
    for arm,run in cfg['eval_run_ids'].items():
        folder=ROOT/'experiments'/run;r=read(folder/'result.json');i=read(folder/'identity.json')
        require(r['status']=='MATCHED_DEV_EVAL_COMPLETE' and r['valid_rollouts']==48 and r['infra_invalid_rollouts']==0,'Incomplete eval')
        records=[json.loads(l) for l in (folder/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        groups[arm]={(r['task_uid'],r['seed']):r for r in records};identities[arm]=i;results[arm]=r
        require(len(groups[arm])==48,'Duplicate taskseed')
        require(i['policy_identity']['condition']==arm,'Wrong adapter label')
    for arm in cfg['conditions']:
        require(set(groups[arm])==set(groups['S1']),'Pairing mismatch')
        for k in ['code_commit','data_sha256','seeds','gpu','packages']:require(identities[arm][k]==identities['S1'][k],'Eval control differs:'+k)
    for arm,run in cfg['training_run_ids'].items():
        p=ROOT/'experiments'/run;tc=read(p/'config.json');tr=read(p/'result.json')
        require(tc=={**cfg,'condition':arm} and tr['status']=='PREFERENCE_TRAINING_COMPLETE_RELOAD_PASSED' and tr['optimizer_updates']==12,'Training protocol mismatch')
        require(identities[arm]['policy_identity']['adapter']['files']==read(p/'adapter_manifest.json'),'Eval adapter changed')
    require(identities['S1']['policy_identity']['adapter']['files']==cfg['initial_adapter_sha256'],'Baseline not original S1')
    uids=sorted({u for u,s in groups['S1']});report={'primary':cfg['primary'],'scope':'exposeddev24,one trainingseed;notsealedgeneralization','results':results,'comparisons':{},'source_hashes':{a:sha(ROOT/'experiments'/r/'trajectories.jsonl') for a,r in cfg['eval_run_ids'].items()}}
    for new,old in [('DPO','CHOSEN_SFT'),('CHOSEN_SFT','S1'),('DPO','S1')]:
        d={}
        for label,ids in [('all',uids),('nonempty',[u for u in uids if groups['S1'][(u,42)]['reference']]),('empty',[u for u in uids if not groups['S1'][(u,42)]['reference']])]:
            scores={a:np.array([sum(groups[a][(u,s)]['verifier']['official_reward']==1 for s in [42,43])/2 for u in ids]) for a in [new,old]}
            delta=scores[new]-scores[old];ix=np.random.default_rng(20260917).integers(0,len(ids),(10000,len(ids)))
            d[label]={'taskclusters':len(ids),'rates':{k:float(v.mean()) for k,v in scores.items()},'delta':float(delta.mean()),'taskcluster95CI':np.quantile(delta[ix].mean(1),[.025,.975]).tolist()}
        report['comparisons'][new+'_minus_'+old]=d
    path=(ROOT/a.output).resolve();require(path.is_relative_to(ROOT) and not path.exists(),'Used or invalid output');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['comparisons']))


if __name__=='__main__':main()
