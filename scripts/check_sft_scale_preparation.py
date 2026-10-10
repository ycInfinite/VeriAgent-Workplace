"""CPU regression gates for the new data path and unchanged optimization/eval loops."""
import ast,copy,hashlib,json
from pathlib import Path
from common import ROOT
from veriagent.sft_scale import load_inputs
from veriagent.sft_stage import validate_example,read
import github_file_sync as sync


def main():
    out=ROOT/'experiments/SFT-SCALE-PREP-20261010-002/cpu_controls.json'
    assert not out.exists(),'Immutable control receipt exists'
    cfg,selection,examples,order=load_inputs('S100',reencode=True);checks={}
    checks['100_unique_whole_tasks']=len({x['task_uid'] for x in selection['tasks']})==100
    checks['310_distinct_examples_once']=len(order)==310 and len({x['example_index'] for x in order})==310
    checks['same_original_S1_nested']=len({x['task_uid'] for x in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']} & {x['task_uid'] for x in selection['tasks']})==50
    for label,mutator in [('context_target',lambda x:x['labels'].__setitem__(0,x['input_ids'][0])),
                          ('dev_source',lambda x:x.update(source_pool='development')),
                          ('selective_target',lambda x:x['labels'].__setitem__(x['prefix_tokens'],-100))]:
        bad=copy.deepcopy(examples[0]);mutator(bad)
        try:validate_example(bad);checks['reject_'+label]=False
        except ValueError:checks['reject_'+label]=True
    def node(path,kind,start):
        tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
        return next(n for n in ast.walk(tree) if isinstance(n,kind) and ast.unparse(n).startswith(start))
    checks['optimizer_loop_AST_identical']=ast.dump(node('scripts/run_sft_comparison.py',ast.For,'for number, item'))==ast.dump(node('scripts/run_sft_scale.py',ast.For,'for number, item'))
    checks['readout_AST_identical']=ast.dump(node('scripts/run_sft_comparison.py',ast.FunctionDef,'def readout('))==ast.dump(node('scripts/run_sft_scale.py',ast.FunctionDef,'def readout('))
    checks['rollout_loop_AST_identical']=ast.dump(node('scripts/evaluate_sft_comparison.py',ast.For,'for seed'))==ast.dump(node('scripts/evaluate_sft_scale.py',ast.For,'for seed'))
    checks['original_eval_unchanged_except_label']=all(cfg['evaluation'][k]==v for k,v in read(ROOT/'configs/sft_comparison_plan.json')['evaluation'].items() if k!='conditions')
    tree=ast.parse(sync.REMOTE_CODE)
    value=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sft_scale_files' for t in n.targets))
    checks['exact_local_remote_deployment_whitelist']=set(sync.SFT_SCALE_FILES)==ast.literal_eval(value)
    checks['only7_new_execution_files']=len(sync.SFT_SCALE_FILES)==7 and all((ROOT/p).is_file() for p in sync.SFT_SCALE_FILES)
    checks['failed_v1_config_not_deployable']='configs/sft_scale_plan.json' not in sync.SFT_SCALE_FILES
    assert all(checks.values()),checks
    receipt={'status':'CPU_CONTROLS_PASSED','checks':checks,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Data/isolation/equivalence checks; actual Transformers,CUDA,CE,gradient,VRAM/reload remain remote gates',
        'model_loaded':False,'parameter_updates':0}
    out.write_text(json.dumps(receipt,indent=2),encoding='utf-8',newline='\n');print(json.dumps(receipt))


if __name__=='__main__':main()
