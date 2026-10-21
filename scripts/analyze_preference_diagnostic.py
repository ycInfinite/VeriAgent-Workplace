"""Join frozen-pair fit and real training-task execution without selecting checkpoints."""
import json
import statistics
from common import ROOT
from veriagent.preference_diagnostic import load_inputs
from veriagent.sft_stage import read, require, sha


def main():
    cfg, pairs, rows, reference = load_inputs()
    out = ROOT/'reports/preference-diagnostic-20261019/analysis.json'
    require(not out.exists(), 'Do not overwrite analysis')
    report = {'scope': 'Selectedtraining29;notgeneralization;S1failuresareselectioncriterion',
              'reference_hash': cfg['reference_sha256'], 'conditions': {}, 'paired_outcome_changes': []}
    groups = {}
    commits = set()
    for arm in ['CHOSEN_SFT', 'DPO']:
        score = ROOT/'experiments'/cfg['score_run_ids'][arm]
        roll = ROOT/'experiments'/cfg['rollout_run_ids'][arm]
        require(read(score/'result.json')['status'] == read(roll/'result.json')['status'] == 'DIAGNOSTIC_COMPLETE', 'Incomplete diagnostic')
        for path in [score, roll]:
            ident = read(path/'identity.json')
            require(ident['policy'] == cfg['policies'][arm], 'Wrong frozen policy')
            commits.add(ident['code_commit'])
        scores = {x['task_uid']: x for x in map(json.loads, (score/'scores.jsonl').read_text(encoding='utf-8').splitlines())}
        runs = {x['task_uid']: x for x in map(json.loads, (roll/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        require(set(scores) == set(runs) == set(cfg['task_uids']), 'Wrong task set')
        require(all(not x['infra_invalid'] and x['seed'] == 42 for x in runs.values()), 'Invalid run or seed')
        groups[arm] = runs
        items = [{**scores[u], 'reward': runs[u]['verifier']['official_reward'], 'termination': runs[u]['termination']} for u in cfg['task_uids']]
        def aggregate(xs):
            return {'n': len(xs), 'mean_relative_margin': statistics.mean(x['relative_margin'] for x in xs),
                'mean_DPO_loss': statistics.mean(x['DPO_loss'] for x in xs),
                'margin_positive': sum(x['relative_margin'] > cfg['cache_tolerance'] for x in xs),
                'chosen_logp_increased': sum(x['chosen_delta'] > cfg['cache_tolerance'] for x in xs),
                'rejected_logp_decreased': sum(x['rejected_delta'] < -cfg['cache_tolerance'] for x in xs),
                'mean_chosen_delta': statistics.mean(x['chosen_delta'] for x in xs),
                'mean_rejected_delta': statistics.mean(x['rejected_delta'] for x in xs),
                'mean_chosen_logp_per_token_delta': statistics.mean(x['chosen_mean_logp_delta'] for x in xs),
                'mean_rejected_logp_per_token_delta': statistics.mean(x['rejected_mean_logp_delta'] for x in xs),
                'official_success': sum(x['reward'] == 1 for x in xs),
                'positive_margin_but_official_failure': sum(x['relative_margin'] > cfg['cache_tolerance'] and x['reward'] == 0 for x in xs)}
        subsets = {'all': items, 'empty': [x for x in items if x['empty_reference']],
                   'nonempty': [x for x in items if not x['empty_reference']]}
        subsets.update({category: [x for x in items if x['category'] == category] for category in sorted({x['category'] for x in items})})
        subsets.update({'chosen_shorter': [x for x in items if x['chosen_target_tokens'] < x['rejected_target_tokens']],
                        'chosen_longer_or_equal': [x for x in items if x['chosen_target_tokens'] >= x['rejected_target_tokens']]})
        report['conditions'][arm] = {'groups': {k: aggregate(v) for k,v in subsets.items() if v},
                                    'tasks': items, 'scores_sha256': sha(score/'scores.jsonl'),
                                    'rollouts_sha256': sha(roll/'trajectories.jsonl')}
    require(len(commits) == 1, 'Mixed diagnostic execution versions')
    report['execution_commit'] = commits.pop()
    for uid in cfg['task_uids']:
        a, b = groups['CHOSEN_SFT'][uid], groups['DPO'][uid]
        if a['verifier']['official_reward'] != b['verifier']['official_reward']:
            report['paired_outcome_changes'].append({'task_id': a['task_id'], 'task_uid': uid,
                'SFT_reward': a['verifier']['official_reward'], 'DPO_reward': b['verifier']['official_reward']})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({a: v['groups'] for a,v in report['conditions'].items()}, indent=2))


if __name__ == '__main__':
    main()
