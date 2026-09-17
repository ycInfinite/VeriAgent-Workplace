"""Teacher request isolation and canonical student formatting, without API calls.

Different teachers have different tokenizers. Re-encode complete visible assistant
turns with the fixed student tokenizer; never claim these are teacher sampled IDs.
This module does not approve data or relax the existing SFT admission gate.
"""
from copy import deepcopy
import hashlib
import json

from veriagent.sft_data import content_sha256, TurnEncoder


def teacher_request(row, task, general_instruction):
    if task['pool'] != 'training_candidate' or task['source_split'] != 'train':
        raise ValueError('Teacher request must come from training pool')
    if row['id'] != task['source_id']:
        raise ValueError('Teacher task identity mismatch')
    messages=deepcopy(row['responses_create_params']['input'])
    messages[0]['content']+='\n\n'+general_instruction
    tools=deepcopy(row['responses_create_params']['tools'])
    request={'messages':messages,'tools':tools}
    validate_request(request,task)
    return request


def validate_request(request,task):
    if set(request)!={'messages','tools'}:
        raise ValueError('Unexpected request field, including verifier/oracle data')
    if task['pool']!='training_candidate':
        raise ValueError('Non-training task')
    if content_sha256(request['messages'])!=task['initial_messages_sha256']:
        raise ValueError('Initial task/prompt differs from fixed B1 cohort')
    if content_sha256(request['tools'])!=task['tool_schemas_sha256']:
        raise ValueError('Tools differ from fixed cohort')
    return True


class CanonicalTeacherEncoder:
    def __init__(self,max_context_tokens=8192):
        self.checked=TurnEncoder(max_context_tokens)
        self.inspector=self.checked.inspector
        self.max_context_tokens=max_context_tokens

    def encode(self,prefix_messages,tools,assistant_message):
        if assistant_message.get('role')!='assistant':
            raise ValueError('Only a visible assistant turn can be a target')
        if set(assistant_message)-{'role','content','tool_calls'}:
            raise ValueError('Unspecified assistant fields require an explicit normalization policy')
        prefix=self.inspector.render(prefix_messages,tools,generate=True)
        complete=self.inspector.render(prefix_messages+[assistant_message],tools,generate=False)
        if not complete.startswith(prefix):
            raise ValueError('Canonical assistant prefix is not a continuation of the input')
        suffix=complete[len(prefix):]
        if not suffix.endswith('<|im_end|>\n'):
            raise ValueError('Unexpected canonical assistant termination')
        # The renderer adds a separator newline after EOS; it is not a policy target.
        target_text=suffix[:-1]
        prefix_ids=self.inspector.tokenizer.encode(prefix,add_special_tokens=False).ids
        target_ids=self.inspector.tokenizer.encode(target_text,add_special_tokens=False).ids
        if not target_ids or target_ids[-1] not in self.checked.eos_ids:
            raise ValueError('Canonical target lacks EOS')
        if len(prefix_ids)+len(target_ids)>self.max_context_tokens:
            raise ValueError('Canonical sequence exceeds bound; no truncation')
        if self.inspector.tokenizer.decode(prefix_ids+target_ids,skip_special_tokens=False)!=prefix+target_text:
            raise ValueError('Canonical encoding roundtrip mismatch')
        return {'input_ids':prefix_ids+target_ids,'labels':[-100]*len(prefix_ids)+target_ids,
            'attention_mask':[1]*(len(prefix_ids)+len(target_ids)),
            'prefix_tokens':len(prefix_ids),'supervised_tokens':len(target_ids),
            'processed_tokens':len(prefix_ids)+len(target_ids),
            'prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),
            'canonical_target_sha256':hashlib.sha256(target_text.encode()).hexdigest(),
            'student_model_revision':self.checked.model_revision,
            'format':'canonical_qwen_non_thinking_complete_visible_assistant_turn_v1',
            'teacher_token_ids_used':False,'training_eligible':False}


def export_teacher_turns(record, review, approved_tasks, encoder, teacher_config,
                         *, source_provider='bailian', required_decision='approved_for_sft_probe'):
    """Admit a whole reviewed API trajectory, retaining every visible decision.

    Separate from the exact sampled-ID admission path for the original 8B policy.
    Raw request/response identity, message continuity and actual observations must
    agree; a successful verifier alone never authorizes a training export.
    """
    from veriagent.teacher_rollout import assistant_from_response, request_body, read_usage
    from veriagent.environment import digest
    response_validator = None
    if source_provider == 'deepseek':
        from veriagent.deepseek_teacher import request_body, validate_response, endpoint
        endpoint(teacher_config['base_url'])
        if (teacher_config['model'] != 'deepseek-flash'
                or teacher_config['enable_thinking'] is not False
                or teacher_config['seed'] is not None
                or required_decision != 'approved_for_sft'):
            raise ValueError('Unqualified DeepSeek source or approval scope')
        response_validator = validate_response
        expected_producer = 'DEEPSEEK_REAL_API'
    elif source_provider == 'bailian' and required_decision == 'approved_for_sft_probe':
        expected_producer = 'BAILIAN_REAL_API'
    else:
        raise ValueError('Unknown or mismatched teacher admission scope')
    task = approved_tasks.get(record.get('task_uid'))
    if (not task or task['pool'] != 'training_candidate' or task['source_split'] != 'train'
            or record.get('source_pool') != 'training_candidate' or record.get('task_id') != task['source_id']):
        raise ValueError('Teacher trajectory is not in the fixed training cohort')
    validate_request({'messages': record['initial_messages'], 'tools': record['tool_schemas']}, task)
    if (record.get('producer') != expected_producer or record.get('requested_model') != teacher_config['model']
            or record.get('student_model_revision') != encoder.checked.model_revision
            or record.get('condition') != 'B1' or record.get('seed') != teacher_config['seed']):
        raise ValueError('Teacher/student provenance mismatch')
    if (record.get('infra_invalid') is not False or record.get('online_replay_equal') is not True
            or record.get('verifier', {}).get('official_reward') != 1
            or record.get('termination') != 'assistant_final' or record.get('parse_errors')):
        raise ValueError('Teacher execution is unsuccessful, incomplete, or invalid')
    if (review.get('trajectory_sha256') != content_sha256(record)
            or review.get('decision') != required_decision
            or not review.get('reviewer') or not review.get('rationale')
            or any(review.get(k) is not True for k in
                ('grounding_checked', 'target_scope_checked', 'all_supervised_turns_acceptable'))):
        raise ValueError('Missing matching full-trajectory quality approval')
    rounds, events, messages = record['rounds'], record['events'], record['messages']
    if (not events or not 1 <= len(rounds) <= teacher_config['max_model_rounds']
            or record.get('api_attempts') != len(rounds) or record.get('usage_unknown_requests') != 0):
        raise ValueError('Incomplete API/tool evidence')
    cursor = len(record['initial_messages']); event_index = 0
    if messages[:cursor] != record['initial_messages']:
        raise ValueError('Initial message continuity mismatch')
    examples = []; inputs = outputs = 0
    for index, turn in enumerate(rounds, 1):
        if turn['turn'] != index or turn['input_messages'] != messages[:cursor]:
            raise ValueError('A whole teacher turn is missing or altered')
        response = turn['raw_response']
        if response_validator is not None:
            response_validator(response)
        assistant, finish, errors = assistant_from_response(response)
        if (errors or finish not in ('stop', 'tool_calls') or finish != turn['finish_reason']
                or assistant != turn['assistant_message'] or assistant != messages[cursor]
                or not isinstance(response.get('model'), str) or not response['model']):
            raise ValueError('Raw API response does not match visible assistant target')
        body = request_body(turn['input_messages'], record['tool_schemas'], teacher_config, turn['provider_output_cap'])
        if digest(body) != turn['request_body_sha256']:
            raise ValueError('Recorded API request differs from the registered teacher config')
        inp, out = read_usage(response); inputs += inp; outputs += out
        if (inp != turn['provider_input_tokens'] or out != turn['provider_output_tokens']
                or out > turn['provider_output_cap']):
            raise ValueError('Usage mismatch')
        example = encoder.encode(turn['input_messages'], record['tool_schemas'], assistant)
        if (example['prefix_tokens'] != turn['student_prefix_tokens']
                or example['supervised_tokens'] != turn['student_supervised_tokens']
                or example['processed_tokens'] != turn['student_processed_tokens']):
            raise ValueError('Student canonical encoding metadata differs')
        cursor += 1
        for call in assistant.get('tool_calls', []):
            event = events[event_index]; event_index += 1
            if (event['tool_call']['name'] != call['function']['name']
                    or json.loads(event['tool_call']['arguments']) != call['function']['arguments']):
                raise ValueError('API action does not match executed tool event')
            expected = {'role': 'tool', 'tool_call_id': call['id'],
                        'content': json.dumps(event['observation'], ensure_ascii=False, default=str)}
            if messages[cursor] != expected:
                raise ValueError('Actual tool observation differs from policy context')
            cursor += 1
        example.update({'task_uid': record['task_uid'], 'task_id': record['task_id'], 'turn': index,
            'condition': 'B1', 'seed': record['seed'], 'source_pool': 'training_candidate',
            'trajectory_sha256': content_sha256(record), 'input_sha256': example['prefix_sha256'],
            'model_revision': encoder.checked.model_revision, 'teacher_requested_model': record['requested_model'],
            'teacher_returned_model': response['model'], 'teacher_model_revision': record.get('model_revision'),
            'encoding': example['format'], 'training_eligible': True, 'quality_review': deepcopy(review)})
        examples.append(example)
    if (cursor != len(messages) or event_index != len(events)
            or inputs != record['input_tokens'] or outputs != record['output_tokens']
            or sum(x['supervised_tokens'] for x in examples) != record['student_supervised_tokens']
            or outputs > teacher_config['max_output_tokens_per_trajectory']
            or record['student_supervised_tokens'] > teacher_config['max_output_tokens_per_trajectory']):
        raise ValueError('Whole-trajectory continuity or token budget mismatch')
    return examples
