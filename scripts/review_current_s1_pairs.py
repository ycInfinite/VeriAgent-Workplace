"""Fresh fixed25 semantic dispositions + replay + complete-branch CPU export.

Human-readable decisions below were made after reading all50 visible transcripts.
No model/provider calls, data selection, or parameter updates occur here.
"""
import gzip
import json
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from common import ROOT
from prepare_postsft_audit import branch
from veriagent.environment import WorkplaceEnv, digest
from veriagent.sft_data import content_sha256
from veriagent.sft_stage import read, sha, require
from veriagent.teacher_data import CanonicalTeacherEncoder

RUN = 'S1-FAILURE-ACQUIRE-20261012-001'
PREP = ROOT/'experiments/S1-FAILURE-PREP-20261012-002'
OUT = ROOT/'experiments/S1-PAIR-REVIEW-20261016-001'
# Decision, primary failure, fresh chosen/rejected interpretation.
REVIEWS = {
    1082: ('no_preference_signal', None, 'Both observe all three values >2 and plot the requested metric/range. Simulated plot-path semantics only; no physical image attestation.'),
    795: ('no_preference_signal', None, 'Both create the requested total-visits bar chart. S1 additionally retrieves counts; extra useful inspection alone is not a correctness preference.'),
    1173: ('no_preference_signal', None, 'Both create the two requested bar plots over Oct3-Nov30.'),
    1076: ('approved_reward_gap_pair', 'unrequested_extra_actions', 'Teacher correctly sums direct82/referral14/search16/social30 and plots direct only. S1 identifies direct correctly but plots all four sources; three extra mutations violate the requested most-popular-only scope.'),
    1000: ('approved_reward_gap_pair', 'threshold_unit_reinterpretation', 'Teacher observes18-22 seconds, none below2, and correctly makes no plot. S1 invents minutes/hours and120-minute threshold, then plots despite the unmet condition.'),
    473: ('approved_reward_gap_pair', 'temporal_ordering', 'Teacher filters future meetings and deletes observed Dec11 ID161. S1 sees that event but deletes Nov6 ID206, incorrectly calling a past meeting the only future meeting.'),
    349: ('approved_reward_gap_pair', 'temporal_ordering', 'Teacher selects earliest future Dec5 ID60 from four matches. S1 lists Dec5/6/18/19 yet renames Dec18 ID160. Both identifiers were observed; this is selection error, not ID hallucination.'),
    1194: ('approved_reward_gap_pair', 'requested_new_value_as_lookup_filter', 'Teacher selects latest Dec21 meeting15:30 ID170 and changes only its name. S1 searches for the requested new name as though it were the existing meeting, then asks the user instead of performing the update.'),
    120: ('no_preference_signal', None, 'Both delete earliest Nov30 meeting09:30 ID200 and correctly report remaining meetings.'),
    51: ('approved_reward_gap_pair', 'conditional_action_violation', 'Teacher sees Nov27/29 meetings and correctly schedules nothing. S1 sees the same meetings but creates an unnecessary Dec1 appointment; its16:00 slot also overlaps the observed15:00-17:00 event and omits a calendar page. Boundary broadness does not affect the two recent matches.'),
    79: ('no_preference_signal', None, 'Both lookup TaylorJackson ID189 and delete exactly that record.'),
    545: ('no_preference_signal', None, 'Both resolve Nadia and add ParkerMartin as Lead assigned to the grounded email.'),
    91: ('no_preference_signal', None, 'Both lookup CameronMartinez ID126 and delete exactly that record.'),
    979: ('no_preference_signal', None, 'Both lookup AlexGarcia ID49 and Akira email, then change only assigned_to_email.'),
    443: ('no_preference_signal', None, 'Both correctly preserve the empty Sofia+Won+Training intersection. Teacher checks broader lists/pages; complete Won list excludes Training. S1 concise no-change answer is sufficient; teacher length does not establish superiority.'),
    45: ('no_preference_signal', None, 'Both forward latest exact-subject ID460 to two resolved recipients. S1 uses first sorted result page; source search sorts descending, so older pages cannot contain a later match. Teacher additionally checks all14 hits.'),
    1130: ('no_preference_signal', None, 'Both forward unique exact-subject ID366 to resolved Dmitri andRaj.'),
    746: ('held_ambiguous_reference', 'date_window_boundary', 'Both delete8 observed Raj emails and receive reward1. Includes Nov23 11:50 while environment now is Nov30 23:59: date-inclusive versus rolling7-day boundary changes scope. Teacher is not an unambiguous superior branch. S1 also misdescribes page counts but recovers all8; preserve raw evidence, no pair.'),
    1179: ('held_censored_or_corrupted', 'wrong_date_window_and_schema_recovery', 'Teacher correctly selects sole Raj exact-subject Nov24 ID288 for last calendar weekNov20-26 and forwards toAmir. S1 chooses Nov13-20, invents three unsupported sender filters, repeats lookup, and ends at6round cap. Valid policy failure, not infra-invalid; censored branch excluded by protocol.'),
    165: ('no_preference_signal', None, 'Both make no deletion after finding no Carlos emails sinceNov25. Teacher checks all21 older records, most recentNov23; boundary broadness cannot change empty result. S1 shorter answer is sufficiently supported.'),
    1146: ('no_preference_signal', None, 'Both inspect12 Olga backlog tasks and move exactly overdueNov27 IDs258/294. Remaining tasksDec1+; no due-today boundary ambiguity.'),
    839: ('no_preference_signal', 'minor_incidental_count_error', 'Both move exactly Fatima IDs74/75/2 from InProgress toInReview. S1 calls the20-item owner list19; preserve this factual error, but do not create a preference solely from this incidental one-item count and broader lookup.'),
    902: ('no_preference_signal', None, 'Both move only Anaya InProgress IDs196/159 toBacklog.'),
    1114: ('no_preference_signal', None, 'Both move only Jinsoo InProgress IDs267/214 toBacklog.'),
    702: ('approved_same_reward_semantic_pair', 'unsupported_final_summary', 'Both correctly make no state change. Teacher faithfully reports22 tasks:Completed6/Backlog12/InReview4/InProgress0. S1 claims21 tasks and distribution11/10/3, inconsistent with observations and with its own total. Preference is factual answer fidelity, not state success, length, or tool efficiency; separate from reward-gap pairs.'),
}


def main():
    OUT.mkdir(exist_ok=False)
    started = time.perf_counter()
    def save(name, obj):
        with (OUT/name).open('x', encoding='utf-8', newline='\n') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    sources = [ROOT/f'experiments/{RUN}/trajectories.jsonl', PREP/'teacher_records.jsonl.gz', PREP/'selection.json',
               ROOT/'configs/s1_failure_pair_review_protocol.json', ROOT/'configs/s1_failure_acquisition.json',
               ROOT/'experiments/SFT-READY-20260917-001/selection.json']
    save('identity.json', {'started_at': datetime.now(timezone.utc).isoformat(), 'execution_commit': '4efbf07e3410cad64b20989498247405e2026a0d',
        'script_sha256': sha(Path(__file__)), 'sources': {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'kind': 'CPU_ONLY_OFFLINE_REVIEW'})
    save('config.json', {'Research Question': 'What usable preferences do the frozen25 currentS1 rollouts yield?',
        'Hypothesis': 'Some currentS1 failures are attributable and have a superior existing teacher branch.',
        'Independent Variable': 'Fresh full-transcript semantic disposition; no policy update or new sampling.',
        'Controlled Variables': 'Exact frozen25, prior teacher sources, original prompt/tools/state, whole trajectories,8192.',
        'Metrics': 'Pair yield/reasons, fresh replay, canonical target/context tokens, source identities.',
        'Evidence Gate': 'Complete semantic review plus same-task/state/tools and exact offline replay; no partial-branch rescue.',
        'Cost Bound': 'Local CPU only; GPU/API/updates0.', 'Failure Branch': 'Preserve failed audit and all held records; no retry of model collection.',
        'protocol': read(sources[3]), 'same_reward_pairs_separate': True, 'GPU_training_authorized': False})
    try:
        student = {r['task_id']: r for r in map(json.loads, sources[0].read_text(encoding='utf-8').splitlines())}
        with gzip.open(sources[1], 'rt', encoding='utf-8') as f:
            teacher = {r['task_id']: r for r in map(json.loads, f)}
        selection = read(sources[2]); selected = {r['task_id']: r for r in selection['tasks']}
        cfg = read(sources[4]); original = read(sources[5])
        train_ids = {x['task_uid'] for x in original['S1']['tasks']}
        require(set(student) == set(teacher) == set(selected) == set(REVIEWS) and len(student) == 25, 'Cohort changed')
        require([r['task_uid'] for r in student.values()] == cfg['task_uids'], 'Order changed')
        pool = {x['task_uid']: x for x in read(ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json')['records']}
        encoder = CanonicalTeacherEncoder(8192); pairs = []; reviews = []; replays = []
        for tid, s in student.items():
            c = teacher[tid]; decision, failure, reason = REVIEWS[tid]
            require(c['task_uid'] == s['task_uid'] and c['task_uid'] not in train_ids, 'Task mismatch/S1 train overlap')
            require(pool[c['task_uid']]['pool'] == 'training_candidate' and pool[c['task_uid']]['source_split'] == 'train', 'Leakage')
            require(s['seed'] == 42 and s['policy_identity']['adapter']['files'] == cfg['initial_adapter_sha256'], 'Policy/seed changed')
            require(content_sha256(c) == selected[tid]['trajectory_sha256'], 'Teacher hash changed')
            for k in ['initial_messages', 'tool_schemas', 'initial_state_sha256', 'reference']:
                require(content_sha256(c[k]) == content_sha256(s[k]), 'Pair context differs: '+k)
            for side, record in [('chosen', c), ('rejected', s)]:
                require(record['source_pool'] == 'training_candidate' and not record['infra_invalid'] and record['online_replay_equal'], 'Invalid source')
                env = WorkplaceEnv(); require(digest(env.initial_state) == record['initial_state_sha256'], 'Initial state changed')
                for event in record['events']:
                    actual = env.step(event['tool_call'])
                    for key in ['observation', 'exception', 'state_before_sha256', 'state_after_sha256', 'state_changes']:
                        require(content_sha256(actual[key]) == content_sha256(event[key]), 'Replay differs: '+key)
                reward = env.verify(record['reference'])['official_reward']
                require(reward == record['verifier']['official_reward'], 'Reward changed')
                replays.append({'task_id': tid, 'side': side, 'events': len(record['events']), 'reward': reward, 'source_record_sha256': content_sha256(record)})
            review = {'task_id': tid, 'task_uid': s['task_uid'], 'category': selected[tid]['category'], 'empty_reference': not s['reference'],
                'decision': decision, 'failure_category': failure, 'reason': reason, 'teacher_reward': c['verifier']['official_reward'],
                'S1_reward': s['verifier']['official_reward'], 'termination': s['termination'],
                'chosen_sha256': content_sha256(c), 'rejected_sha256': content_sha256(s), 'reviewer': 'Codex',
                'all_visible_messages_reviewed': True, 'independent_human_review': False}
            reviews.append(review)
            if not decision.startswith('approved_'):
                continue
            require(c['termination'] == s['termination'] == 'assistant_final' and not c['parse_errors'] and not s['parse_errors'], 'Censored/corrupt pair')
            require(c['verifier']['official_reward'] == 1, 'Chosen verifier failed')
            require(s['verifier']['official_reward'] == (0 if decision == 'approved_reward_gap_pair' else 1), 'Decision/reward mismatch')
            a, b = branch(c, encoder), branch(s, encoder)
            for obj in [a, b]:
                for e in obj['encoded_turns']:
                    e.update(task_id=tid, task_uid=s['task_uid'], source_pool='training_candidate', training_eligible=True)
            pairs.append({'pair_id': f'CURRENT-S1-{tid}-20261016-v1', 'task_id': tid, 'task_uid': s['task_uid'],
                'source_pool': 'training_candidate', 'category': selected[tid]['category'], 'prompt_context': c['initial_messages'],
                'tools': c['tool_schemas'], 'initial_state_sha256': c['initial_state_sha256'], 'chosen_run': 'DEEPSEEK-SFTDATA-20260917-001',
                'rejected_run': RUN, 'chosen': a, 'rejected': b, 'failure_category': failure, 'why_pair_valid': reason,
                'fresh_review': review, 'preference_type': decision, 'dpo_data_admitted': True,
                'status': 'CPU_DATA_ADMITTED_GPU_UNQUALIFIED', 'GPU_training_authorized': False})
        require(len(pairs) == 7 and len(replays) == 50, 'Unexpected audited totals')
        for filename, subset in [('reward_gap_pairs.jsonl.gz', [p for p in pairs if p['preference_type'] == 'approved_reward_gap_pair']),
                                 ('same_reward_pairs.jsonl.gz', [p for p in pairs if p['preference_type'] == 'approved_same_reward_semantic_pair'])]:
            payload = ''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in subset).encode()
            (OUT/filename).write_bytes(gzip.compress(payload, mtime=0))
        save('review.json', {'reviewed_tasks': 25, 'reviewed_branches': 50, 'dispositions': dict(Counter(r['decision'] for r in reviews)),
            'tasks': reviews, 'review_scope': 'Single Codex full visible transcript review, not independent human review; no hidden reasoning review.'})
        save('replay.json', {'branches': replays, 'all_equal': True})
        save('manifest.json', {'pairs': [{k: v for k, v in p.items() if k not in ['chosen', 'rejected', 'prompt_context', 'tools']} |
            {side: {k: v for k, v in p[side].items() if k not in ['messages', 'encoded_turns']} for side in ['chosen', 'rejected']} for p in pairs],
            'artifacts': {n: sha(OUT/n) for n in ['reward_gap_pairs.jsonl.gz', 'same_reward_pairs.jsonl.gz']},
            'confounds': ['25 selected from previously teacher-approved strata, not representative training-pool sample',
                'Chosen is one teacher provider; rejected is currentS1; style and length remain confounded',
                'One seed per task does not establish failure reproducibility', 'Same-reward702 targets answer fidelity, not state completion'],
            'future_training': 'Requires a separately approved plan; old frozen12-pair files remain unchanged. Same-reward data require explicit loader/plan support.'})
        summary = {'status': 'CURRENT_S1_PAIR_REVIEW_COMPLETE', 'tasks': 25, 'fresh_replay_branches': 50,
            'reward_gap_pairs': 6, 'same_reward_pairs': 1, 'held_censored': 1, 'held_boundary': 1, 'no_preference_signal': 16,
            'chosen_target_tokens': sum(p['chosen']['target_tokens'] for p in pairs), 'rejected_target_tokens': sum(p['rejected']['target_tokens'] for p in pairs),
            'processed_tokens': sum(p[side]['processed_tokens'] for p in pairs for side in ['chosen', 'rejected']),
            'branch_turns': {side: sum(p[side]['turn_count'] for p in pairs) for side in ['chosen', 'rejected']},
            'max_sequence_tokens': max(p[side]['max_sequence_tokens'] for p in pairs for side in ['chosen', 'rejected']),
            'by_type': {kind: {'pairs': len(sub := [p for p in pairs if p['preference_type'] == kind]),
                'chosen_target_tokens': sum(p['chosen']['target_tokens'] for p in sub), 'rejected_target_tokens': sum(p['rejected']['target_tokens'] for p in sub)} for kind in {p['preference_type'] for p in pairs}},
            'CPU_seconds': time.perf_counter()-started, 'GPU_hours': 0, 'API_requests': 0, 'parameter_updates': 0, 'GPU_DPO_qualified': False}
        save('result.json', summary); print(json.dumps(summary))
    except Exception:
        save('invalid_run.json', {'traceback': traceback.format_exc(), 'CPU_seconds': time.perf_counter()-started, 'model_calls': 0}); raise


if __name__ == '__main__':
    main()
