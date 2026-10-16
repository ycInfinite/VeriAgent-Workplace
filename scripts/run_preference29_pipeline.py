"""One bounded five-run matrix. Stops on failure; never powers off the instance."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]


def main():
    assert os.name == 'posix' and sys.argv[1:] == ['--execute']
    cfg = json.loads((ROOT/'configs/preference29_plan.json').read_text())
    assert cfg['GPU_training_authorized'] and not cfg['instance_shutdown_authorized']
    out = ROOT/'logs/pref29-20261016'
    out.mkdir(exist_ok=False)
    all_ids = list(cfg['training_run_ids'].values()) + list(cfg['eval_run_ids'].values())
    assert all(not (ROOT/'experiments'/run).exists() for run in all_ids), 'Used immutable run ID'
    phases = [('torch_controls', ['scripts/check_preference_torch.py']),
              ('train_data_controls', ['scripts/run_preference29.py', '--condition', 'DPO']),
              ('dev_data_controls', ['scripts/evaluate_preference29.py', '--condition', 'S1'])]
    def ev(arm):
        args = ['scripts/evaluate_preference29.py', '--condition', arm, '--execute', '--run-id', cfg['eval_run_ids'][arm]]
        if arm != 'S1':
            args += ['--training-run', cfg['training_run_ids'][arm]]
        return args
    phases += [('eval_S1', ev('S1'))]
    for arm in ['CHOSEN_SFT', 'DPO']:
        phases += [('train_'+arm, ['scripts/run_preference29.py', '--condition', arm, '--execute', '--run-id', cfg['training_run_ids'][arm]]),
                   ('eval_'+arm, ev(arm))]
    started = time.time(); completed = []
    def save(obj):
        tmp = out/'status.tmp'
        tmp.write_text(json.dumps({'started_epoch': started, 'updated_epoch': time.time(), 'completed': completed,
            'instance_shutdown_authorized': False, **obj}, indent=2))
        tmp.replace(out/'status.json')
    for phase, args in phases:
        remaining = 9000-(time.time()-started)
        if remaining < 1900:
            save({'status': 'STOPPED_PROCESS_LIFECYCLE_BOUND', 'next_phase': phase}); return 124
        with (out/(phase+'.log')).open('xb') as log:
            proc = subprocess.Popen([sys.executable, '-u', *args], cwd=ROOT, stdout=log,
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            save({'status': 'RUNNING', 'phase': phase, 'child_pid': proc.pid, 'command': args})
            try:
                code = proc.wait(timeout=1900)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                code = 124
        if code:
            save({'status': 'FAILED_STOPPED_NO_RETRY', 'phase': phase, 'exit_code': code}); return code
        completed.append({'phase': phase, 'ended_epoch': time.time(), 'exit_code': code})
        save({'status': 'PHASE_COMPLETE', 'phase': phase})
    save({'status': 'COMPLETE_KEEP_INSTANCE_ON'}); return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--import-only']:
        print(json.dumps({'status': 'PIPELINE_STDLIB_IMPORT_PASSED_NO_MODEL'}))
    else:
        raise SystemExit(main())
