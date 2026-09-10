"""Per-turn policy-target encoding and strict admission for future SFT data.

No model loading, tool execution, or training. Recorded development examples may
be encoded for diagnostics, but admission to a training export is separate.
"""
from copy import deepcopy
import hashlib
import json

from veriagent.token_mask import TokenMaskInspector


def content_sha256(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


class TurnEncoder:
    def __init__(self, max_context_tokens=8192):
        self.inspector = TokenMaskInspector()
        for artifact in self.inspector.meta['files']:
            actual = hashlib.sha256((self.inspector.path / artifact['name']).read_bytes()).hexdigest()
            if actual != artifact['sha256']:
                raise ValueError('Pinned tokenizer artifact hash mismatch: ' + artifact['name'])
        self.model_revision = self.inspector.meta['model_revision']
        self.max_context_tokens = max_context_tokens
        config = json.loads((self.inspector.path / 'generation_config.json').read_text())
        eos = config['eos_token_id']
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])

    def encode(self, trajectory, turn):
        if trajectory.get('model_revision') != self.model_revision:
            raise ValueError('Model/tokenizer revision mismatch')
        if trajectory.get('infra_invalid') is not False:
            raise ValueError('Infrastructure-invalid or unspecified trajectory')
        if turn.get('eos_reached') is not True:
            raise ValueError('Incomplete generation is not a supervised example')
        prompt = self.inspector.render(turn['input_messages'], trajectory['tool_schemas'], generate=True)
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        if prompt_hash != turn['input_sha256']:
            raise ValueError('Recorded prompt hash mismatch')
        prefix = self.inspector.tokenizer.encode(prompt, add_special_tokens=False).ids
        if len(prefix) != turn['input_tokens']:
            raise ValueError('Recorded input token count mismatch')
        output = list(turn['output_token_ids'])
        if not output or any(type(token) is not int or token < 0 for token in output):
            raise ValueError('Invalid generated token IDs')
        if len(output) != turn['output_tokens'] or output[-1] not in self.eos_ids:
            raise ValueError('Output count or EOS mismatch')
        decoded = self.inspector.tokenizer.decode(output, skip_special_tokens=False)
        if decoded != turn['raw_generation']:
            raise ValueError('Raw generation and output token IDs disagree')
        ids = prefix + output
        if len(ids) > self.max_context_tokens:
            raise ValueError('Per-turn context bound exceeded; truncation forbidden')
        return {
            'task_uid': trajectory['task_uid'], 'task_id': trajectory['task_id'],
            'condition': trajectory['condition'], 'seed': trajectory['seed'],
            'turn': turn['turn'], 'source_pool': trajectory['source_pool'],
            'trajectory_sha256': content_sha256(trajectory),
            'input_sha256': prompt_hash, 'model_revision': self.model_revision,
            'input_ids': ids, 'labels': [-100] * len(prefix) + output,
            'attention_mask': [1] * len(ids),
            'prefix_tokens': len(prefix), 'supervised_tokens': len(output),
            'processed_tokens': len(ids),
            'encoding': 'recorded_per_turn_prefix_plus_actual_generated_ids_v1',
            'training_eligible': False,
        }


def admit_training_trajectory(trajectory, review, approved_tasks, model_revision):
    """Admission requires task-pool proof plus an explicit matching quality review.

    This does not automate semantic judgement; the reviewer must justify grounding,
    target scope and recovery quality using real trajectory evidence.
    """
    if trajectory.get('task_uid') not in approved_tasks:
        raise ValueError('Task is outside the approved training acquisition manifest')
    if trajectory.get('source_pool') != 'training_candidate':
        raise ValueError('Only training_candidate trajectories can enter SFT')
    if trajectory.get('model_revision') != model_revision:
        raise ValueError('Unapproved generating model revision')
    task = approved_tasks[trajectory['task_uid']]
    if trajectory.get('task_id') != task['source_id']:
        raise ValueError('Task ID does not match approved source task')
    if content_sha256(trajectory.get('initial_messages')) != task['initial_messages_sha256']:
        raise ValueError('Initial messages do not match approved training task')
    if content_sha256(trajectory.get('tool_schemas')) != task['tool_schemas_sha256']:
        raise ValueError('Tool schemas do not match approved training task')
    if trajectory.get('producer') != 'Qwen/Qwen3-8B_REAL_MODEL':
        raise ValueError('Unapproved or scripted producer')
    if trajectory.get('infra_invalid') is not False or trajectory.get('online_replay_equal') is not True:
        raise ValueError('Invalid execution or replay evidence')
    if trajectory.get('verifier', {}).get('official_reward') != 1:
        raise ValueError('SFT success pool requires official success')
    if trajectory.get('termination') != 'assistant_final' or trajectory.get('parse_errors'):
        raise ValueError('Budget/incomplete/parser termination requires separate design')
    if not trajectory.get('rounds') or not trajectory.get('events'):
        raise ValueError('Initial probe requires a nonempty real interaction')
    if review.get('trajectory_sha256') != content_sha256(trajectory):
        raise ValueError('Quality review does not match trajectory content')
    if review.get('decision') != 'approved_for_sft_probe':
        raise ValueError('Missing explicit quality approval')
    if not review.get('reviewer') or not review.get('rationale'):
        raise ValueError('Quality review needs attribution and rationale')
    for name in ('grounding_checked', 'target_scope_checked', 'all_supervised_turns_acceptable'):
        if review.get(name) is not True:
            raise ValueError('Missing quality check: ' + name)
    return True


def export_training_turns(trajectory, review, approved_tasks, encoder):
    admit_training_trajectory(trajectory, review, approved_tasks, encoder.model_revision)
    encoded = [encoder.encode(trajectory, turn) for turn in trajectory['rounds']]
    for example in encoded:
        example['training_eligible'] = True
        example['quality_review'] = deepcopy(review)
    return encoded
