"""CPU-only diagnostic gates; originalS1 may live only on the qualified host."""
import ast
import json
import math
import traceback
from common import ROOT
from veriagent.preference_diagnostic import load_inputs, score_change
from veriagent.sft_stage import read, sha


def main():
    out = ROOT/'experiments/PREF29-DIAG-PREP-20261019-002'
    out.mkdir(exist_ok=False)
    checks = {}
    def save(name, obj):
        (out/name).write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')
    try:
        cfg, pairs, rows, refs = load_inputs()
        old = read(ROOT/'configs/preference29_plan.json')
        checks['same29_order'] = cfg['task_order'] == old['task_order'] and len(rows) == 29
        checks['whole179_turns'] = sum(p[s]['turn_count'] for p in pairs for s in ['chosen','rejected']) == 179
        checks['same14empty'] = sum(not bool(x['ground_truth']) for x in rows) == 14
        checks['train_dev_disjoint'] = not set(cfg['task_uids']) & set(old['evaluation']['task_uids'])
        checks['same_hyperparameters'] = all(cfg[k] == old[k] for k in ['model_revision','required_packages','beta','scoring','B1_addition'])
        checks['same_generation'] = all(cfg[k] == old['evaluation'][k] for k in ['max_context_tokens','max_model_rounds','max_output_tokens_per_model_call','max_output_tokens_per_trajectory','temperature','top_p'])
        checks['cache29_keys_passed'] = len(refs) == 29
        availability = {}
        for arm, policy in cfg['policies'].items():
            availability[arm] = {}
            for name, expected in policy['sha256'].items():
                path = ROOT/policy['adapter_path']/name
                if path.exists():
                    assert sha(path) == expected, 'Wrong local adapter hash'
                    availability[arm][name] = 'LOCAL_SHA_VERIFIED'
                else:
                    availability[arm][name] = 'LOCAL_ABSENT_REMOTE_RUNTIME_REQUIRED'
        checks['two_new_adapters_locally_verified'] = all(v == 'LOCAL_SHA_VERIFIED' for arm in ['CHOSEN_SFT','DPO'] for v in availability[arm].values())
        checks['S1_identity_frozen'] = cfg['policies']['S1']['sha256'] == old['initial_adapter_sha256']
        checks['identity_scores_loss_ln2'] = abs(score_change(-10,-5,{'chosen':-10,'rejected':-5},10,5,.1)['DPO_loss']-math.log(2)) < 1e-12
        z = score_change(-8,-7,{'chosen':-10,'rejected':-5},10,5,.1)
        checks['margin_and_loss_direction'] = z['relative_margin'] == 4 and z['DPO_loss'] < math.log(2) and z['chosen_delta'] == 2 and z['rejected_delta'] == -2
        z = score_change(-10,-9,{'chosen':-10,'rejected':-5},10,5,.1)
        checks['suppression_is_not_chosen_improvement'] = z['chosen_delta'] == 0 and z['relative_margin'] == 4
        checks['meanlogp_diagnostic'] = abs(z['mean_logp_margin_delta_diagnostic_only']-.8) < 1e-12
        ids = [cfg['reference_run_id'], *cfg['score_run_ids'].values(), *cfg['rollout_run_ids'].values()]
        checks['new5_ids'] = len(set(ids)) == 5 and all(not (ROOT/'experiments'/i).exists() for i in ids)
        runtime = (ROOT/'scripts/run_preference_diagnostic.py').read_text(encoding='utf-8')
        checks['no_parameter_updates'] = 'optimizer' not in runtime and '.backward(' not in runtime and not cfg['GPU_training_authorized']
        import github_file_sync as sync
        tree = ast.parse(sync.REMOTE_CODE)
        remote = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'preference_diagnostic_files' for t in n.targets))
        checks['whitelist'] = set(cfg['deployment_files']) == set(sync.PREFERENCE_DIAGNOSTIC_FILES) == remote
        pipeline = (ROOT/'scripts/run_preference_diagnostic_pipeline.py').read_text(encoding='utf-8')
        checks['keep_on'] = not cfg['instance_shutdown_authorized'] and 'shutdown(' not in pipeline
        for f in cfg['deployment_files']:
            if f.endswith('.py'):
                ast.parse((ROOT/f).read_text(encoding='utf-8'))
        assert all(checks.values()), checks
        save('result.json', {'status': 'CPU_DIAGNOSTIC_PREPARATION_PASSED', 'checks': checks,
            'local_adapter_availability': availability, 'actual_GPU_calls': 0, 'actual_updates': 0,
            'planned_scores': '29pairsx2newmodels plus2fixedS1calibrationpairs', 'planned_rollouts': 58})
        save('config.json', cfg)
        save('identity.json', {'files': {f: sha(ROOT/f) for f in cfg['deployment_files']},
            'old_core_sha256': {f: sha(ROOT/f) for f in ['veriagent/dpo.py','scripts/run_day3.py','configs/preference29_plan.json']}})
        print(json.dumps({'status': 'CPU_DIAGNOSTIC_PREPARATION_PASSED', 'checks': len(checks)}))
    except Exception:
        save('invalid_run.json', {'checks': checks, 'traceback': traceback.format_exc(), 'model_calls': 0})
        raise


if __name__ == '__main__':
    main()
