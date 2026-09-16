"""Remote CPU-only teacher collection; key entered in a real non-echoing terminal."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import importlib.metadata
import json
import os
import re
import sys
import threading
import time
import warnings

from run_day3 import ROOT, write, append
from collect_training_probe import validate_inputs
from veriagent.environment import WorkplaceEnv
from veriagent.teacher_data import teacher_request, CanonicalTeacherEncoder
from veriagent.teacher_rollout import BailianTransport, teacher_trajectory, validate_endpoint


def preflight(config):
    required = ['Research Question', 'Hypothesis', 'Independent Variable', 'Controlled Variables',
                'Metrics', 'Evidence Gate', 'Cost Bound', 'Failure Branch']
    if any(not config.get(key) for key in required):
        raise ValueError('Incomplete preregistration')
    expected = {'model': 'qwen3.8-max', 'billing_mode': 'ordinary_pay_as_you_go',
        'max_tasks': 20, 'max_requests': 120, 'max_model_rounds': 6,
        'max_context_tokens': 8192, 'max_output_tokens_per_model_call': 768,
        'max_output_tokens_per_trajectory': 2048, 'max_wall_seconds': 1800,
        'enable_thinking': False, 'retries': 0}
    if any(config.get(k) != v for k, v in expected.items()):
        raise ValueError('Acquisition scope differs from the bounded plan')
    validate_endpoint(config['base_url'])
    build = json.loads((ROOT/'bundle_manifest.json').read_text())
    entries = {entry['path']: entry for entry in build['files']}
    essential = ['scripts/collect_teacher_probe.py', 'veriagent/teacher_rollout.py',
                 'veriagent/teacher_data.py', 'configs/teacher_acquisition_plan.json',
                 config['cohort_manifest'], config['data_path']]
    if any(path not in entries for path in essential):
        raise ValueError('Teacher execution files missing from verified GitHub deployment')
    for entry in entries.values():
        path = (ROOT/entry['path']).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Deployment file hash mismatch')
    if build.get('code_transport') != 'GitHub fixed-ref temporary raw-file downloads':
        raise ValueError('Expected exact-ref GitHub deployment')
    cohort = json.loads((ROOT/config['cohort_manifest']).read_text())
    rows = [json.loads(line) for line in (ROOT/config['data_path']).read_text().splitlines() if line.strip()]
    validate_inputs(config, cohort, rows)
    encoder = CanonicalTeacherEncoder(config['max_context_tokens'])
    if encoder.checked.model_revision != config['student_revision']:
        raise ValueError('Student revision mismatch')
    tasks = {task['task_uid']: task for task in cohort['tasks']}
    coverage = []
    for row in rows:
        request = teacher_request(row, tasks[row['task_uid']], cohort['B1_addition'])
        prompt = encoder.inspector.render(request['messages'], request['tools'], generate=True)
        tokens = len(encoder.inspector.tokenizer.encode(prompt, add_special_tokens=False).ids)
        coverage.append({'task_id': row['id'], 'student_initial_tokens': tokens,
                         'fits': tokens < config['max_context_tokens']})
    return build, cohort, rows, tasks, coverage


def summary(records, config):
    valid = [r for r in records if not r['infra_invalid']]
    calls = [c for r in valid for c in r['call_diagnostics']]
    malformed = sum(len(r['parse_errors']) for r in valid)
    inputs = sum(r['input_tokens'] for r in records)
    outputs = sum(r['output_tokens'] for r in records)
    unknown = sum(r['usage_unknown_requests'] for r in records)
    known_cost = (inputs*config['input_rmb_per_million'] + outputs*config['output_rmb_per_million'])/1e6
    return {'attempted_rollouts': len(records), 'valid_rollouts': len(valid),
        'infra_invalid_rollouts': len(records)-len(valid),
        'verified_successes': sum(r['verifier']['official_reward'] == 1 for r in valid),
        'success_rate': sum(r['verifier']['official_reward'] == 1 for r in valid)/len(valid) if valid else None,
        'tool_calls': len(calls), 'malformed_calls': malformed,
        'executable_tool_calls': sum(c['executable_gate'] for c in calls),
        'executable_call_rate': sum(c['executable_gate'] for c in calls)/(len(calls)+malformed) if calls or malformed else None,
        'provider_prompt_tokens': inputs, 'provider_completion_tokens': outputs,
        'student_supervised_tokens': sum(r['student_supervised_tokens'] for r in records),
        'api_attempts': sum(r['api_attempts'] for r in records), 'usage_unknown_requests': unknown,
        'known_usage_list_price_rmb': known_cost,
        'total_cost_estimate_rmb': None if unknown else known_cost,
        'cost_caveat': 'Undiscounted documented list price; no free/cache benefit assumed; errors may have unknown charges; excludes host/storage',
        'training_approved_trajectories': 0, 'parameter_updates': 0, 'local_gpu_hours': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id')
    parser.add_argument('--base-url', help='Ordinary Beijing endpoint from your workspace API example; never a key')
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--prompt-key', action='store_true')
    args = parser.parse_args()
    cfg = json.loads((ROOT/'configs/teacher_acquisition_plan.json').read_text())
    if args.base_url:
        cfg['base_url'] = args.base_url
    build, cohort, rows, tasks, coverage = preflight(cfg)
    print(json.dumps({'status': 'CPU_PREFLIGHT', 'coverage': coverage,
                      'code_commit': build['code_commit'], 'api_requests': 0}), flush=True)
    if not all(item['fits'] for item in coverage):
        raise ValueError('Initial context coverage failed; no truncation')
    if args.preflight_only:
        return
    if not args.run_id or not re.fullmatch(r'TEACHER-ACQUIRE-\d{8}-\d{3}', args.run_id):
        raise ValueError('An immutable TEACHER-ACQUIRE-YYYYMMDD-NNN ID is required')
    out = ROOT/'experiments'/args.run_id
    if out.exists():
        raise FileExistsError('Experiment ID already used; no overwrite/resume/retry')
    env_name = cfg['api_key_environment']
    if args.prompt_key:
        if os.name != 'posix' or not sys.stdin.isatty():
            raise ValueError('Enter key only in a real remote Linux terminal')
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            os.environ[env_name] = getpass.getpass('Ordinary Bailian API key (hidden; remote process only): ')
    transport = BailianTransport(cfg)
    out.mkdir(parents=True, exist_ok=False)
    write(out/'config.json', cfg)
    write(out/'context_coverage.json', coverage)
    write(out/'initial_state.json', WorkplaceEnv().initial_state)
    identity = {'experiment_id': args.run_id, 'started_at': datetime.now(timezone.utc).isoformat(),
        'kind': 'REAL_API_TRAINING_DATA_ACQUISITION_NO_UPDATE', 'code_commit': build['code_commit'],
        'bundle_manifest': build, 'requested_model': cfg['model'], 'model_revision': None,
        'student_revision': cfg['student_revision'], 'dataset_revision': build['dataset_revision'],
        'seed': cfg['seed'], 'provider_reproducibility': cfg['seed_reproducibility'],
        'packages': {name: importlib.metadata.version(name) for name in ('tokenizers', 'jinja2', 'pandas', 'numpy', 'jsonschema')},
        'credential_persisted': False, 'key_source': 'remote_terminal' if args.prompt_key else 'remote_process_environment'}
    write(out/'identity.json', identity)
    append(ROOT/'experiments/registry.jsonl', {'experiment_id': args.run_id, 'event': 'started', 'identity': identity})
    records = []; started = time.perf_counter()
    def deadline():
        write(out/'deadline.json', {'status': 'PROCESS_DEADLINE', 'completed_trajectories': len(records),
                                  'partial_request_evidence': 'api_events.jsonl', 'inflight_charge_unknown': True})
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': args.run_id, 'event': 'deadline_incomplete'})
        os._exit(124)
    timer = threading.Timer(cfg['max_wall_seconds'], deadline); timer.daemon = True; timer.start()
    try:
        for row in rows:
            if time.perf_counter()-started >= cfg['max_wall_seconds']-1:
                raise TimeoutError('Process time bound')
            record = teacher_trajectory(row, tasks[row['task_uid']], cohort, cfg, transport,
                lambda: cfg['max_wall_seconds']-(time.perf_counter()-started),
                lambda event: append(out/'api_events.jsonl', event))
            record['experiment_id'] = args.run_id
            records.append(record); append(out/'trajectories.jsonl', record)
            progress = summary(records, cfg); write(out/'progress.json', progress)
            print(json.dumps({'completed': len(records), 'task_id': row['id'],
                'reward': record['verifier']['official_reward'], 'termination': record['termination'],
                'infra_invalid': record['infra_invalid']}), flush=True)
            if record['infra_invalid']:
                raise RuntimeError('Infrastructure/contract failure; automatic retry disabled')
        result = summary(records, cfg)
        result.update({'status': 'ACQUIRED_REQUIRES_EXPLICIT_FULL_TRAJECTORY_REVIEW',
                       'wall_seconds': time.perf_counter()-started})
        write(out/'result.json', result)
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': args.run_id, 'event': 'completed'})
    except Exception as exc:
        result = summary(records, cfg)
        result.update({'status': 'INCOMPLETE_REQUIRES_REVIEW', 'error_type': type(exc).__name__,
                       'wall_seconds': time.perf_counter()-started})
        write(out/'result.json', result)
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': args.run_id, 'event': 'invalid_or_incomplete'})
        raise
    finally:
        timer.cancel()
        os.environ.pop(env_name, None)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid traceback locals/HTTP bodies/headers and inherited env in logs.
        print(json.dumps({'status': 'STOPPED', 'error_type': type(exc).__name__,
                          'detail': 'Inspect non-secret preflight or experiment result; no automatic retry'}), flush=True)
        raise SystemExit(1)
    finally:
        os.environ.pop('VERIAGENT_BAILIAN_API_KEY', None)
