"""Offline acquisition integrity and mechanical screening, NOT semantic admission."""
from collections import Counter,defaultdict
from contextlib import redirect_stdout
from datetime import datetime,timezone
import hashlib
import io
import json

from common import ROOT,write_json
from veriagent.environment import WorkplaceEnv,digest,snapshot
from veriagent.teacher_data import CanonicalTeacherEncoder,validate_request
from veriagent.deepseek_teacher import request_body,usage,estimated_cost

RUN='DEEPSEEK-SFTDATA-20260917-001'


def main():
    out=ROOT/'experiments'/RUN
    assert not (out/'integrity_summary.json').exists()
    cfg=json.loads((out/'config.json').read_text(encoding='utf-8'))
    original=json.loads((out/'result.json').read_text(encoding='utf-8'))
    cohort=json.loads((ROOT/cfg['cohort_manifest']).read_text(encoding='utf-8'))
    records=[json.loads(line) for line in (out/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
    api=[json.loads(line) for line in (out/'api_events.jsonl').read_text(encoding='utf-8').splitlines()]
    indexed={(e['task_id'],e['turn'],e['event']):e for e in api}
    assert len(indexed)==len(api)==4886
    assert len(records)==len({r['task_uid'] for r in records})==723
    assert [r['task_uid'] for r in records]==[t['task_uid'] for t in cohort['tasks']]
    assert not {r['task_uid'] for r in records}&set(cohort['excluded_task_uids'])
    tasks={t['task_uid']:t for t in cohort['tasks']}
    encoder=CanonicalTeacherEncoder(8192)
    calls=[];costs=[];screen=[];seen=set();encodings=0;reasoning_known=0
    by_domain=defaultdict(lambda:Counter());terminations=Counter();empty=Counter()
    for r in records:
        task=tasks[r['task_uid']]
        assert not r['infra_invalid'] and r['online_replay_equal'] and not r['training_eligible']
        assert task['pool']=='training_candidate' and task['source_split']=='train'
        assert r['producer']=='DEEPSEEK_REAL_API' and r['seed'] is None
        validate_request({'messages':r['initial_messages'],'tools':r['tool_schemas']},task)
        env=WorkplaceEnv()
        assert digest(env.initial_state)==r['initial_state_sha256']
        with redirect_stdout(io.StringIO()):
            for event in r['events']:
                actual=env.step(event['tool_call'])
                assert digest(actual['observation'])==digest(event['observation'])
                assert actual['state_after_sha256']==event['state_after_sha256']
            assert digest(snapshot(env.tools))==r['final_state_sha256']
            assert env.verify(r['reference'])['official_reward']==r['verifier']['official_reward']
        reasons=[];processed=0;targets=0
        if r['verifier']['official_reward']!=1:reasons.append('official_reward_not_one')
        if r['termination']!='assistant_final':reasons.append('not_normal_assistant_final')
        if r['parse_errors']:reasons.append('parse_errors')
        if not all(c['executable_gate'] for c in r['call_diagnostics']):reasons.append('nonexecutable_call')
        if any(not i['observed_in_policy_context'] for c in r['call_diagnostics'] for i in c['identifiers']):
            reasons.append('identifier_candidate_needs_manual_review')
        for turn in r['rounds']:
            key=(r['task_id'],turn['turn'])
            req=indexed[(*key,'request_started')];resp=indexed[(*key,'response')]
            seen.update([(*key,'request_started'),(*key,'response')])
            assert cfg['start_at_utc']<=req['observed_at']<cfg['stop_at_utc']
            body=request_body(turn['input_messages'],r['tool_schemas'],cfg,turn['provider_output_cap'])
            assert digest(body)==digest(req['body'])==turn['request_body_sha256']
            assert digest(resp['body'])==digest(turn['raw_response'])
            assert body['thinking']=={'type':'disabled'} and 'seed' not in body
            assert not resp['body']['choices'][0]['message'].get('reasoning_content')
            u=usage(resp['body']);assert u['reasoning_tokens'] in (None,0)
            reasoning_known+=u['reasoning_tokens'] is not None
            costs.append(estimated_cost(resp['body'],resp['observed_at']))
            prompt=encoder.inspector.render(turn['input_messages'],r['tool_schemas'],generate=True)
            assert len(encoder.inspector.tokenizer.encode(prompt,add_special_tokens=False).ids)==turn['student_prefix_tokens']
            try:
                e=encoder.encode(turn['input_messages'],r['tool_schemas'],turn['assistant_message'])
            except ValueError:
                reasons.append('whole_target_encoding_rejected')
                continue
            if 'student_supervised_tokens' in turn:
                assert e['supervised_tokens']==turn['student_supervised_tokens']
                assert e['processed_tokens']==turn['student_processed_tokens']
            encodings+=1;processed+=e['processed_tokens'];targets+=e['supervised_tokens']
        is_empty=r['reference_action_count']==0
        assert is_empty==task['empty_reference_requires_semantic_review']
        empty['tasks']+=is_empty;empty['official_successes']+=is_empty and r['verifier']['official_reward']==1
        by_domain[task['category']]['tasks']+=1
        by_domain[task['category']]['official_successes']+=r['verifier']['official_reward']==1
        terminations[r['termination']]+=1;calls.extend(r['call_diagnostics'])
        screen.append({'task_id':r['task_id'],'task_uid':r['task_uid'],'trajectory_sha256':digest(r),
            'official_reward':r['verifier']['official_reward'],'mechanical_flags':sorted(set(reasons)),
            'empty_reference_requires_semantic_review':is_empty,'student_processed_tokens':processed,
            'student_target_tokens':targets,'whole_semantic_review_done':False,'training_approved':False})
    assert seen==set(indexed)
    assert len(costs)==original['api_attempts']==2443
    assert abs(sum(c['estimated_rmb'] for c in costs)-original['total_model_cost_estimate_rmb'])<1e-9
    clean=[s for s in screen if not s['mechanical_flags']]
    summary={'status':'INTEGRITY_PASSED_SEMANTIC_REVIEW_PENDING','reviewed_at':datetime.now(timezone.utc).isoformat(),
        'audit_script_sha256':hashlib.sha256((ROOT/'scripts/audit_deepseek_pool_acquisition.py').read_bytes()).hexdigest(),
        'trajectories':len(records),'state_observation_verifier_replays_passed':len(records),
        'request_response_pairs_checked':len(costs),'initial_task_identity_checks_passed':len(records),
        'successes':sum(r['verifier']['official_reward']==1 for r in records),
        'by_domain':dict(by_domain),'empty_reference':dict(empty),'termination_counts':dict(terminations),
        'executable_calls':sum(c['executable_gate'] for c in calls),'call_denominator':len(calls),
        'unknown_tool_calls':sum(not c['known_tool'] for c in calls),
        'schema_argument_error_calls':sum(bool(c['schema_errors']) for c in calls),
        'identifier_candidate_denominator':sum(len(c['identifiers']) for c in calls),
        'unobserved_identifier_candidates':sum(not i['observed_in_policy_context'] for c in calls for i in c['identifiers']),
        'same_call_same_state':sum(c['same_call_same_state_before'] for c in calls),
        'three_call_loop':sum(c['three_call_loop'] for c in calls),
        'responses_with_explicit_reasoning_usage':reasoning_known,
        'reasoning_usage_note':'Absent internal reasoning usage is unavailable,not measured zero; visible reasoning_content empty.',
        'mechanically_unflagged_pending_semantics':len(clean),
        'mechanically_flagged':len(screen)-len(clean),
        'mechanical_flag_counts':dict(Counter(reason for s in screen for reason in s['mechanical_flags'])),
        'unflagged_empty_reference_pending_semantics':sum(s['empty_reference_requires_semantic_review'] for s in clean),
        'unflagged_processed_tokens':sum(s['student_processed_tokens'] for s in clean),
        'unflagged_target_tokens':sum(s['student_target_tokens'] for s in clean),
        'encoded_assistant_turns':encodings,'training_approved_trajectories':0,'parameter_updates':0,'gpu_hours':0,
        'semantic_limitation':'No whole-trajectory semantic approval. Automated identifier flags are diagnostic; absence of flags does not prove grounding,scope,pagination or correct final answers.'}
    write_json(out/'mechanical_screen.json',{'trajectories':screen,'training_approved':False})
    write_json(out/'integrity_summary.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':main()
