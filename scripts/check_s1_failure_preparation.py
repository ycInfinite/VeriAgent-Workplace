"""Training cohort isolation/collector equivalence and deployment controls."""
import ast,copy,json
from common import ROOT
from collect_s1_failures import load_eval
from veriagent.sft_stage import read,sha
import github_file_sync as sync


def main():
    out=ROOT/'experiments/S1-FAILURE-PREP-20261012-002/cpu_controls.json';assert not out.exists()
    cfg,_,rows=load_eval();checks={}
    checks['25unique_training_only']=len({r['task_uid'] for r in rows})==25 and all(r['source_pool']=='training_candidate' for r in rows)
    s1={r['task_uid'] for r in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}
    dev=set(read(ROOT/'configs/preference_comparison_plan.json')['evaluation']['task_uids'])
    checks['S1_and_dev_disjoint']=not {r['task_uid'] for r in rows}&(s1|dev)
    selected=read(ROOT/cfg['selection_manifest'])['tasks']
    checks['20action5empty']=sum(r['empty_reference'] for r in selected)==5
    checks['5per_domain']=all(sum(r['category']==d for r in selected)==5 for d in {r['category'] for r in selected})
    checks['one_seed_no_retry']=cfg['seeds']==[42] and cfg['max_tasks']==25
    checks['same_S1_identity']=cfg['initial_adapter_sha256']==read(ROOT/'configs/dpo_probe_plan.json')['initial_adapter_sha256']
    checks['generation_bounds_unchanged']=all(cfg[k]==v for k,v in read(ROOT/'configs/preference_comparison_plan.json')['evaluation'].items() if k in ['temperature','top_p','max_model_rounds','max_context_tokens','max_output_tokens_per_model_call','max_output_tokens_per_trajectory'])
    # The only scientific inference-loop changes are pool and record labels.
    def loop(path):
        return next(n for n in ast.walk(ast.parse((ROOT/path).read_text(encoding='utf-8'))) if isinstance(n,ast.For) and ast.unparse(n).startswith('for seed'))
    actual=ast.unparse(loop('scripts/collect_s1_failures.py'))
    expected=ast.unparse(loop('scripts/evaluate_preference_comparison.py')).replace("source_pool='development'","source_pool='training_candidate'").replace("'comparison_condition': args.condition","'acquisition_condition': 'S1_TRAIN25'")
    checks['original_inference_loop_except_pool_label']=actual==expected
    tree=ast.parse(sync.REMOTE_CODE)
    remote=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='s1_failure_files' for t in n.targets))
    checks['exact4file_whitelist']=set(sync.S1_FAILURE_FILES)==remote==set(cfg['deployment_files']) and len(remote)==4
    checks['teacher_not_new_collector_payload']=cfg['teacher_artifact'] not in remote
    checks['no_optimizer_or_generation_rewrite']='torch.optim' not in (ROOT/'scripts/collect_s1_failures.py').read_text(encoding='utf-8')
    assert all(checks.values()),checks
    result={'status':'CPU_CONTROLS_PASSED','checks':checks,'sources':{p:sha(ROOT/p) for p in cfg['deployment_files']},'actual_HF_GPU':'unmeasured_required_on_host','parameter_updates':0}
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({'status':result['status'],'checks':len(checks)}))


if __name__=='__main__':main()
