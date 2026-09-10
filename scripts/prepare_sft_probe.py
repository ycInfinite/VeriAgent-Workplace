"""CPU-only encoding audit and deterministic training-only acquisition selection."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import time

from common import ROOT, Run, load_rows, write_json
from veriagent.sft_data import TurnEncoder, admit_training_trajectory, content_sha256


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_rejection(name, operation):
    try:
        operation()
    except ValueError as exc:
        return {'name': name, 'passed': True, 'reason': str(exc)}
    return {'name': name, 'passed': False, 'reason': 'Unexpected admission'}


def run(run_id, config_path):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    exp = Run(run_id, config)
    start = time.monotonic()
    try:
        encoder = TurnEncoder(config['max_context_tokens'])
        manifest_path = ROOT / config['split_manifest']
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        plan = json.loads((ROOT / 'configs/model_qualification_plan.json').read_text())
        rows = load_rows('train')  # Never load official validation case contents.
        candidates = [x for x in manifest['records'] if x['pool'] == 'training_candidate'
                      and config['acquisition_reference_call_min'] <= x['reference_action_count']
                      <= config['acquisition_reference_call_max']]
        selected = []
        for category in sorted({x['category'] for x in candidates}):
            domain = [x for x in candidates if x['category'] == category]
            domain.sort(key=lambda x: hashlib.sha256(
                f"{config['seed']}:{x['task_uid']}".encode()).hexdigest())
            if len(domain) < config['acquisition_tasks_per_domain']:
                raise ValueError('Insufficient training-only tasks in a domain')
            for metadata in domain[:config['acquisition_tasks_per_domain']]:
                row = rows[metadata['source_row_index']]
                if row['id'] != metadata['source_id'] or metadata['source_split'] != 'train':
                    raise ValueError('Source task mismatch')
                messages = deepcopy(row['responses_create_params']['input'])
                messages[0]['content'] += '\n\n' + plan['B1_addition']
                schemas = row['responses_create_params']['tools']
                prompt = encoder.inspector.render(messages, schemas, generate=True)
                count = len(encoder.inspector.tokenizer.encode(prompt, add_special_tokens=False).ids)
                selected.append({**metadata, 'initial_input_tokens': count,
                    'initial_messages_sha256': content_sha256(messages),
                    'tool_schemas_sha256': content_sha256(schemas),
                    'initial_prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'initial_context_fits': count < config['max_context_tokens']})
        if len(selected) != config['acquisition_max_rollouts']:
            raise ValueError('Selected cohort size does not match rollout cap')
        approved = {x['task_uid']: x for x in selected}
        acquisition = {'status': 'FIXED_TRAINING_ONLY_ACQUISITION_COHORT_NOT_COLLECTED',
            'selection_seed': config['seed'], 'rollout_seed': config['acquisition_seed'],
            'model_revision': config['model_revision'], 'prompt_condition': config['acquisition_prompt_condition'],
            'B1_addition': plan['B1_addition'], 'split_manifest': config['split_manifest'],
            'split_manifest_sha256': sha_file(manifest_path),
            'selection_rule': '4 per business domain, nonempty reference of 1-4 calls, sorted by seed/task_uid SHA256; no model-performance-based reselection',
            'tasks': selected, 'max_rollouts': len(selected), 'no_final_case_contents_loaded': True}
        write_json(exp.path / 'acquisition_manifest.json', acquisition)

        counts = Counter()
        maxima = Counter()
        input_hashes = {config['split_manifest']: sha_file(manifest_path)}
        first_pair = None
        dev_records = []
        for source_run in config['source_runs']:
            raw_path = ROOT / 'experiments' / source_run / 'trajectories.jsonl'
            input_hashes[str(raw_path.relative_to(ROOT))] = sha_file(raw_path)
            for line in raw_path.read_text(encoding='utf-8').splitlines():
                record = json.loads(line)
                dev_records.append(record)
                counts['trajectories_audited'] += 1
                rejected = expect_rejection('development_training_admission', lambda r=record:
                    admit_training_trajectory(r, {}, approved, encoder.model_revision))
                if not rejected['passed']:
                    raise ValueError('Development trajectory was admitted to training')
                counts['development_trajectories_rejected_from_training'] += 1
                for turn in record['rounds']:
                    if time.monotonic() - start > config['max_wall_seconds']:
                        raise TimeoutError('CPU audit wall time cap exceeded')
                    example = encoder.encode(record, turn)
                    prefix = example['prefix_tokens']
                    if example['labels'][:prefix] != [-100] * prefix:
                        raise ValueError('Unmasked context prefix')
                    if example['labels'][prefix:] != turn['output_token_ids']:
                        raise ValueError('Targets differ from actual generated IDs')
                    prompt = encoder.inspector.render(turn['input_messages'], record['tool_schemas'], generate=True)
                    has_prefill = prompt.endswith('<think>\n\n</think>\n\n')
                    if not has_prefill:
                        raise ValueError('Unexpected non-thinking generation prefix')
                    if first_pair is None:
                        first_pair = (record, turn)
                    counts['model_turns_audited'] += 1
                    counts['prompt_hash_matches'] += 1
                    counts['exact_generated_target_matches'] += 1
                    counts['forced_prefill_masked_as_input'] += 1
                    counts['processed_tokens'] += example['processed_tokens']
                    counts['supervised_tokens'] += example['supervised_tokens']
                    counts['prefix_tokens'] += prefix
                    maxima['max_processed_tokens_per_turn'] = max(maxima['max_processed_tokens_per_turn'],example['processed_tokens'])
                    maxima['max_supervised_tokens_per_turn'] = max(maxima['max_supervised_tokens_per_turn'],example['supervised_tokens'])
                    # Only numeric/hash diagnostics are saved, never a trainable dev corpus.
                    exp.append('turn_audit.jsonl', {k: example[k] for k in (
                        'task_uid','task_id','condition','seed','turn','source_pool','trajectory_sha256',
                        'input_sha256','model_revision','prefix_tokens','supervised_tokens','processed_tokens',
                        'encoding','training_eligible')} | {'source_run': source_run,
                        'target_ids_sha256': content_sha256(turn['output_token_ids']),
                        'prefix_mask_verified': True, 'forced_prefill_in_input': has_prefill})

        record, turn = first_pair
        controls = []
        changed = deepcopy(turn); changed['input_sha256'] = '0' * 64
        controls.append(expect_rejection('tampered_prompt_hash', lambda: encoder.encode(record,changed)))
        changed = deepcopy(turn); changed['output_token_ids'][0] += 1
        controls.append(expect_rejection('tampered_generated_ids', lambda: encoder.encode(record,changed)))
        changed = deepcopy(turn); changed['eos_reached'] = False
        controls.append(expect_rejection('incomplete_generation', lambda: encoder.encode(record,changed)))
        altered = deepcopy(record); altered['infra_invalid'] = True
        controls.append(expect_rejection('infrastructure_invalid', lambda: encoder.encode(altered,turn)))
        altered = deepcopy(record); altered['model_revision'] = 'wrong-revision'
        controls.append(expect_rejection('wrong_model_revision', lambda: encoder.encode(altered,turn)))
        controls.append(expect_rejection('development_pool_even_if_uid_allowed', lambda:
            admit_training_trajectory(record, {}, {record['task_uid']: {}}, encoder.model_revision)))
        altered = deepcopy(record); altered['source_pool'] = 'training_candidate'
        altered['task_uid'] = selected[0]['task_uid']; altered['task_id'] = selected[0]['source_id']
        controls.append(expect_rejection('relabelled_dev_as_training_task', lambda:
            admit_training_trajectory(altered, {}, approved, encoder.model_revision)))
        write_json(exp.path / 'negative_controls.json', controls)
        write_json(exp.path / 'input_hashes.json', input_hashes)
        all_passed = all(x['passed'] for x in controls) and all(x['initial_context_fits'] for x in selected)
        result = {'status': 'CPU_PREPARATION_PASSED_GPU_COLLECTION_AND_TRAINER_PENDING' if all_passed else 'GATE_FAILED',
            **dict(counts), **dict(maxima), 'negative_controls_passed': sum(x['passed'] for x in controls),
            'negative_controls_total': len(controls),
            'training_acquisition_task_count': len(selected),
            'training_acquisition_by_domain': dict(Counter(x['category'] for x in selected)),
            'initial_context_coverage': sum(x['initial_context_fits'] for x in selected) / len(selected),
            'acquisition_initial_tokens_min': min(x['initial_input_tokens'] for x in selected),
            'acquisition_initial_tokens_max': max(x['initial_input_tokens'] for x in selected),
            'eligible_training_trajectories_collected': 0, 'dev_training_export_count': 0,
            'parameter_updates': 0, 'gpu_hours': 0, 'paid_cost_rmb': 0,
            'elapsed_seconds': time.monotonic() - start,
            'limitations': ['CPU reconstruction is not a trainer forward/CE/update/reload check',
                           'one training example per model turn repeats context and defines a declared SFT objective',
                           'quality approval and complete training provenance are still required',
                           'B1 is a probe candidate; full qualification/composition questions remain']}
        exp.finish(result, status='completed' if all_passed else 'gate_failed')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all_passed else 1
    except Exception as exc:
        exp.finish({'status': 'PREPARATION_INVALID', 'error_type': type(exc).__name__,
                    'error': str(exc), 'parameter_updates': 0, 'gpu_hours': 0}, status='invalid')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', default='configs/sft_preparation_audit.json')
    args = parser.parse_args()
    raise SystemExit(run(args.run_id, ROOT / args.config))
