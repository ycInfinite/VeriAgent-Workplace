"""CPU integrity controls for evidence-based no-op and whole mixed100 admission."""
import ast,copy,gzip,json
from collections import Counter
from common import ROOT
from veriagent.sft_stage import read,sha,validate_example
from veriagent.sft_mixed import load_inputs


def main():
    output=ROOT/'experiments/MIX100-PREP-20261010-001/cpu_controls.json';assert not output.exists()
    review=ROOT/'experiments/NOOP-REVIEW-20261010-001';cfg,selection,examples,order=load_inputs('MIX100',reencode=True)
    manifest=read(review/'manifest.json');quality=read(review/'quality_approvals.json');checks={}
    checks['all83_disposed']=len(quality['approved'])+len(quality['held'])==83
    checks['29_unique_approved']=len({x['task_uid'] for x in quality['approved']})==29
    checks['all_approvals_whole_semantic']=all(x['whole_semantic_review_done'] and x['all_supervised_turns_acceptable'] for x in quality['approved'])
    allowed={x['task_uid'] for x in quality['approved']};selected_noops=[x for x in selection['tasks'] if x['empty_reference']]
    checks['20_approved_noops_only']=len(selected_noops)==20 and all(x['task_uid'] in allowed for x in selected_noops)
    checks['no_held_task_selected']=not {x['task_uid'] for x in quality['held']}&{x['task_uid'] for x in selection['tasks']}
    checks['100_unique_tasks']=len({x['task_uid'] for x in selection['tasks']})==100
    checks['five_domain_quotas']=sorted(Counter(x['category'] for x in selection['tasks']).values())==[20]*5
    checks['310_samples_once']=len(examples)==len(order)==len({x['example_index'] for x in order})==310
    checks['S100_exact_hashes_preserved']=all(sha(ROOT/p)==h for p,h in manifest['frozen_S100_sha256'].items())
    checks['8K_not_expanded']=max(e['processed_tokens'] for e in examples)<=cfg['max_context_tokens']==8192
    for name,edit in [('dev',lambda x:x.update(source_pool='development')),('context_loss',lambda x:x['labels'].__setitem__(0,x['input_ids'][0])),('partial_targets',lambda x:x['labels'].__setitem__(x['prefix_tokens'],-100))]:
        value=copy.deepcopy(examples[0]);edit(value)
        try:validate_example(value);checks['reject_'+name]=False
        except ValueError:checks['reject_'+name]=True
    def find(path,kind,prefix):
        return next(n for n in ast.walk(ast.parse((ROOT/path).read_text(encoding='utf-8'))) if isinstance(n,kind) and ast.unparse(n).startswith(prefix))
    for label,old,new,kind,prefix in [
        ('optimizer','scripts/run_sft_scale.py','scripts/run_sft_mixed.py',ast.For,'for number, item'),
        ('reload','scripts/run_sft_scale.py','scripts/run_sft_mixed.py',ast.FunctionDef,'def readout('),
        ('rollout','scripts/evaluate_sft_scale.py','scripts/evaluate_sft_mixed.py',ast.For,'for seed')]:
        checks[label+'_AST_identical']=ast.dump(find(old,kind,prefix))==ast.dump(find(new,kind,prefix))
    assert all(checks.values()),checks
    result={'status':'CPU_CONTROLS_PASSED','checks':checks,'count':len(checks),'model_loaded':False,'parameter_updates':0,
        'pending':'actualHFtokenizer/GPU/CE/gradients/VRAM/adapterreload and newAgent eval'}
    output.write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n');print(json.dumps(result))


if __name__=='__main__':main()
