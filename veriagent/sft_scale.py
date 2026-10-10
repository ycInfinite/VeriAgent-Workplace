"""Admission for the separately authorized nested100 data-diversity experiment."""
import gzip,json
from .sft_stage import ROOT,read,sha,require,validate_example,schedule
from .sft_data import content_sha256
from .teacher_data import CanonicalTeacherEncoder,export_teacher_turns


def load_inputs(arm,reencode=True):
    require(arm=='S100','Only frozen S100 supported')
    cfg=read(ROOT/'configs/sft_scale_plan_v2.json')
    require(cfg['status']=='PREPARED_NOT_EXECUTED' and cfg['epochs']==1 and cfg['seed']==42,'Scale protocol changed')
    require(cfg['max_context_tokens']==8192 and cfg['model_revision']=='b968826d9c46dd6066d109eabc6255188de91218','Model/context changed')
    for name,h in cfg['input_artifact_sha256'].items():
        path=(ROOT/name).resolve();require(path.is_relative_to(ROOT) and sha(path)==h,'Scale artifact changed: '+name)
    selection=read(ROOT/cfg['selection_manifest'])[arm]
    require(len(selection['tasks'])==100 and len({x['task_uid'] for x in selection['tasks']})==100,'Wrong unique task count')
    require(not set(cfg['evaluation']['task_uids']) & {x['task_uid'] for x in selection['tasks']},'Dev leakage')
    s1={x['task_uid'] for x in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}
    require(s1<={x['task_uid'] for x in selection['tasks']},'Not nested original S1')
    require(sha(ROOT/selection['data_path'])==selection['data_sha256'],'Scale data hash mismatch')
    with gzip.open(ROOT/selection['data_path'],'rt',encoding='utf-8') as f:examples=[json.loads(x) for x in f]
    require([(e['task_uid'],e['turn']) for e in examples]==[(t['task_uid'],i) for t in selection['tasks'] for i in range(1,t['turns']+1)],'Whole-turn membership changed')
    approvals={x['task_uid']:x for x in read(ROOT/cfg['quality_approvals'])['approved']}
    for e in examples:
        validate_example(e);require(e['quality_review']==approvals[e['task_uid']],'Review mismatch')
        require(e['source_run']==cfg['source_run'] and e['student_model_revision']==cfg['model_revision'],'Source/model mismatch')
    for k in ['processed_tokens','supervised_tokens']:
        require(sum(x[k] for x in examples)==selection['totals'][k],'Token total mismatch')
    if reencode:
        source=ROOT/'experiments'/cfg['source_run'];teacher=read(source/'config.json')
        tasks={x['task_uid']:x for x in read(ROOT/teacher['cohort_manifest'])['tasks']}
        rows={x['task_uid']:x for x in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        enc=CanonicalTeacherEncoder(8192);rebuilt=[]
        for t in selection['tasks']:
            r=rows[t['task_uid']];require(content_sha256(r)==t['trajectory_sha256'],'Source trajectory changed')
            rebuilt.extend(export_teacher_turns(r,approvals[t['task_uid']],tasks,enc,teacher,source_provider='deepseek',required_decision='approved_for_sft'))
        require(len(rebuilt)==len(examples)==310,'Wrong sample count')
        for a,b in zip(rebuilt,examples):
            for k in ['input_ids','labels','attention_mask','prefix_sha256','canonical_target_sha256']:
                require(a[k]==b[k],'Re-encoding mismatch: '+k)
    order=schedule(len(examples),cfg['epochs'],cfg['seed'])
    require(len(order)==cfg['optimizer_steps_per_arm']==310 and content_sha256(order)==cfg['schedule_sha256'],'Scale schedule changed')
    return cfg,selection,examples,order
