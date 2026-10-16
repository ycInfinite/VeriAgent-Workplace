"""CPU-only preregistration and unchanged-runner checks for six current-S1 pairs."""
import ast
import argparse
import json
import traceback
from pathlib import Path
from common import ROOT
from veriagent.dpo import load_pairs
from veriagent.sft_stage import read, sha
from evaluate_current_s1_preference import load_eval


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', default='CURPREF-PREP-20261016-001'); args = parser.parse_args()
    assert args.run_id.startswith('CURPREF-PREP-') and Path(args.run_id).name == args.run_id
    out = ROOT/'experiments'/args.run_id; out.mkdir(exist_ok=False)
    def save(name, value):
        with (out/name).open('x', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    checks = {}
    try:
        cfg, pairs = load_pairs('configs/current_s1_preference_plan.json'); _, ev, rows = load_eval()
        old = read(ROOT/'configs/preference_comparison_plan.json')
        save('config.json', cfg)
        checks['six_distinct_once'] = len(cfg['task_order']) == len(set(cfg['task_order'])) == cfg['optimizer_updates'] == 6 and set(cfg['task_order']) == {p['task_id'] for p in pairs}
        checks['only_six_reviewed_reward_gap'] = {p['task_id'] for p in pairs} == {1076,1000,473,349,1194,51} and all(p['preference_type'] == 'approved_reward_gap_pair' for p in pairs)
        checks['train_dev_disjoint'] = not {p['task_uid'] for p in pairs} & {r['task_uid'] for r in rows}
        checks['same_exact_S1'] = cfg['initial_adapter_path'] == old['initial_adapter_path'] and cfg['initial_adapter_sha256'] == old['initial_adapter_sha256']
        checks['same_hyperparameters'] = all(cfg[k] == old[k] for k in ['seed','beta','learning_rate','max_context_tokens','scoring','required_packages','model_revision'])
        checks['same_dev_protocol'] = ev == old['evaluation'] and len(rows) == 24
        checks['complete_all39_turns'] = sum(p[s]['turn_count'] for p in pairs for s in ['chosen','rejected']) == 39
        checks['review_cpu_controls_passed'] = read(ROOT/'experiments/S1-PAIR-REVIEW-20261016-001/cpu_controls.json')['passed'] == 12
        for oldname, newname in [('run_preference_comparison.py','run_current_s1_preference.py'),
                                  ('evaluate_preference_comparison.py','evaluate_current_s1_preference.py'),
                                  ('compare_preference_evaluations.py','compare_current_s1_preferences.py')]:
            oldtext = (ROOT/'scripts'/oldname).read_text(encoding='utf-8')
            expected = oldtext.replace('configs/preference_comparison_plan.json','configs/current_s1_preference_plan.json').replace("cfg['optimizer_updates']==12","cfg['optimizer_updates']==6").replace("tr['optimizer_updates']==12","tr['optimizer_updates']==6")
            expected = expected.replace('Frozen twelve-task','Frozen six-task current-S1').replace('Matched exposed-dev outcomes','Matched current-S1 six-pair exposed-dev outcomes')
            checks[newname+'_only_registered_differences'] = (ROOT/'scripts'/newname).read_text(encoding='utf-8') == expected
        import github_file_sync as sync
        tree = ast.parse(sync.REMOTE_CODE)
        remote = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'current_preference_files' for t in n.targets))
        checks['exact_GitHub_whitelist'] = set(cfg['deployment_files']) == set(sync.CURRENT_PREFERENCE_FILES) == remote
        for path in cfg['deployment_files']:
            if path.endswith('.py'): ast.parse((ROOT/path).read_text(encoding='utf-8'))
        checks['pipeline_keeps_power_on'] = not cfg['instance_shutdown_authorized'] and 'shutdown(' not in (ROOT/'scripts/run_current_s1_preference_pipeline.py').read_text(encoding='utf-8')
        checks['pipeline_no_undeployed_common_import'] = 'from common import' not in (ROOT/'scripts/run_current_s1_preference_pipeline.py').read_text(encoding='utf-8')
        assert all(checks.values()), checks
        save('identity.json', {'parent_commit':'121a0061130ee1ff8a7918b613676b79ad274f5b', 'files':{p:sha(ROOT/p) for p in cfg['deployment_files']},
            'transport_sha256':sha(ROOT/'scripts/github_file_sync.py'), 'old_frozen_files':{p:sha(ROOT/p) for p in ['configs/preference_comparison_plan.json','scripts/run_preference_comparison.py','scripts/evaluate_preference_comparison.py','veriagent/dpo.py']}})
        save('result.json', {'status':'CPU_CURRENT_S1_COMPARISON_PREPARED', 'checks':checks, 'planned_updates_per_arm':6,
            'planned_dev_rollouts':144, 'training_targets':{s:sum(p[s]['target_tokens'] for p in pairs) for s in ['chosen','rejected']},
            'processed_tokens':sum(p[s]['processed_tokens'] for p in pairs for s in ['chosen','rejected']),
            'actual_GPU_hours':0,'actual_parameter_updates':0,'actual_HF_Torch_checks':'pending_on_host'})
        print(json.dumps({'status':'CPU_CURRENT_S1_COMPARISON_PREPARED','checks_passed':len(checks),'planned_updates':12,'planned_rollouts':144}))
    except Exception:
        save('invalid_run.json', {'checks':checks,'traceback':traceback.format_exc(),'model_run':False}); raise


if __name__ == '__main__':
    main()
