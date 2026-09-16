"""Bounded ordinary Bailian API transport and real Workplace tool loop.

No SDK retries, key files, response repair, automatic quality approval or training.
Transport injection is for clearly labelled CPU fixtures only.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from jsonschema import Draft202012Validator
from veriagent.environment import WorkplaceEnv, snapshot, digest, canonical
from veriagent.policy_protocol import identifier_candidates
from veriagent.teacher_data import teacher_request, CanonicalTeacherEncoder
from resources_servers.workplace_assistant.utils import execute_actions_and_reset_state


class APIError(Exception):
    def __init__(self, kind, status=None):
        self.kind, self.status = kind, status
        super().__init__(kind)  # Never include HTTP exception/request/header text.


def validate_endpoint(base_url):
    parsed = urllib.parse.urlsplit(base_url)
    host = parsed.hostname or ''
    allowed = host == 'dashscope.aliyuncs.com' or bool(re.fullmatch(
        r'[a-z0-9-]+\.cn-beijing\.maas\.aliyuncs\.com', host))
    if (not allowed or host.startswith('token-plan.') or parsed.scheme != 'https'
            or parsed.path != '/compatible-mode/v1' or parsed.query or parsed.fragment
            or parsed.username or parsed.password or parsed.port is not None):
        raise ValueError('Only the documented ordinary Beijing API endpoint is allowed')
    return base_url + '/chat/completions'


def wire_messages(messages):
    result = deepcopy(messages)
    for message in result:
        for call in message.get('tool_calls', []):
            args = call['function']['arguments']
            if isinstance(args, dict):
                call['function']['arguments'] = json.dumps(args, ensure_ascii=False, allow_nan=False)
    return result


def request_body(messages, schemas, config, cap):
    # Change only the API envelope; preserve every official schema field.
    tools = []
    for schema in schemas:
        if schema.get('type') != 'function':
            raise ValueError('Unsupported official tool type')
        tools.append({'type': 'function', 'function': {
            key: deepcopy(value) for key, value in schema.items() if key != 'type'}})
    return {'model': config['model'], 'messages': wire_messages(messages), 'tools': tools,
            'stream': False, 'enable_thinking': False, 'seed': config['seed'],
            'temperature': config['temperature'], 'top_p': config['top_p'],
            'max_tokens': cap}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise APIError('redirect_refused', code)


class BailianTransport:
    def __init__(self, config):
        self.url = validate_endpoint(config['base_url'])
        self.key_env = config['api_key_environment']
        key = os.environ.get(self.key_env, '')
        if not key or key.startswith('sk-sp-') or any(c.isspace() for c in key):
            raise ValueError('Missing ordinary API key or subscription key supplied')
        self.opener = urllib.request.build_opener(NoRedirect())

    def __call__(self, body, timeout):
        key = os.environ[self.key_env]
        request = urllib.request.Request(self.url, method='POST',
            data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise APIError('response_size_limit')
            value = json.loads(raw)
            # Defensive: never persist a response reflecting our credential.
            if key in json.dumps(value, ensure_ascii=False):
                raise APIError('credential_reflected_response_suppressed')
            return value
        except APIError:
            raise
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise APIError('http_error', status) from None
        except Exception:
            raise APIError('network_or_response_error') from None


def read_usage(response):
    usage = response.get('usage', {})
    values = [usage.get(k) for k in ('prompt_tokens', 'completion_tokens')]
    if any(type(x) is not int or x < 0 for x in values):
        raise APIError('missing_or_invalid_usage')
    return values


def assistant_from_response(response):
    choices = response.get('choices')
    if not isinstance(choices, list) or len(choices) != 1:
        raise APIError('unexpected_choices')
    choice = choices[0]
    message = choice.get('message', {})
    if message.get('role') != 'assistant':
        raise APIError('unexpected_message_role')
    if message.get('reasoning_content'):
        raise APIError('unexpected_thinking_output')
    content = message.get('content')
    if content is not None and not isinstance(content, str):
        raise APIError('unsupported_content_type')
    assistant = {'role': 'assistant', 'content': content or ''}
    calls = message.get('tool_calls') or []
    errors = []
    normalized = []
    seen = set()
    for index, call in enumerate(calls):
        try:
            call_id = call['id']
            if (not isinstance(call_id, str) or not call_id or call_id in seen
                    or call['type'] != 'function' or not isinstance(call['function']['name'], str)):
                raise ValueError('Invalid call envelope')
            seen.add(call_id)
            args = call['function']['arguments']
            if not isinstance(args, str):
                raise ValueError('Expected JSON argument string')
            args = json.loads(args, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite')))
            if not isinstance(args, dict):
                raise ValueError('Arguments must be object')
            normalized.append({'id': call_id, 'type': 'function',
                               'function': {'name': call['function']['name'], 'arguments': args}})
        except (KeyError, TypeError, ValueError):
            errors.append({'call_index': index, 'error': 'Malformed tool-call structure or arguments'})
    if normalized:
        assistant['tool_calls'] = normalized
    return assistant, choice.get('finish_reason'), errors


def teacher_trajectory(row, task, cohort, config, transport, remaining_seconds,
                       response_sink=lambda item: None, producer='BAILIAN_REAL_API'):
    request = teacher_request(row, task, cohort['B1_addition'])
    messages, schemas = request['messages'], request['tools']
    encoder = CanonicalTeacherEncoder(config['max_context_tokens'])
    env = WorkplaceEnv()
    validators = {s['name']: Draft202012Validator(s['parameters']) for s in schemas}
    record = {'task_id': row['id'], 'task_uid': task['task_uid'], 'source_pool': 'training_candidate',
        'condition': 'B1', 'seed': config['seed'], 'producer': producer,
        'requested_model': config['model'], 'model_revision': None, 'returned_models': [],
        'student_model_revision': config['student_revision'], 'initial_messages': deepcopy(messages),
        'tool_schemas': schemas, 'initial_state_sha256': digest(env.initial_state),
        'rounds': [], 'call_diagnostics': [], 'parse_errors': [], 'infra_invalid': False,
        'input_tokens': 0, 'output_tokens': 0, 'student_supervised_tokens': 0,
        'api_attempts': 0, 'usage_unknown_requests': 0, 'training_eligible': False}
    started = time.perf_counter()
    termination = 'round_limit'
    history = []
    try:
        for turn in range(1, config['max_model_rounds'] + 1):
            if remaining_seconds() <= 1:
                raise APIError('process_deadline')
            prompt = encoder.inspector.render(messages, schemas, generate=True)
            prefix_count = len(encoder.inspector.tokenizer.encode(prompt, add_special_tokens=False).ids)
            if prefix_count >= config['max_context_tokens']:
                termination = 'student_context_limit'; break
            remaining = config['max_output_tokens_per_trajectory'] - record['output_tokens']
            if remaining <= 0:
                termination = 'provider_output_limit'; break
            if record['student_supervised_tokens'] >= config['max_output_tokens_per_trajectory']:
                termination = 'student_output_limit'; break
            cap = min(config['max_output_tokens_per_model_call'], remaining)
            body = request_body(messages, schemas, config, cap)
            current = {'turn': turn, 'input_messages': deepcopy(messages),
                       'student_prefix_tokens': prefix_count, 'provider_output_cap': cap,
                       'request_body_sha256': digest(body)}
            record['rounds'].append(current)
            response_sink({'task_id': row['id'], 'turn': turn, 'event': 'request_started',
                           'body': body})  # No headers, credentials, oracle or env dump.
            record['api_attempts'] += 1
            record['usage_unknown_requests'] += 1
            call_start = time.perf_counter()
            response = transport(body, min(config['request_timeout_seconds'], remaining_seconds()))
            current['model_latency_seconds'] = time.perf_counter() - call_start
            response_sink({'task_id': row['id'], 'turn': turn, 'event': 'response', 'body': response})
            current['raw_response'] = response
            input_count, output_count = read_usage(response)
            record['usage_unknown_requests'] -= 1
            record['input_tokens'] += input_count; record['output_tokens'] += output_count
            current.update({'provider_input_tokens': input_count, 'provider_output_tokens': output_count})
            if response.get('model') not in record['returned_models']:
                record['returned_models'].append(response.get('model'))
            if output_count > cap:
                raise APIError('provider_output_cap_violation')
            assistant, finish, errors = assistant_from_response(response)
            current.update({'finish_reason': finish, 'assistant_message': assistant})
            record['parse_errors'].extend({'turn': turn, **err} for err in errors)
            if finish == 'length':
                termination = 'generation_incomplete'; break  # Never execute partial calls.
            if finish not in ('stop', 'tool_calls'):
                termination = 'provider_noncompletion'; break
            if errors:
                termination = 'malformed_tool_call'; break  # No repair or invented feedback.
            try:
                encoded = encoder.encode(messages, schemas, assistant)
            except ValueError as exc:
                current['encoding_error'] = str(exc)
                termination = 'student_encoding_rejected'; break
            current['student_supervised_tokens'] = encoded['supervised_tokens']
            current['student_processed_tokens'] = encoded['processed_tokens']
            record['student_supervised_tokens'] += encoded['supervised_tokens']
            if record['student_supervised_tokens'] > config['max_output_tokens_per_trajectory']:
                termination = 'student_output_limit'; break
            visible = json.dumps([m for m in messages if m['role'] in ('user', 'tool')], ensure_ascii=False)
            messages.append(assistant)
            calls = assistant.get('tool_calls', [])
            if not calls:
                termination = 'assistant_final'; break
            for index, call in enumerate(calls):
                name, args = call['function']['name'], call['function']['arguments']
                state = digest(snapshot(env.tools))
                signature = (name, canonical(args), state)
                errors = [] if name not in validators else [e.message for e in validators[name].iter_errors(args)]
                event = env.step({'name': name, 'arguments': json.dumps(args, ensure_ascii=False)})
                record['call_diagnostics'].append({'turn': turn, 'call_index': index, 'step': event['step'],
                    'name': name, 'arguments': args, 'known_tool': name in validators, 'schema_errors': errors,
                    'executable_gate': name in validators and not errors and event['exception'] is None,
                    'identifiers': identifier_candidates(args, visible),
                    'same_call_same_state_before': signature in history,
                    'three_call_loop': len(history) >= 2 and history[-2:] == [signature, signature],
                    'tool_exception': event['exception']})
                history.append(signature)
                messages.append({'role': 'tool', 'tool_call_id': call['id'],
                    'content': json.dumps(event['observation'], ensure_ascii=False, default=str)})
    except APIError as exc:
        record.update({'infra_invalid': True, 'infra_failure_kind': exc.kind, 'http_status': exc.status})
        termination = 'infra_failure'
    except Exception as exc:
        record.update({'infra_invalid': True, 'infra_failure_kind': type(exc).__name__})
        termination = 'infra_failure'
    try:
        record['verifier'] = env.verify(row['ground_truth'])
        with redirect_stdout(io.StringIO()):
            replay = execute_actions_and_reset_state([e['tool_call'] for e in env.events])
        record['online_replay_equal'] = snapshot(replay) == snapshot(env.tools)
        if not record['online_replay_equal']:
            record.update({'infra_invalid': True, 'infra_failure_kind': 'online_replay_mismatch'})
    except Exception as exc:
        record['verifier'] = {'official_reward': None, 'error_type': type(exc).__name__}
        record.update({'infra_invalid': True, 'infra_failure_kind': 'verifier_exception'})
    record.update({'messages': messages, 'events': env.events, 'termination': termination,
        'reference_action_count': len(row['ground_truth']), 'reference': row['ground_truth'],
        'final_state_sha256': digest(snapshot(env.tools)), 'tool_steps': len(env.events),
        'trajectory_latency_seconds': time.perf_counter() - started})
    return record
