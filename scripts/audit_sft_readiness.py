"""CPU admission/negative controls for frozen SFT inputs; no model construction."""
from copy import deepcopy
from datetime import datetime,timezone
import json,math,sys
import numpy as np
from common import ROOT,write_json
from veriagent.sft_stage import load_inputs,validate_example,read,sha
from veriagent.teacher_data import CanonicalTeacherEncoder,export_teacher_turns
from veriagent.sft_data import content_sha256
from evaluate_sft_comparison import load_eval


def main():
    out=ROOT/'experiments/SFT-READY-20260917-001';target=out/'cpu_readiness_checks.json'
    assert not target.exists()
    checks=[];arms={}
    for arm in ['S1','S2']:
        cfg,selected,examples,order=load_inputs(arm,reencode=True)
        assert len(examples)==155 and len(order)==310
        assert all(sum(x['example_index']==i for x in order)==2 for i in range(155))
        arms[arm]={'tasks':len(selected['tasks']),'examples':len(examples),'steps':len(order),
                  'full_schedule_processed_tokens':2*selected['totals']['processed_tokens'],
                  'full_schedule_supervised_tokens':2*selected['totals']['supervised_tokens']}
        checks.append(arm+'_whole_raw_to_template_ids_labels_reconstruction')
    source=ROOT/'experiments'/cfg['source_run'];teacher=read(source/'config.json');cohort=read(ROOT/teacher['cohort_manifest'])
    tasks={t['task_uid']:t for t in cohort['tasks']}
    rows={r['task_uid']:r for r in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
    reviews={r['task_uid']:r for r in read(ROOT/cfg['quality_approvals'])['approved']}
    uid=next(k for k,r in rows.items() if k in reviews and len(r['rounds'])>=3)
    record=rows[uid];review=reviews[uid];encoder=CanonicalTeacherEncoder(8192)
    def admit(r,v,tasks_arg=tasks):return export_teacher_turns(r,v,tasks_arg,encoder,teacher,source_provider='deepseek',required_decision='approved_for_sft')
    def rejected(name,fn):
        try:fn()
        except (ValueError,KeyError,IndexError):checks.append(name);return
        raise AssertionError('Negative control admitted: '+name)
    for name,mutation in [
        ('changed_provider',lambda r:r.update(producer='BAILIAN_REAL_API')),
        ('changed_model',lambda r:r.update(requested_model='other-model')),
        ('missing_whole_turn',lambda r:r['rounds'].pop()),
        ('changed_tool_observation',lambda r:next(m for m in r['messages'] if m['role']=='tool').update(content='{}')),
        ('changed_raw_assistant',lambda r:r['rounds'][0]['raw_response']['choices'][0]['message'].update(content='fabricated replacement')),
        ('changed_wire_request_hash',lambda r:r['rounds'][0].update(request_body_sha256='0'*64)),
        ('wrong_pool',lambda r:r.update(source_pool='development')),
    ]:
        altered=deepcopy(record);mutation(altered)
        # Rebinding a review hash must still not bypass deeper source continuity checks.
        rebound={**review,'trajectory_sha256':content_sha256(altered)}
        rejected(name,lambda r=altered,v=rebound:admit(r,v))
    rejected('missing_semantic_approval',lambda:admit(record,{**review,'target_scope_checked':False}))
    rejected('stale_approval_hash',lambda:admit(record,{**review,'trajectory_sha256':'f'*64}))
    rejected('mechanical_screen_is_not_semantic_approval',lambda:admit(record,{**review,'decision':'mechanically_unflagged'}))
    denied_tasks=deepcopy(tasks);denied_tasks[uid]['pool']='official_validation_SEALED'
    rejected('sealed_pool_metadata_refused',lambda:admit(record,review,denied_tasks))
    ex=deepcopy(examples[0]);ex['labels'][0]=ex['input_ids'][0]
    rejected('context_label_unmasked',lambda:validate_example(ex))
    ex2=deepcopy(examples[0]);ex2['labels'][ex2['prefix_tokens']]=-100
    rejected('selectively_removed_assistant_target',lambda:validate_example(ex2))
    ex3=deepcopy(examples[0]);ex3['attention_mask'][0]=0
    rejected('unregistered_attention_mask',lambda:validate_example(ex3))
    evcfg,ev,dev=load_eval();assert len(dev)==24
    train_uids={t['task_uid'] for a in ['S1','S2'] for t in read(ROOT/cfg['selection_manifest'])[a]['tasks']}
    assert not train_uids & {t['task_uid'] for t in dev};checks.append('fixed_dev24_disjoint_and_identical_protocol')
    split=read(ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json')
    pool={r['task_uid']:r['pool'] for r in split['records']}
    assert all(pool[u]=='training_candidate' for u in train_uids)
    checks.append('global_split_membership_no_dev_validation_final_bfcl_training')
    # A small analytic CE fixture checks shifting/masking only; it is not a model forward or update.
    logits=np.random.default_rng(42).normal(size=(7,8));labels=np.array([-100,-100,-100,-100,2,3,7])
    def ce(x):
        positions=np.nonzero(labels[1:]!=-100)[0];chosen=labels[1:][positions]
        active=x[:-1][positions];m=active.max(axis=1)
        return float(np.mean(m+np.log(np.exp(active-m[:,None]).sum(axis=1))-active[np.arange(len(chosen)),chosen]))
    loss=ce(logits);ignored=logits.copy();ignored[:3]+=123
    targeted=logits.copy();targeted[3,2]+=2
    assert ce(ignored)==loss and not math.isclose(ce(targeted),loss)
    checks.append('analytic_shifted_CE_masks_context_but_includes_first_assistant_target')
    old=ROOT/'experiments/TEACHER-ACQUIRE-20260916-001';oldcfg=read(old/'config.json')
    oldcohort=read(ROOT/oldcfg['cohort_manifest']);oldtasks={t['task_uid']:t for t in oldcohort['tasks']}
    oldrows={content_sha256(r):r for r in map(json.loads,(old/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
    legacy=[]
    for v in read(old/'probe_quality_approvals.json')['approved']:
        legacy.extend(export_teacher_turns(oldrows[v['trajectory_sha256']],v,oldtasks,encoder,oldcfg))
    assert len(legacy)==8 and sum(e['supervised_tokens'] for e in legacy)==582
    checks.append('legacy_Bailian_two_whole_trajectory_export_unchanged_8turns582targets')
    assert 'torch' not in sys.modules
    result={'status':'CPU_READINESS_CHECKS_PASSED','checked_at':datetime.now(timezone.utc).isoformat(),
        'checks':checks,'check_count':len(checks),'arms':arms,'model_loaded':False,'model_requests':0,'parameter_updates':0,'gpu_hours':0,
        'real_CE_gradient_update_reload':'Not rerun; prior8-update probe evidence retained. New310-step runner runtime checks require future authorized GPU run.',
        'semantic_review':'Codex only;150 reviewed,137 approved,13 held; no independent human review',
        'audit_script_sha256':sha(ROOT/'scripts/audit_sft_readiness.py')}
    write_json(target,result);print(json.dumps(result))


if __name__=='__main__':main()
