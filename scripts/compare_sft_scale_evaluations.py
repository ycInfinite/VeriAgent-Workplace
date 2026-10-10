"""Post-hoc paired S100 vs S1; exact shared inference and normalized train loop gates."""
import argparse,json,hashlib
import numpy as np
from run_day3 import ROOT,write
from veriagent.sft_stage import read,require


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    groups={};identities={};train={}
    for arm in ['S1','S100']:
        root=ROOT/'experiments'/f'SFT-EVAL-{arm}-20261010-001';result=read(root/'result.json');identity=read(root/'identity.json')
        require(result['status']=='MATCHED_DEV_EVAL_COMPLETE','Incomplete evaluation')
        rows=[json.loads(x) for x in (root/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        require(len(rows)==48 and all(not x['infra_invalid'] for x in rows),'All48 valid required')
        groups[arm]={(x['task_uid'],x['seed']):x for x in rows};identities[arm]=identity
        tr=ROOT/'experiments'/identity['policy_identity']['adapter']['training_run']
        train[arm]={'identity':read(tr/'identity.json'),'config':read(tr/'config.json'),'result':read(tr/'result.json')}
        require(train[arm]['result']['status']=='SFT_TRAINING_COMPLETE_RELOAD_PASSED','Unqualified training')
    for k in ['data_sha256','seeds','gpu','packages']:
        require(identities['S1'][k]==identities['S100'][k],'Eval control differs: '+k)
    for k in ['model_revision','seed','learning_rate','weight_decay','max_grad_norm','lora_rank','lora_alpha','lora_dropout','target_modules','required_packages','max_context_tokens','optimizer_steps_per_arm','B1_addition','weight_and_tokenizer_sha256']:
        require(train['S1']['config'][k]==train['S100']['config'][k],'Training control differs: '+k)
    old={x['path']:x['sha256'] for x in train['S1']['identity']['deployment']['files']}
    new={x['path']:x['sha256'] for x in train['S100']['identity']['deployment']['files']}
    # Every original deployment file must remain unchanged; new scale entries are additive.
    require(all(new.get(k)==v for k,v in old.items()),'Shared deployed inference/environment/source changed')
    checks=read(ROOT/'experiments/SFT-SCALE-PREP-20261010-002/source_line_ending_checks.json')
    for path,check in checks.items():require(old[path]==check['canonical_LF_sha256'],'Frozen runner provenance mismatch')
    for oldpath,newpath,replacements in [
        ('scripts/run_sft_comparison.py','scripts/run_sft_scale.py',[
            ('from veriagent.sft_stage import load_inputs,validate_deployment,verify_weights,require,sha','from veriagent.sft_stage import validate_deployment,verify_weights,require,sha\nfrom veriagent.sft_scale import load_inputs'),
            ("choices=['S1','S2']","choices=['S100']"),
            ("['configs/sft_comparison_plan.json','veriagent/sft_stage.py','scripts/run_sft_comparison.py']","['configs/sft_scale_plan_v2.json','veriagent/sft_scale.py','scripts/run_sft_scale.py']"),
            ("'training_tasks':50","'training_tasks':100")]),
        ('scripts/evaluate_sft_comparison.py','scripts/evaluate_sft_scale.py',[
            ("ROOT/'configs/sft_comparison_plan.json'","ROOT/'configs/sft_scale_plan_v2.json'"),
            ("for arm in ['S1','S2']","for arm in ['S100']"),
            ("choices=['BASE_B1','S1','S2']","choices=['S100']"),
            ("['configs/sft_comparison_plan.json','scripts/evaluate_sft_comparison.py','veriagent/sft_stage.py']","['configs/sft_scale_plan_v2.json','scripts/evaluate_sft_scale.py','veriagent/sft_stage.py']")])]:
        text=(ROOT/oldpath).read_text(encoding='utf-8');require(hashlib.sha256(text.encode()).hexdigest()==old[oldpath],'Old runner changed')
        for x,y in replacements:require(text.count(x)==1,'Unexpected runner structure');text=text.replace(x,y)
        require(hashlib.sha256(text.encode()).hexdigest()==new[newpath],'New runner changes beyond allowed data/arm metadata')
    keys=set(groups['S1']);require(len(keys)==48 and keys==set(groups['S100']),'Task/seed mismatch')
    uids=sorted({u for u,s in keys});report={'scope':'Exposed development only,nesteddata diversity x repetition change at near-fixedbudget','comparison':'S100-S1','strata':{}}
    for label,selected in [('all',uids),('nonempty',[u for u in uids if groups['S1'][(u,42)]['reference']]),('empty',[u for u in uids if not groups['S1'][(u,42)]['reference']])]:
        values={arm:np.array([sum(rows[(u,s)]['verifier']['official_reward']==1 for s in [42,43])/2 for u in selected]) for arm,rows in groups.items()}
        delta=values['S100']-values['S1'];rng=np.random.default_rng(20260917);ix=rng.integers(0,len(selected),size=(10000,len(selected)))
        report['strata'][label]={'tasks':len(selected),'rates':{k:float(v.mean()) for k,v in values.items()},'difference':float(delta.mean()),'task_cluster95CI':np.quantile(delta[ix].mean(axis=1),[.025,.975]).tolist()}
    out=(ROOT/a.output).resolve();require(out.is_relative_to(ROOT) and not out.exists(),'Invalid/used output');out.parent.mkdir(parents=True,exist_ok=True);write(out,report);print(json.dumps(report))


if __name__=='__main__':main()
