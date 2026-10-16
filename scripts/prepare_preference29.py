"""Freeze and validate exact29 comparison, without loading a model."""
import ast
import json
import traceback
from common import ROOT
from veriagent.dpo import load_pairs
from veriagent.sft_stage import read, sha
from evaluate_preference29 import load_eval


def main():
    out = ROOT/'experiments/PREF29-PREP-20261016-001'
    out.mkdir(exist_ok=False)
    def save(name, value):
        (out/name).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    checks = {}
    try:
        cfg, pairs = load_pairs('configs/preference29_plan.json')
        _, ev, rows = load_eval()
        old = read(ROOT/'configs/current_s1_preference_plan.json')
        proposal = read(ROOT/'configs/preference29_comparison_proposal.json')
        checks['exact29_once'] = len(cfg['task_order']) == len(set(cfg['task_order'])) == cfg['optimizer_updates'] == 29 and set(cfg['task_order']) == {p['task_id'] for p in pairs}
        checks['approved_reward_gap_only'] = all(p['preference_type'] == 'approved_reward_gap_pair' for p in pairs)
        checks['unchanged_proposed_order'] = cfg['task_order'] == proposal['task_order']
        checks['train_dev_disjoint'] = not {p['task_uid'] for p in pairs} & {r['task_uid'] for r in rows}
        checks['same_S1_hyperparameters'] = all(cfg[k] == old[k] for k in ['initial_adapter_path','initial_adapter_sha256','seed','beta','learning_rate','max_context_tokens','scoring','required_packages','model_revision','B1_addition'])
        checks['same_eval'] = ev == old['evaluation'] and len(rows) == 24
        checks['whole179_turns'] = sum(p[s]['turn_count'] for p in pairs for s in ['chosen','rejected']) == 179
        preflight = read(ROOT/cfg['preflight_evidence'])
        checks['actual_HF_longest_gradient_passed'] = preflight['status'] == 'FULL_HF_LONGEST_PAIR_GRADIENT_PREFLIGHT_PASSED' and preflight['HF_turns'] == 179 and preflight['optimizer_updates'] == 0
        for source, target in [('run_current_s1_preference.py','run_preference29.py'),('evaluate_current_s1_preference.py','evaluate_preference29.py'),('compare_current_s1_preferences.py','compare_preference29.py')]:
            expected = (ROOT/'scripts'/source).read_text(encoding='utf-8').replace('configs/current_s1_preference_plan.json','configs/preference29_plan.json').replace("cfg['optimizer_updates']==6","cfg['optimizer_updates']==29").replace("tr['optimizer_updates']==6","tr['optimizer_updates']==29").replace('Frozen six-task current-S1','Frozen29-task current-S1').replace('Matched current-S1 six-pair','Matched current-S1 29-pair')
            if target == 'run_preference29.py':
                expected = expected.replace("    build=validate_deployment(cfg['deployment_files'])", "    require(cfg['GPU_training_authorized'], 'Training not authorized')\n    build=validate_deployment(cfg['deployment_files'])", 1)
                expected = expected.replace('        actual_count=actual_tokenizer_check(tokenizer,pairs)', "        actual_count=actual_tokenizer_check(tokenizer,pairs)\n        require(actual_count==179, 'Whole29 HF turn count changed')", 1)
            checks[target+'_only_registered_differences'] = expected == (ROOT/'scripts'/target).read_text(encoding='utf-8')
        import github_file_sync as sync
        tree = ast.parse(sync.REMOTE_CODE)
        remote = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'preference29_files' for t in n.targets))
        checks['deployment_whitelist'] = set(cfg['deployment_files']) == set(sync.PREFERENCE29_FILES) == remote
        pipeline = (ROOT/'scripts/run_preference29_pipeline.py').read_text(encoding='utf-8')
        checks['keep_on_standalone_pipeline'] = not cfg['instance_shutdown_authorized'] and 'shutdown(' not in pipeline and 'from common import' not in pipeline
        ids = list(cfg['training_run_ids'].values())+list(cfg['eval_run_ids'].values())
        checks['new_ids'] = len(set(ids)) == 5 and all(not (ROOT/'experiments'/i).exists() for i in ids)
        for p in cfg['deployment_files']:
            if p.endswith('.py'):
                ast.parse((ROOT/p).read_text(encoding='utf-8'))
        assert all(checks.values()), checks
        save('config.json', cfg)
        save('identity.json', {'files': {p: sha(ROOT/p) for p in cfg['deployment_files']},
            'historical_files': {p: sha(ROOT/p) for p in ['scripts/run_current_s1_preference.py','configs/current_s1_preference_plan.json','veriagent/dpo.py','scripts/run_day3.py']}})
        save('result.json', {'status': 'CPU_PREF29_PREPARATION_PASSED', 'checks': checks, 'updates_per_arm': 29,
            'dev_rollouts': 144, 'actual_updates': 0, 'training_targets': {s: sum(p[s]['target_tokens'] for p in pairs) for s in ['chosen','rejected']}})
        print(json.dumps({'passed': len(checks), 'updates': 0, 'planned_updates': 58, 'planned_rollouts': 144}))
    except Exception:
        save('invalid_run.json', {'checks': checks, 'traceback': traceback.format_exc(), 'model_loaded': False})
        raise


if __name__ == '__main__':
    main()
