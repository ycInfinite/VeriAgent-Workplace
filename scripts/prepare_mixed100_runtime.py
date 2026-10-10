"""Build isolated MIX100 data admission and runner variants without changing S100."""
import ast,difflib,hashlib,json
from pathlib import Path
from common import ROOT
from veriagent.sft_stage import read,sha,schedule
from veriagent.sft_data import content_sha256

OUT=ROOT/'experiments/MIX100-PREP-20261010-001'
REVIEW=ROOT/'experiments/NOOP-REVIEW-20261010-001'

def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False)
def change(source,dest,replacements):
    before=source.read_text(encoding='utf-8');after=before
    for old,new in replacements:
        assert after.count(old)==1,(source.name,old)
        after=after.replace(old,new)
    compile(after,str(dest),'exec')
    with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(after)
    return {'source':str(source.relative_to(ROOT)).replace('\\','/'),'target':str(dest.relative_to(ROOT)).replace('\\','/'),
        'source_canonical_LF_sha256':hashlib.sha256(before.encode()).hexdigest(),'target_sha256':sha(dest),'replacements':replacements}, ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=source.name,tofile=dest.name))


def main():
    assert not (OUT/'result.json').exists()
    original=read(ROOT/'configs/sft_scale_plan_v2.json');selection=read(REVIEW/'mixed100_selection.json')['MIX100']
    oldreviews=read(ROOT/original['quality_approvals'])['approved'];newreviews=read(REVIEW/'quality_approvals.json')['approved']
    assert not {x['task_uid'] for x in oldreviews}&{x['task_uid'] for x in newreviews}
    write(OUT/'quality_approvals.json',{'approved':oldreviews+newreviews,'scope':'Original137 unchanged plus29 newlyqualified no-ops','source_sha256':[sha(ROOT/original['quality_approvals']),sha(REVIEW/'quality_approvals.json')]})
    cfg=dict(original);cfg.update(research_stage='MATCHED_BUDGET_NOOP_MIXTURE',
        selection_manifest='experiments/NOOP-REVIEW-20261010-001/mixed100_selection.json',
        quality_approvals='experiments/MIX100-PREP-20261010-001/quality_approvals.json',
        comparison_token_deltas=read(REVIEW/'mixed100_selection.json')['relative_tokens_vs_S100'],
        **{'Research Question':'At100tasks/310updates/near-equal tokens,does replacing20 action tasks with reviewed evidence-basedno-op tasks reduce unnecessarymutations withoutlosing requiredactions?',
           'Hypothesis':'No-op coverage may improve conditionalrestraint;increasedrefusals or lowernonemptysuccess arepossible. No causalresult established.',
           'Independent Variable':'MIX100=80originalS100+20newwholeapprovedno-op tasks. Replacingdataalsochangesspecifictaskcoverage;notpurelabeltoggle.',
           'Controlled Variables':['samefreshQwen3-8B','sameLoRA/optimizer/lr/seed42','100tasks20/domain','oneepoch310updates','processed+1.3869%,target+1.3707%vsS100','same8K/6rounds/2048output/B1','samefixeddev24x42,43','fixedfinalcheckpoint'],
           'Metrics':['officialsuccess overall/nonempty/empty','unnecessarymutationonemptytasks with semanticreview','wrongrefusal/prematurestoponnonemptytasks','tokens/steps/latency/VRAM/GPUhours','pairedtaskcluster MIX100-S100'],
           'Evidence Gate':'29noopsreviewed andwholeencoded;20selectedwithcompleteobservations;unchangedS100;100trainingtasksdisjointfromdev;actualHF/GPU/CE/gradient/reloadgate before48rollout evaluation.',
           'Cost Bound':'PREPARATIONONLYnow;singlePRO600096GBwhenavailable,310updates<=60min/eval48<=30min. Estimate0.3-0.5scriptGPUh perarm,notmeasured. Maxsample7756within8192;newVRAMunmeasured.',
           'Failure Branch':'HoldandpreservefailedCPU/GPUruns;nochangedS100,nohiddencontexttruncation,newteacherAPI,rentalorRL. Ifdataeffectuncertain do notautoscale.'})
    cfg['evaluation']={**original['evaluation'],'conditions':['MIX100']}
    cfg['input_artifact_sha256']={**original['input_artifact_sha256'],**{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [REVIEW/'quality_approvals.json',REVIEW/'judgments.json',REVIEW/'mixed100_selection.json',REVIEW/'mixed100_examples.jsonl.gz',OUT/'quality_approvals.json']}}
    write(ROOT/'configs/sft_mixed100_plan.json',cfg)
    transformations=[];patches=[]
    specs=[('veriagent/sft_scale.py','veriagent/sft_mixed.py',[
        ("arm=='S100'","arm=='MIX100'"),("configs/sft_scale_plan_v2.json","configs/sft_mixed100_plan.json"),
        ("s1={x['task_uid'] for x in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}\n    require(s1<={x['task_uid'] for x in selection['tasks']},'Not nested original S1')",
         "base={x['task_uid'] for x in read(ROOT/'experiments/SFT-SCALE-PREP-20261010-002/selection.json')['S100']['tasks']}\n    require(len(base & {x['task_uid'] for x in selection['tasks']})==80,'Must retain80 originalS100')\n    require(sum(x['empty_reference'] for x in selection['tasks'])==20,'Must include20 reviewednoops')")]),
        ('scripts/run_sft_scale.py','scripts/run_sft_mixed.py',[
            ('from veriagent.sft_scale import load_inputs','from veriagent.sft_mixed import load_inputs'),
            ("choices=['S100']","choices=['MIX100']"),
            ("['configs/sft_scale_plan_v2.json','veriagent/sft_scale.py','scripts/run_sft_scale.py']","['configs/sft_mixed100_plan.json','veriagent/sft_mixed.py','scripts/run_sft_mixed.py']")]),
        ('scripts/evaluate_sft_scale.py','scripts/evaluate_sft_mixed.py',[
            ("ROOT/'configs/sft_scale_plan_v2.json'","ROOT/'configs/sft_mixed100_plan.json'"),
            ("for arm in ['S100']","for arm in ['MIX100']"),("choices=['S100']","choices=['MIX100']"),
            ("['configs/sft_scale_plan_v2.json','scripts/evaluate_sft_scale.py','veriagent/sft_stage.py']","['configs/sft_mixed100_plan.json','scripts/evaluate_sft_mixed.py','veriagent/sft_stage.py']")]),
        ('scripts/validate_sft_scale_host.py','scripts/validate_sft_mixed_host.py',[
            ('from run_sft_scale import validate_actual_tokenizer','from run_sft_mixed import validate_actual_tokenizer'),
            ('from veriagent.sft_scale import load_inputs','from veriagent.sft_mixed import load_inputs'),
            ("SFT-SCALE-REMOTE-PREP-","SFT-MIX-REMOTE-PREP-"),("load_inputs('S100')","load_inputs('MIX100')"),
            ("['configs/sft_scale_plan_v2.json','veriagent/sft_scale.py','scripts/run_sft_scale.py','scripts/evaluate_sft_scale.py','scripts/validate_sft_scale_host.py']","['configs/sft_mixed100_plan.json','veriagent/sft_mixed.py','scripts/run_sft_mixed.py','scripts/evaluate_sft_mixed.py','scripts/validate_sft_mixed_host.py']"),
            ('S100_HOST_PREFLIGHT_PASSED','MIX100_HOST_PREFLIGHT_PASSED')])]
    for old,new,replacements in specs:
        item,patch=change(ROOT/old,ROOT/new,replacements);transformations.append(item);patches.append(patch)
    write(OUT/'runner_transformations.json',{'transformations':transformations,'basis':'ExactS100sourceswithdeclareddata/armchangesonly'})
    (OUT/'runner_delta.patch').write_text(''.join(patches),encoding='utf-8',newline='\n')
    from veriagent.sft_mixed import load_inputs
    checked=load_inputs('MIX100',reencode=True)
    write(OUT/'result.json',{'status':'MIX100_CPU_PREPARED_NOT_TRAINED','tasks':100,'noops':20,'retained_S100':80,
        'examples':len(checked[2]),'planned_updates':len(checked[3]),'totals':selection['totals'],
        'max_sequence':max(e['processed_tokens'] for e in checked[2]),'relative_tokens_vs_S100':cfg['comparison_token_deltas'],
        'script_sha256':sha(Path(__file__)),'parameter_updates':0,'GPU_hours':0,'API_requests':0,
        'planned_training_id':'SFT-MIX100-20261010-001','planned_eval_id':'SFT-EVAL-MIX100-20261010-001'})
    print(json.dumps(read(OUT/'result.json')))


if __name__=='__main__':main()
