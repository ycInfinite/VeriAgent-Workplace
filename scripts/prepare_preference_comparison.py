"""Freeze evidence gates for the bounded12-task two-objective comparison."""
import ast,hashlib,json
from pathlib import Path
from common import ROOT
from veriagent.dpo import load_pairs
from veriagent.sft_stage import read,sha
from evaluate_preference_comparison import load_eval


def main():
    out=ROOT/'experiments/PREF-PREP-20261012-001';out.mkdir(exist_ok=False)
    cfg,pairs=load_pairs('configs/preference_comparison_plan.json');_,ev,rows=load_eval()
    def save(name,x):(out/name).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8',newline='\n')
    save('config.json',cfg)
    checks={}
    try:
        checks['12distinct_pairs_once']=len(cfg['task_order'])==len(set(cfg['task_order']))==12 and set(cfg['task_order'])=={p['task_id'] for p in pairs}
        checks['train_dev_disjoint']=not {p['task_uid'] for p in pairs}&{r['task_uid'] for r in rows}
        checks['unchanged12pair_archive']=cfg['pair_artifact_sha256']==read(ROOT/'configs/dpo_probe_plan.json')['pair_artifact_sha256']
        checks['S1_not_probe_start']=cfg['initial_adapter_path']=='experiments/SFT-S1-20261010-001/adapter' and cfg['initial_adapter_sha256']==read(ROOT/'experiments/SFT-S1-20261010-001/adapter_manifest.json')
        checks['same_lr_beta_seed_context']=cfg['learning_rate']==5e-6 and cfg['beta']==.1 and cfg['seed']==42 and cfg['max_context_tokens']==8192
        old=read(ROOT/'configs/sft_mixed100_plan.json')['evaluation']
        checks['all_eval_fields_unchanged_except_conditions']=all(ev[k]==v for k,v in old.items() if k!='conditions')
        def node(path,cls,prefix):
            return next(n for n in ast.walk(ast.parse((ROOT/path).read_text(encoding='utf-8'))) if isinstance(n,cls) and ast.unparse(n).startswith(prefix))
        checks['inference_loop_AST_unchanged']=ast.dump(node('scripts/evaluate_sft_mixed.py',ast.For,'for seed'))==ast.dump(node('scripts/evaluate_preference_comparison.py',ast.For,'for seed'))
        checks['readout_AST_unchanged']=ast.dump(node('scripts/run_dpo_probe.py',ast.FunctionDef,'def readout'))==ast.dump(node('scripts/run_preference_comparison.py',ast.FunctionDef,'def readout'))
        checks['HF_checker_AST_unchanged']=ast.dump(node('scripts/run_dpo_probe.py',ast.FunctionDef,'def actual_tokenizer_check'))==ast.dump(node('scripts/run_preference_comparison.py',ast.FunctionDef,'def actual_tokenizer_check'))
        for p in cfg['deployment_files']:ast.parse((ROOT/p).read_text(encoding='utf-8')) if p.endswith('.py') else read(ROOT/p)
        checks['syntax_valid']=True
        import github_file_sync as sync
        tree=ast.parse(sync.REMOTE_CODE)
        remote=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='preference_files' for t in n.targets))
        checks['deployment_whitelist_matches']=set(sync.PREFERENCE_FILES)==remote==set(cfg['deployment_files'])
        assert all(checks.values()),checks
        save('identity.json',{'parent_commit':'f7e807f44db2dc3b6174f1d64dc89af6443acdb8','sources':{p:sha(ROOT/p) for p in cfg['deployment_files']},'transport_sha256':sha(ROOT/'scripts/github_file_sync.py'),'data_sha256':cfg['pair_artifact_sha256'],'kind':'CPU_PREPARATION'})
        save('result.json',{'status':'CPU_COMPARISON_PREPARED','checks':checks,'actual_training_updates':0,'planned_training_updates_per_arm':12,'planned_eval_rollouts':144,'GPU_hours':0,'actual_host_Torch_controls':'required before training'})
        print(json.dumps({'status':'CPU_COMPARISON_PREPARED','checks':len(checks),'planned_eval_rollouts':144}))
    except Exception:
        import traceback
        save('invalid_run.json',{'checks':checks,'traceback':traceback.format_exc(),'model_run':False});raise


if __name__=='__main__':main()
