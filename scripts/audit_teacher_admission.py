"""CPU-only integrity gate for reviewed whole teacher trajectories and SFT inputs."""
from copy import deepcopy
import json
from common import ROOT, Run, card, write_json
from run_sft_probe import prepare_examples
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import CanonicalTeacherEncoder, export_teacher_turns


def main(run_id):
    folder=ROOT/'experiments/TEACHER-ACQUIRE-20260916-001'
    cfg=json.loads((ROOT/'configs/sft_probe_plan.json').read_text())
    teacher_cfg=json.loads((folder/'config.json').read_text())
    cohort=json.loads((ROOT/cfg['cohort_manifest']).read_text())
    tasks={x['task_uid']:x for x in cohort['tasks']}
    rows=[json.loads(x) for x in (folder/'trajectories.jsonl').read_text().splitlines()]
    by_id={x['task_id']:x for x in rows}
    reviews=json.loads((folder/'quality_review_full_trajectory.json').read_text())
    exp=Run(run_id,card('Can reviewed whole API trajectories pass student provenance/mask admission?',
        'All approved full trajectories encode without skipped turns; invalid provenance and altered events are rejected.',
        'Canonical teacher admission path; no optimization',
        ['approved tasks/turns admitted','student token budgets','prefix masking','negative controls','eight-example probe selection'],
        'Every approved trajectory passes, all negative controls reject, probe contains2 full trajectories/8 turns',
        experiment_kind='CPU_TEACHER_SFT_ADMISSION_NOT_PARAMETER_UPDATE',seed=42))
    encoder=CanonicalTeacherEncoder(cfg['max_context_tokens']); examples=[]
    for review in reviews['approved']:
        encoded=export_teacher_turns(by_id[review['task_id']],review,tasks,encoder,teacher_cfg)
        examples.extend(encoded)
        exp.append('admission_manifest.jsonl',{'task_id':review['task_id'],'turns':len(encoded),
            'processed_tokens':sum(x['processed_tokens'] for x in encoded),
            'supervised_tokens':sum(x['supervised_tokens'] for x in encoded),
            'all_prefix_labels_masked':all(x['labels'][:x['prefix_tokens']]==[-100]*x['prefix_tokens'] for x in encoded)})
    original=by_id[707]; approval=next(x for x in reviews['approved'] if x['task_id']==707)
    controls=[]
    def rejected(name,change,review_change=None):
        record=deepcopy(original); change(record); review=deepcopy(approval)
        # Re-hash so checks test provenance, not only stale-review detection.
        review['trajectory_sha256']=content_sha256(record)
        if review_change:review_change(review)
        try:export_teacher_turns(record,review,tasks,encoder,teacher_cfg)
        except (ValueError,IndexError,KeyError) as exc:
            controls.append({'name':name,'passed':True,'error_type':type(exc).__name__});return
        controls.append({'name':name,'passed':False})
    rejected('development_pool',lambda r:r.update(source_pool='development'))
    rejected('scripted_producer',lambda r:r.update(producer='CPU_REPLAY_FIXTURE_NOT_TRAINING'))
    rejected('infra_invalid',lambda r:r.update(infra_invalid=True))
    rejected('failed_reward',lambda r:r['verifier'].update(official_reward=0))
    rejected('missing_full_turn',lambda r:r['rounds'].pop(0))
    rejected('altered_observation',lambda r:r['events'][0].update(observation='fabricated'))
    rejected('altered_api_response',lambda r:r['rounds'][0]['raw_response']['choices'][0]['message'].update(content='modified'))
    rejected('wrong_request_hash',lambda r:r['rounds'][0].update(request_body_sha256='0'*64))
    rejected('wrong_student_revision',lambda r:r.update(student_model_revision='wrong'))
    rejected('wrong_usage',lambda r:r.update(output_tokens=0))
    rejected('missing_quality_approval',lambda r:None,lambda r:r.update(all_supervised_turns_acceptable=False))
    for review in reviews['rejected_or_held']:
        try:export_teacher_turns(by_id[review['task_id']],review,tasks,encoder,teacher_cfg)
        except ValueError:controls.append({'name':'held_task_'+str(review['task_id']),'passed':True})
        else:controls.append({'name':'held_task_'+str(review['task_id']),'passed':False})
    selected,probe,_=prepare_examples(cfg,folder/'trajectories.jsonl',folder/'probe_quality_approvals.json','canonical-teacher')
    assert [r['task_id'] for r in selected]==[707,965] and len(probe)==8
    for example in probe:exp.append('probe_examples.jsonl',example)
    write_json(exp.path/'negative_controls.json',controls)
    result={'status':'CPU_TEACHER_ADMISSION_PASSED' if all(x['passed'] for x in controls) else 'GATE_FAILED',
        'approved_tasks':len(reviews['approved']),'full_assistant_turns':len(examples),'turns_dropped':0,
        'probe_tasks':[r['task_id'] for r in selected],'probe_examples':len(probe),
        'probe_processed_tokens':sum(x['processed_tokens'] for x in probe),
        'probe_supervised_tokens':sum(x['supervised_tokens'] for x in probe),
        'probe_max_sequence_tokens':max(x['processed_tokens'] for x in probe),
        'negative_controls_passed':sum(x['passed'] for x in controls),'negative_controls_total':len(controls),
        'api_calls':0,'parameter_updates':0,'gpu_hours':0,'paid_cost_rmb':0,
        'limitations':['No actual Transformers/CE/gradient/update/reload in this CPU gate',
                       'Teacher alias and HTTP model label do not establish immutable closed-model weights']}
    exp.finish(result,'completed' if result['status'].endswith('PASSED') else 'gate_failed')
    print(json.dumps(result,indent=2))
    if not all(x['passed'] for x in controls):raise SystemExit(1)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True)
    main(parser.parse_args().run_id)
