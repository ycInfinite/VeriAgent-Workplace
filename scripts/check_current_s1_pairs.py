"""Offline corruption controls and resource summary for completed25 acquisition."""
import copy
import gzip
import json
import statistics
from datetime import datetime, timezone
from common import ROOT
from prepare_postsft_audit import branch
from veriagent.sft_stage import read, sha
from veriagent.teacher_data import CanonicalTeacherEncoder


def main():
    out = ROOT/'experiments/S1-PAIR-REVIEW-20261016-001'
    run = ROOT/'experiments/S1-FAILURE-ACQUIRE-20261012-001'
    pairs = []
    for name in ['reward_gap_pairs.jsonl.gz', 'same_reward_pairs.jsonl.gz']:
        with gzip.open(out/name, 'rt', encoding='utf-8') as f:
            pairs.extend(map(json.loads, f))
    rows = [json.loads(x) for x in (run/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
    encoder = CanonicalTeacherEncoder(8192)
    fixture = next(r for r in rows if r['task_id'] == 1000)
    checks = {}
    def rejected(name, modified, selected_encoder=encoder):
        try:
            branch(modified, selected_encoder)
        except (AssertionError, ValueError):
            checks[name] = True
        else:
            checks[name] = False
    x = copy.deepcopy(fixture); x['rounds'][0]['eos_reached'] = False
    rejected('incomplete_assistant_turn_rejected', x)
    x = copy.deepcopy(fixture); x['rounds'][1]['input_messages'][0]['content'] += ' MUTATED'
    rejected('changed_context_rejected', x)
    x = copy.deepcopy(fixture)
    next(m for m in x['messages'][len(x['initial_messages']):] if m['role'] == 'tool')['content'] = 'MUTATED'
    rejected('changed_observation_rejected', x)
    rejected('overlength_not_truncated', copy.deepcopy(fixture), CanonicalTeacherEncoder(64))
    checks['all_context_labels_ignored'] = all(e['labels'][:e['prefix_tokens']] == [-100]*e['prefix_tokens'] for p in pairs for side in ['chosen', 'rejected'] for e in p[side]['encoded_turns'])
    checks['all_assistant_tokens_targeted'] = all(e['labels'][e['prefix_tokens']:] == e['input_ids'][e['prefix_tokens']:] for p in pairs for side in ['chosen', 'rejected'] for e in p[side]['encoded_turns'])
    checks['six_gap_one_same_separate'] = sum(p['preference_type'] == 'approved_reward_gap_pair' for p in pairs) == 6 and sum(p['preference_type'] == 'approved_same_reward_semantic_pair' for p in pairs) == 1
    checks['censored1179_not_exported'] = all(p['task_id'] != 1179 for p in pairs)
    checks['ambiguous746_not_exported'] = all(p['task_id'] != 746 for p in pairs)
    checks['all_complete_assistant_final'] = all(p[side]['termination'] == 'assistant_final' for p in pairs for side in ['chosen', 'rejected'])
    checks['audit_script_identity_matches'] = read(out/'identity.json')['script_sha256'] == sha(ROOT/'scripts/review_current_s1_pairs.py')
    checks['all_fifty_replays_equal'] = read(out/'replay.json')['all_equal'] and len(read(out/'replay.json')['branches']) == 50
    assert all(checks.values()), checks
    with (out/'cpu_controls.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump({'checks': checks, 'passed': len(checks), 'GPU_or_HF_runtime_validation': False}, f, indent=2)
    samples = [json.loads(x) for x in (run/'gpu_samples.jsonl').read_text(encoding='utf-8').splitlines()]
    parsed = [s['sample'].split(', ') for s in samples if s['returncode'] == 0]
    result = read(run/'result.json')
    evidence = ROOT/'evidence/s1-failure-execution-20261016'
    ops = evidence/'remote_operations/logs/s1collect20261016'
    host = read(ops/'host.json'); preserve = read(ops/'preservation.json')
    resource = {'script_wall_seconds': result['wall_seconds'], 'script_GPU_hours': result['gpu_hours'],
        'trajectory_seconds_sum': sum(r['trajectory_latency_seconds'] for r in rows),
        'input_tokens': sum(r['input_tokens'] for r in rows), 'output_tokens': sum(r['output_tokens'] for r in rows),
        'model_rounds': sum(r['model_rounds'] for r in rows),
        'peak_torch_allocated_GiB': max(r['peak_torch_allocated_bytes'] for r in rows)/2**30,
        'peak_torch_reserved_GiB': max(r['peak_torch_reserved_bytes'] for r in rows)/2**30,
        'device_sample_peak_used_GiB': max(float(s[2]) for s in parsed)/1024,
        'sample_mean_GPU_util_percent': statistics.mean(float(s[3]) for s in parsed), 'samples': len(parsed),
        'sampling_scope': 'Whole collector including weight checks/load; nvidia-smi samples, not continuous occupancy integral',
        'container_start_estimate_to_preservation_GPU_hours': (preserve['observed_epoch']-host['container_start_estimate'])/3600,
        'first_project_observation_to_preservation_GPU_hours': (preserve['observed_epoch']-host['first_observed_epoch'])/3600,
        'script_GPU_hours_per_official_success': result['gpu_hours']/18,
        'script_GPU_hours_per_reward_gap_pair': result['gpu_hours']/6,
        'script_GPU_hours_per_all_admitted_pair': result['gpu_hours']/7,
        'hourly_RMB': None, 'cost_RMB': None, 'invoice_verified': False, 'storage_excluded': True,
        'instance_kept_on_by_user': True, 'cost_continues_after_preservation': True,
        'SSH_closed_after_verified_retrieval': True, 'shutdown_command_or_guard': False,
        'recorded_at': datetime.now(timezone.utc).isoformat()}
    with (evidence/'resource_summary.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(resource, f, indent=2)
    print(json.dumps({'controls': checks, 'resources': resource}))


if __name__ == '__main__':
    main()
