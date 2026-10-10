"""Export nested100 and freeze runner deltas; CPU only, no model/API/update."""
import difflib,gzip,json,hashlib,time
from pathlib import Path
from common import ROOT
from veriagent.sft_stage import read,sha,schedule
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import CanonicalTeacherEncoder,export_teacher_turns

OUT=ROOT/'experiments/SFT-SCALE-PREP-20261010-001'
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def rewrite(source,dest,replacements):
    text=source.read_text(encoding='utf-8');original=text
    for before,after in replacements:
        assert text.count(before)==1,(source.name,before,text.count(before))
        text=text.replace(before,after)
    compile(text,str(dest),'exec')
    with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return ''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(source.relative_to(ROOT)),tofile=str(dest.relative_to(ROOT))))


def main():
    start=time.perf_counter();assert not (OUT/'identity.json').exists()
    parent=read(ROOT/'configs/sft_comparison_plan.json')
    proposal=read(ROOT/'experiments/POSTSFT-AUDIT-20261010-001/nested100_proposal.json')
    assert proposal['status']=='FEASIBLE_MANIFEST_ONLY_NOT_TRAINED'
    write(OUT/'identity.json',{'script_sha256':sha(Path(__file__)),'parent_plan_sha256':sha(ROOT/'configs/sft_comparison_plan.json'),
        'proposal_sha256':sha(ROOT/'experiments/POSTSFT-AUDIT-20261010-001/nested100_proposal.json'),
        'execution':'CPU only','authorization':'User2026-10-10 chose 100task SFT size check;DPO deferred'})
    source=ROOT/'experiments'/parent['source_run'];tc=read(source/'config.json')
    cohort={x['task_uid']:x for x in read(ROOT/tc['cohort_manifest'])['tasks']}
    records={x['task_uid']:x for x in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
    reviews={x['task_uid']:x for x in read(ROOT/parent['quality_approvals'])['approved']}
    encoder=CanonicalTeacherEncoder(8192);flat=[]
    for t in proposal['tasks']:
        r=records[t['task_uid']];assert content_sha256(r)==t['trajectory_sha256']
        examples=export_teacher_turns(r,reviews[t['task_uid']],cohort,encoder,tc,source_provider='deepseek',required_decision='approved_for_sft')
        for e in examples:e.update(source_run=parent['source_run'],student_model_revision=parent['model_revision'])
        flat.extend(examples)
    assert len(flat)==310 and len(proposal['tasks'])==100
    data=OUT/'s100_examples.jsonl.gz'
    with data.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:
        for r in flat:f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    selection={'S100':{'tasks':proposal['tasks'],'totals':{'turns':len(flat),**{k:sum(e[k] for e in flat) for k in ['processed_tokens','supervised_tokens']}},
        'data_path':str(data.relative_to(ROOT)).replace('\\','/'),'data_sha256':sha(data),'full_trajectory_targets':True}}
    write(OUT/'selection.json',selection)
    cfg=dict(parent);cfg.update(epochs=1,research_stage='NESTED100_DATA_DIVERSITY_AT_MATCHED_BUDGET',
        selection_manifest='experiments/SFT-SCALE-PREP-20261010-001/selection.json',schedule_sha256=content_sha256(schedule(310,1,42)),
        comparison_token_deltas=proposal['versus_S1_two_epoch_relative_tokens'],
        **{'Research Question':'Does100unique reviewedtrainingtasks at approximatelyfixedtokens/310updates outperform original50tasks repeatedtwice?',
           'Hypothesis':'More taskdiversity may reduce remaining semantic failures;notestablishedbycurrent50taskresult.',
           'Independent Variable':'100unique tasks x1epoch vs50 x2epochs;retains originalS1,adds50 viafrozen budgetmatching SHA rank;notuniform random.',
           'Controlled Variables':['samefreshBase','sameLoRA/optimizer/lr/seed42','310updates','processedtokens+0.3521%,targettokens-0.8372%','sameB1/nonthinking/8K/dev24/seeds42,43','samePRO6000GPUandpackages','fixedfinalcheckpoint'],
           'Metrics':['officialsuccess/all/nonempty/empty','callvalidity and newfailureaudit','tokens/latency/VRAM/stepseconds/GPUhours','pairedtaskcluster S100-S1'],
           'Evidence Gate':'100approvedwhole tasks,canonicalmask/reencoding,actualHFtokenizer,exactweights/packages,sameGPU;CE/gradients/adapter/reload;all48validdevrollouts;sharedalgorithm-equivalence checks.',
           'Cost Bound':'One existingPRO6000,one310update training max60min plusone48rollout eval max30min. Engineeringestimate~0.3-0.4scriptGPUh based priorruns;setup/idle extra,rateunknown,existingbudgetwaiver.',
           'Failure Branch':'StopandpreserveonOOM/CE/gradient/reload/invalidrun;noauto retry,contextgrowth,moreepochs,newrental orDPO.'})
    cfg['evaluation']={**parent['evaluation'],'conditions':['S100']}
    cfg['input_artifact_sha256']={**parent['input_artifact_sha256'],str((OUT/'selection.json').relative_to(ROOT)).replace('\\','/'):sha(OUT/'selection.json'),str(data.relative_to(ROOT)).replace('\\','/'):sha(data)}
    write(ROOT/'configs/sft_scale_plan.json',cfg)
    manifest={x['path']:x['sha256'] for x in read(ROOT/'experiments/SFT-S1-20261010-001/identity.json')['deployment']['files']}
    assert sha(ROOT/'scripts/run_sft_comparison.py')==manifest['scripts/run_sft_comparison.py']
    assert sha(ROOT/'scripts/evaluate_sft_comparison.py')==manifest['scripts/evaluate_sft_comparison.py']
    delta=rewrite(ROOT/'scripts/run_sft_comparison.py',ROOT/'scripts/run_sft_scale.py',[
        ('from veriagent.sft_stage import load_inputs,validate_deployment,verify_weights,require,sha','from veriagent.sft_stage import validate_deployment,verify_weights,require,sha\nfrom veriagent.sft_scale import load_inputs'),
        ("choices=['S1','S2']","choices=['S100']"),
        ("['configs/sft_comparison_plan.json','veriagent/sft_stage.py','scripts/run_sft_comparison.py']","['configs/sft_scale_plan.json','veriagent/sft_scale.py','scripts/run_sft_scale.py']"),
        ("'training_tasks':50","'training_tasks':100")])
    delta+=rewrite(ROOT/'scripts/evaluate_sft_comparison.py',ROOT/'scripts/evaluate_sft_scale.py',[
        ("ROOT/'configs/sft_comparison_plan.json'","ROOT/'configs/sft_scale_plan.json'"),
        ("for arm in ['S1','S2']","for arm in ['S100']"),
        ("choices=['BASE_B1','S1','S2']","choices=['S100']"),
        ("['configs/sft_comparison_plan.json','scripts/evaluate_sft_comparison.py','veriagent/sft_stage.py']","['configs/sft_scale_plan.json','scripts/evaluate_sft_scale.py','veriagent/sft_stage.py']")])
    (OUT/'runner_delta.patch').write_text(delta,encoding='utf-8',newline='\n')
    from veriagent.sft_scale import load_inputs
    checked=load_inputs('S100',reencode=True)
    write(OUT/'result.json',{'status':'CPU_PREPARED_NOT_GPU_TRAINED','tasks':100,'examples':310,'updates_planned':310,
        'totals':selection['S100']['totals'],'maximum_sequence_tokens':max(e['processed_tokens'] for e in flat),
        'relative_tokens_vs_S1':proposal['versus_S1_two_epoch_relative_tokens'],'reencoding_passed':True,
        'training_loop_unchanged':True,'runner_delta_sha256':sha(OUT/'runner_delta.patch'),
        'GPU_hours':0,'API_calls':0,'parameter_updates':0,'CPU_seconds':time.perf_counter()-start,
        'planned_training_id':'SFT-S100-20261010-001','planned_eval_id':'SFT-EVAL-S100-20261010-001'})
    print(json.dumps(read(OUT/'result.json')))


if __name__=='__main__': main()
