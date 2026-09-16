"""CPU regression evidence. Replayed API fixtures are NEVER real teacher rollouts."""
from copy import deepcopy
import json
import urllib.request
from unittest.mock import patch

from common import ROOT, Run, card, load_rows, write_json
from veriagent.teacher_data import teacher_request
from veriagent.teacher_rollout import (APIError, validate_endpoint, request_body,
    teacher_trajectory, assistant_from_response, read_usage)


def run(run_id):
    cfg = json.loads((ROOT/'configs/teacher_acquisition_plan.json').read_text())
    experiment = Run(run_id, card(
        'Does the CPU teacher collector preserve tools/state and stop safely at API/format boundaries?',
        'Replayed fixtures exercise the real environment without any network or quality approval.',
        'New teacher collector implementation, recorded fixtures only',
        ['wire-schema identity', 'replay equality', 'truncated-call nonexecution', 'invalid-cost attribution', 'negative controls'],
        'All controls pass; zero external requests; fixtures explicitly ineligible',
        experiment_kind='CPU_COLLECTOR_FIXTURE_AUDIT_NOT_MODEL_EVALUATION', seed=42))
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
    def reject(name, fn):
        try:
            fn()
        except (ValueError, APIError):
            check(name, True)
        else:
            check(name, False)
    cohort = json.loads((ROOT/cfg['cohort_manifest']).read_text())
    rows = load_rows('train')
    for task in cohort['tasks']:
        row = rows[task['source_row_index']]
        request = teacher_request(row, task, cohort['B1_addition'])
        body = request_body(request['messages'], request['tools'], cfg, 768)
        restored = [{'type': x['type'], **x['function']} for x in body['tools']]
        check('wire_schema_identity_'+str(row['id']), restored == request['tools'])
        check('wire_only_allowed_fields_'+str(row['id']), set(body) == {
            'model', 'messages', 'tools', 'stream', 'enable_thinking', 'seed', 'temperature', 'top_p', 'max_tokens'})
    check('workspace_endpoint', validate_endpoint(cfg['base_url']).endswith('/chat/completions'))
    reject('subscription_endpoint', lambda: validate_endpoint('https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'))
    reject('foreign_endpoint', lambda: validate_endpoint('https://example.com/compatible-mode/v1'))
    reject('url_credentials', lambda: validate_endpoint('https://secret@dashscope.aliyuncs.com/compatible-mode/v1'))
    reject('usage_unavailable', lambda: read_usage({'choices': []}))
    original = next(json.loads(line) for line in (ROOT/'experiments/SFT-ACQUIRE-20260916-001/trajectories.jsonl').read_text(encoding='utf-8').splitlines()
                    if json.loads(line)['task_id'] == 707)
    task = next(x for x in cohort['tasks'] if x['source_id'] == 707)
    row = rows[task['source_row_index']]
    fixtures = []
    for turn in original['rounds']:
        assistant = original['messages'][len(turn['input_messages'])]
        body = request_body([assistant], original['tool_schemas'], cfg, 768)
        fixtures.append({'model': 'CPU_REPLAY_FIXTURE_NOT_TEACHER',
            'choices': [{'message': body['messages'][0], 'finish_reason': 'tool_calls' if assistant.get('tool_calls') else 'stop'}],
            'usage': {'prompt_tokens': turn['input_tokens'], 'completion_tokens': turn['output_tokens']}})
    def replay_factory(values):
        pending = iter(deepcopy(values))
        return lambda body, timeout: next(pending)
    def rollout(transport):
        return teacher_trajectory(row, task, cohort, cfg, transport, lambda: 100,
                                  producer='CPU_REPLAY_FIXTURE_NOT_TRAINING')
    # Fail if ANY production network transport accidentally executes during audit.
    with patch.object(urllib.request.OpenerDirector, 'open', side_effect=AssertionError('Network forbidden')):
        replayed = rollout(replay_factory(fixtures))
        write_json(experiment.path/'replay_fixture.json', replayed)
        check('real_state_and_replay', replayed.get('online_replay_equal') is True and not replayed['infra_invalid'])
        def actions(record):
            return [(e['tool_call']['name'], json.loads(e['tool_call']['arguments'])) for e in record['events']]
        check('same_official_actions', actions(replayed) == actions(original))
        check('same_final_state', replayed['final_state_sha256'] == original['final_state_sha256'])
        check('fixture_not_eligible', replayed['training_eligible'] is False and replayed['producer'] == 'CPU_REPLAY_FIXTURE_NOT_TRAINING')
        check('all_turns_retained', len(replayed['rounds']) == len(original['rounds']))
        truncated = deepcopy(fixtures[0]); truncated['choices'][0]['finish_reason'] = 'length'
        incomplete = rollout(replay_factory([truncated]))
        check('truncated_calls_not_executed', incomplete['termination'] == 'generation_incomplete' and not incomplete['events'])
        def failed_request(body, timeout):
            raise APIError('http_error', 401)
        invalid = rollout(failed_request)
        check('api_error_excluded', invalid['infra_invalid'] and invalid['http_status'] == 401)
        check('api_error_no_retry', invalid['api_attempts'] == 1 and invalid['usage_unknown_requests'] == 1)
        malformed = deepcopy(fixtures[0]); malformed['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{broken'
        bad = rollout(replay_factory([malformed]))
        check('malformed_policy_call_not_infra', not bad['infra_invalid'] and bad['termination'] == 'malformed_tool_call' and not bad['events'])
        thinking = deepcopy(fixtures[0]); thinking['choices'][0]['message']['reasoning_content'] = 'fixture'
        reject('thinking_disabled_contract', lambda: assistant_from_response(thinking))
    write_json(experiment.path/'checks.json', checks)
    result = {'status': 'CPU_COLLECTOR_CHECKS_PASSED' if all(x['passed'] for x in checks) else 'GATE_FAILED',
              'checks_passed': sum(x['passed'] for x in checks), 'checks_total': len(checks),
              'external_api_requests': 0, 'new_model_rollouts': 0, 'new_training_approvals': 0,
              'parameter_updates': 0, 'gpu_hours': 0, 'paid_cost_rmb': 0,
              'fixture_scope': 'Previously unapproved training707 replay only; not teacher quality or training evidence'}
    experiment.finish(result, 'completed' if result['status'].endswith('PASSED') else 'gate_failed')
    print(json.dumps(result, indent=2))
    if not all(x['passed'] for x in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True)
    run(parser.parse_args().run_id)
