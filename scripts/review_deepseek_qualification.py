"""Evidence checks plus recorded Codex whole-trajectory judgments; no inference/training."""
from datetime import datetime,timezone
import json
from common import ROOT,write_json
from veriagent.environment import WorkplaceEnv,digest,snapshot
from veriagent.teacher_data import CanonicalTeacherEncoder,validate_request
from veriagent.deepseek_teacher import request_body,usage,estimated_cost

RUN='DEEPSEEK-QUAL-20260917-001'
APPROVED={
565:'User supplies metric/date; correct histogram action and returned simulated plot path. No physical image existence established.',
450:'Observed daily counts substantiate the threshold; dates/metric and final table agree with observations.',
972:'Both requested metrics and dates are plotted; reports the actual simulated paths.',
247:'Unique directory lookup grounds Lena; meeting name, business-hour time and duration match request. Final constraints statement is scoped to working hours, not an independent conflict audit.',
859:'Both calendar pages inspected; chosen latest event is observed and renamed correctly.',
123:'All three meetings fit one returned page; earliest event identified and deleted.',
770:'Lena email obtained from directory; Lead status and new customer match request and actual response.',
271:'Directory identity, Lost/Hardware filters and complete one-customer result support deletion.',
20:'Both owners resolved; all four consulting customers observed, status predicate applied before reassignment.',
707:'Unique customer lookup precedes status update; final record details grounded.',
177:'All five matching emails fit one page; newest timestamp and both resolved recipients support forwarding.',
76:'Both matching messages are visible and from Sofia; newest ID and exact user reply text are correct.',
965:'Unfiltered In Progress query returns the full list (no pagination); only one item belongs to resolved Dmitri. Broader than necessary, but grounded and correct.',
687:'Resolved owner and filtered full task list ground both updates to In Review.',
8:'Resolved owner and full matching list ground the single Backlog update.'}
HELD={
331:('student_context_fit','Official reward1 but final target exceeds8192 student tokens; no truncation or removal of earlier turns. Approximate traffic totals are also not exact sums.'),
1183:('unsupported_scope_completion','Search arbitrarily ends2024-12-31; observations do not establish all future meetings, despite official reward1.'),
980:('pagination_coverage','Only page1/2 inspected. Schema does not promise newest-first ordering; global latest claim is not supported by complete observable coverage.'),
518:('pagination_coverage','Only page1/2 inspected; same conservative ordering/coverage standard as the earlier Max review.'),
1175:('due_date_boundary_omission','Reward0: updates observed250/257 but excludes observed246 due today. Official reference also requires246; date-boundary interpretation differs. Do not alter official reward.')}


def main():
    out=ROOT/'experiments'/RUN
    cfg=json.loads((out/'config.json').read_text(encoding='utf-8'))
    records=[json.loads(l) for l in (out/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
    api=[json.loads(l) for l in (out/'api_events.jsonl').read_text(encoding='utf-8').splitlines()]
    indexed={(e['task_id'],e['turn'],e['event']):e for e in api}
    cohort=json.loads((ROOT/cfg['cohort_manifest']).read_text(encoding='utf-8'))
    tasks={t['task_uid']:t for t in cohort['tasks']}
    assert len(records)==20 and set(APPROVED)|set(HELD)=={r['task_id'] for r in records}
    assert not set(APPROVED)&set(HELD)
    encoder=CanonicalTeacherEncoder(8192)
    approved=[];held=[];call_count=0;mode_count=0;reasoning_known=0
    examples=[];costs=[];prefixes=[];all_calls=[]
    for r in records:
        assert not r['infra_invalid'] and r['online_replay_equal']
        validate_request({'messages':r['initial_messages'],'tools':r['tool_schemas']},tasks[r['task_uid']])
        assert r['producer']=='DEEPSEEK_REAL_API' and r['seed'] is None
        env=WorkplaceEnv()
        assert digest(env.initial_state)==r['initial_state_sha256']
        for event in r['events']:
            repeated=env.step(event['tool_call'])
            assert digest(repeated['observation'])==digest(event['observation'])
            assert repeated['state_after_sha256']==event['state_after_sha256']
        assert digest(snapshot(env.tools))==r['final_state_sha256']
        assert env.verify(r['reference'])['official_reward']==r['verifier']['official_reward']
        for t in r['rounds']:
            req=indexed[(r['task_id'],t['turn'],'request_started')]
            resp=indexed[(r['task_id'],t['turn'],'response')]
            body=request_body(t['input_messages'],r['tool_schemas'],cfg,t['provider_output_cap'])
            assert digest(body)==t['request_body_sha256']==digest(req['body'])
            assert digest(resp['body'])==digest(t['raw_response'])
            assert body['thinking']=={'type':'disabled'} and 'seed' not in body
            assert not t['raw_response']['choices'][0]['message'].get('reasoning_content')
            u=usage(t['raw_response']);assert u['reasoning_tokens'] in (None,0)
            reasoning_known+=u['reasoning_tokens'] is not None
            mode_count+=1;costs.append(estimated_cost(resp['body'],resp['observed_at']))
            prefixes.append(t['student_prefix_tokens'])
            if r['task_id'] in APPROVED:
                e=encoder.encode(t['input_messages'],r['tool_schemas'],t['assistant_message'])
                assert e['supervised_tokens']==t['student_supervised_tokens']
                assert e['processed_tokens']==t['student_processed_tokens']
                examples.append(e)
        all_calls.extend(r['call_diagnostics']);call_count+=len(r['events'])
        entry={'task_id':r['task_id'],'task_uid':r['task_uid'],'trajectory_sha256':digest(r),
               'official_reward':r['verifier']['official_reward'],'reviewer':'Codex',
               'independent_human_review':False,'all_turns_reviewed':True}
        if r['task_id'] in APPROVED:
            assert r['termination']=='assistant_final' and r['verifier']['official_reward']==1
            assert all(c['executable_gate'] for c in r['call_diagnostics'])
            approved.append({**entry,'decision':'whole_trajectory_quality_pass',
                'grounding_checked':True,'target_scope_checked':True,'rationale':APPROVED[r['task_id']],
                'training_export_admitted':False})
        else:
            category,reason=HELD[r['task_id']]
            held.append({**entry,'decision':'hold','category':category,'rationale':reason})
    result={'status':'QUALIFICATION_COMPLETE_QUALITY_REVIEWED_NO_TRAINING',
        'valid_trajectories':20,'infrastructure_invalid_trajectories':0,'official_successes':19,
        'quality_approved_trajectories':len(approved),'quality_approval_rate':len(approved)/20,
        'quality_approved_distinct_tasks':len(approved),'held_trajectories':len(held),
        'executable_calls':sum(c['executable_gate'] for c in all_calls),'call_denominator':call_count,
        'unknown_tool_calls':sum(not c['known_tool'] for c in all_calls),
        'schema_argument_error_calls':sum(bool(c['schema_errors']) for c in all_calls),
        'unobserved_identifier_candidates':sum(not i['observed_in_policy_context'] for c in all_calls for i in c['identifiers']),
        'identifier_candidate_denominator':sum(len(c['identifiers']) for c in all_calls),
        'same_call_same_state':sum(c['same_call_same_state_before'] for c in all_calls),
        'three_call_loop':sum(c['three_call_loop'] for c in all_calls),
        'mean_tool_steps':call_count/20,'non_thinking_request_and_response_checks':mode_count,
        'responses_with_explicit_reasoning_usage':reasoning_known,
        'missing_reasoning_usage_note':'Missing internal usage is unavailable, not assumed0; all visible reasoning_content empty.',
        'model_tariff_estimate_rmb':sum(x['estimated_rmb'] for x in costs),
        'model_cost_per_quality_approved':sum(x['estimated_rmb'] for x in costs)/len(approved),
        'whole_approved_assistant_turns':len(examples),
        'whole_approved_student_processed_tokens':sum(e['processed_tokens'] for e in examples),
        'whole_approved_student_target_tokens':sum(e['supervised_tokens'] for e in examples),
        'max_approved_student_sequence':max(e['processed_tokens'] for e in examples),
        'training_export_admitted':False,'export_note':'New provider admission to trainer remains a separate CPU gate; original raw flags unchanged.',
        'parameter_updates':0,'gpu_hours':0,'reviewed_at':datetime.now(timezone.utc).isoformat()}
    for name,data in [('quality_review.json',{'approved':approved,'held':held}),('review_summary.json',result)]:
        if (out/name).exists():raise FileExistsError('Review output already exists')
        write_json(out/name,data)
    print(json.dumps(result))


if __name__=='__main__':main()
