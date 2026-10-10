"""Paired MIX100/S100 reporting with exact recorded runner transformations."""
import argparse,json,hashlib
import numpy as np
from run_day3 import ROOT,write
from veriagent.sft_stage import read,require


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    groups={};identities={};trains={}
    for arm in ['S100','MIX100']:
        folder=ROOT/'experiments'/f'SFT-EVAL-{arm}-20261010-001'
        result=read(folder/'result.json');identity=read(folder/'identity.json')
        require(result['status']=='MATCHED_DEV_EVAL_COMPLETE' and result['condition']==arm,'Incomplete/wrong condition')
        rows=[json.loads(x) for x in (folder/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        require(len(rows)==48 and all(not r['infra_invalid'] for r in rows),'Need48 valid trajectories perarm')
        groups[arm]={(r['task_uid'],r['seed']):r for r in rows};identities[arm]=identity
        train=ROOT/'experiments'/identity['policy_identity']['adapter']['training_run']
        trains[arm]={'config':read(train/'config.json'),'identity':read(train/'identity.json'),'result':read(train/'result.json')}
        require(trains[arm]['result']['status']=='SFT_TRAINING_COMPLETE_RELOAD_PASSED','Unqualified training')
    for k in ['data_sha256','seeds','gpu','packages']:require(identities['S100'][k]==identities['MIX100'][k],'Eval control differs: '+k)
    for k in ['model_revision','epochs','seed','learning_rate','weight_decay','max_grad_norm','lora_rank','lora_alpha','lora_dropout','target_modules','required_packages','max_context_tokens','optimizer_steps_per_arm','B1_addition','weight_and_tokenizer_sha256']:
        require(trains['S100']['config'][k]==trains['MIX100']['config'][k],'Training control differs: '+k)
    require(trains['S100']['identity']['gpu']==trains['MIX100']['identity']['gpu'],'Training GPU differs')
    old={x['path']:x['sha256'] for x in trains['S100']['identity']['deployment']['files']}
    new={x['path']:x['sha256'] for x in trains['MIX100']['identity']['deployment']['files']}
    require(all(new.get(k)==v for k,v in old.items()),'Existing deployment files changed')
    for t in read(ROOT/'experiments/MIX100-PREP-20261010-001/runner_transformations.json')['transformations']:
        source=(ROOT/t['source']).read_text(encoding='utf-8')
        require(hashlib.sha256(source.encode()).hexdigest()==old[t['source']]==t['source_canonical_LF_sha256'],'Original source identity changed')
        for before,after in t['replacements']:
            require(source.count(before)==1,'Unexpected source structure');source=source.replace(before,after)
        require(hashlib.sha256(source.encode()).hexdigest()==new[t['target']]==t['target_sha256'],'Unexpected mixed runner changes')
    keys=set(groups['S100']);require(len(keys)==48 and keys==set(groups['MIX100']),'Pairing mismatch')
    uids=sorted({u for u,s in keys});report={'scope':'Exposeddevonly;20noopsreplace20actiontasks atnear-fixedbudget',
        'primary':'Empty-reference tasksuccess with manual restraint audit;also report nonemptytask regression',
        'limitations':'Only4 empty-reference taskclusters;officialreward cannot certify correctlookup orjustifiedrestraint',
        'semantic_rates':'Require new per-trajectory review;not inferred from reward','strata':{}}
    for label,ids in [('all',uids),('nonempty',[u for u in uids if groups['S100'][(u,42)]['reference']]),('empty',[u for u in uids if not groups['S100'][(u,42)]['reference']])]:
        scores={arm:np.array([sum(rows[(u,s)]['verifier']['official_reward']==1 for s in [42,43])/2 for u in ids]) for arm,rows in groups.items()}
        delta=scores['MIX100']-scores['S100'];ix=np.random.default_rng(20260917).integers(0,len(ids),(10000,len(ids)))
        report['strata'][label]={'taskclusters':len(ids),'rates':{k:float(v.mean()) for k,v in scores.items()},
            'MIX100_minus_S100':float(delta.mean()),'taskcluster95CI':np.quantile(delta[ix].mean(axis=1),[.025,.975]).tolist()}
    out=(ROOT/a.output).resolve();require(out.is_relative_to(ROOT) and not out.exists(),'Invalid/used output');out.parent.mkdir(parents=True,exist_ok=True);write(out,report);print(json.dumps(report))


if __name__=='__main__':main()
