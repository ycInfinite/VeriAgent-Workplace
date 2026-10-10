"""Post-hoc resource and diagnostic summary; no model execution or case selection."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

# Use only these generic functions. Never call review_run or reuse old task labels.
from review_day3_metrics import identifier_review, gpu_samples

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def rate(n, d):
    return {'numerator': n, 'denominator': d, 'rate': n / d if d else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    assert out.is_relative_to(ROOT) and not out.exists()
    report = {
        'scope': 'Fixed exposed development24; no held-out/generalization claim',
        'semantic_review': 'Full semantic rates pending; automatic and typed detectors remain candidates',
        'typed_detector_limits': 'Exact text visibility plus current domain table membership; does not prove entity resolution, correct target scope, or complete lookup',
        'old_day3_semantic_labels_used': False,
        'source_summary_script_sha256': digest(Path(__file__)),
        'typed_detector_module_sha256': digest(ROOT / 'scripts/review_day3_metrics.py'),
        'conditions': {}, 'training': {}, 'task_pairs': [],
    }
    indexed = {}
    for condition, suffix in [('BASE_B1', 'BASE'), ('S1', 'S1'), ('S2', 'S2')]:
        name = f'SFT-EVAL-{suffix}-20261010-001'
        folder = ROOT / 'experiments' / name
        result = read(folder / 'result.json')
        assert result['status'] == 'MATCHED_DEV_EVAL_COMPLETE'
        rows = [json.loads(x) for x in (folder / 'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(rows) == 48 and all(not r['infra_invalid'] and r['online_replay_equal'] for r in rows)
        initial = read(folder / 'initial_state.json')
        findings = []; identity_calls = []; record_calls = []; email_calls = []
        for r in rows:
            for step, fields in identifier_review(r, initial).items():
                if fields:
                    identity_calls.append(fields)
                records = [f for f in fields if f['kind'] == 'record_id']
                emails = [f for f in fields if f['kind'] == 'email_slot']
                if records:
                    record_calls.append(records)
                if emails:
                    email_calls.append(emails)
                if any(f['confirmed_error'] for f in fields):
                    findings.append({'task_id': r['task_id'], 'seed': r['seed'], 'step': step,
                        'candidate_fields': [{**{k: v for k, v in f.items() if k != 'confirmed_error'},
                                              'candidate_error': f['confirmed_error']} for f in fields]})
        report['conditions'][condition] = {
            'run_id': name, 'result': result, 'gpu_polling': gpu_samples(folder / 'gpu_samples.jsonl'),
            'trajectory_sha256': digest(folder / 'trajectories.jsonl'),
            'typed_identifier_candidate_rate': rate(sum(any(f['confirmed_error'] for f in fs) for fs in identity_calls), len(identity_calls)),
            'nonexistent_typed_record_id_rate': rate(sum(any(not f['exists_in_current_typed_column'] for f in fs) for fs in record_calls), len(record_calls)),
            'email_grounding_candidate_rate': rate(sum(any(f['confirmed_error'] for f in fs) for fs in email_calls), len(email_calls)),
            'identifier_candidate_details': findings,
            'latency_interpretation': 'Measured deployment latency; SFT adapters are unmerged, BASE has no adapter; output length also differs',
        }
        indexed[condition] = {(r['task_id'], r['seed']): r for r in rows}
    for arm in ['S1', 'S2']:
        name = f'SFT-{arm}-20261010-001';folder = ROOT / 'experiments' / name
        result = read(folder / 'result.json')
        assert result['status'] == 'SFT_TRAINING_COMPLETE_RELOAD_PASSED'
        steps = [json.loads(x) for x in (folder / 'steps.jsonl').read_text().splitlines()]
        assert len(steps) == 310 and [s['step'] for s in steps] == list(range(1, 311))
        report['training'][arm] = {
            'run_id': name, 'result': result, 'gpu_polling': gpu_samples(folder / 'gpu_samples.jsonl'),
            'step_time_median_seconds': statistics.median(s['seconds'] for s in steps),
            'epoch_mean_sample_CE': {str(e): statistics.mean(s['loss'] for s in steps if s['epoch'] == e) for e in [1, 2]},
            'CE_scope': 'Unweighted mean of per-example target-token mean CE; not policy success or globally token-weighted loss',
            'reload_check': read(folder / 'reload_check.json'),
        }
    assert all(set(x) == set(indexed['BASE_B1']) for x in indexed.values())
    for task, seed in sorted(indexed['BASE_B1']):
        report['task_pairs'].append({'task_id': task, 'seed': seed,
            'conditions': {c: {'reward': rows[(task, seed)]['verifier']['official_reward'],
                'termination': rows[(task, seed)]['termination'], 'tool_steps': rows[(task, seed)]['tool_steps'],
                'output_tokens': rows[(task, seed)]['output_tokens']} for c, rows in indexed.items()}})
    report['measured_script_gpu_hours'] = sum(v['result']['gpu_hours'] for section in ['conditions', 'training'] for v in report[section].values())
    report['instance_allocation_hours'] = None
    report['cost_scope'] = 'Script GPU-hours exclude restoration and gaps; actual billing start/rate unknown. Separate instance receipt required.'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(out), 'conditions': 3, 'training_arms': 2, 'semantic_rates_pending': True}))


if __name__ == '__main__':
    main()
