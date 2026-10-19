"""Five inference-only phases, bounded processes, keep the user instance on."""
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
    cfg = json.loads((ROOT/'configs/preference29_diagnostic.json').read_text())
    assert cfg['GPU_inference_authorized'] and not cfg['GPU_training_authorized'] and not cfg['instance_shutdown_authorized']
    ids = [cfg['reference_run_id'], *cfg['score_run_ids'].values(), *cfg['rollout_run_ids'].values()]
    assert all(not (ROOT/'experiments'/run).exists() for run in ids), 'Immutable ID already used'
    out = ROOT/'logs/pref29-diagnostic-20261019'
    out.mkdir(exist_ok=False)
    phases = [('reference', 'S1'), ('score', 'CHOSEN_SFT'), ('score', 'DPO'),
              ('rollout', 'CHOSEN_SFT'), ('rollout', 'DPO')]
    started = time.time()
    completed = []
    def save(**fields):
        temp = out/'status.tmp'
        temp.write_text(json.dumps({'started_epoch': started, 'updated_epoch': time.time(),
            'completed': completed, 'instance_shutdown_authorized': False, **fields}, indent=2))
        temp.replace(out/'status.json')
    for mode, arm in phases:
        phase = mode+'_'+arm
        if time.time()-started+1900 > cfg['pipeline_wall_seconds']:
            save(status='LIFECYCLE_BOUND_STOPPED', phase=phase)
            return 124
        command = [sys.executable, '-u', 'scripts/run_preference_diagnostic.py', '--mode', mode,
                   '--condition', arm, '--execute']
        with (out/(phase+'.log')).open('xb') as f:
            proc = subprocess.Popen(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            save(status='RUNNING', phase=phase, child_pid=proc.pid)
            try:
                code = proc.wait(timeout=1900)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code = 124
        if code:
            save(status='FAILED_STOPPED_NO_RETRY', phase=phase, exit_code=code)
            return code
        completed.append({'phase': phase, 'ended_epoch': time.time(), 'exit_code': 0})
    save(status='COMPLETE_KEEP_INSTANCE_ON')
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--import-only']:
        print(json.dumps({'status': 'STDLIB_PIPELINE_IMPORT_OK_NO_MODEL'}))
    else:
        raise SystemExit(main())
