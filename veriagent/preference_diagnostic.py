"""Frozen post-training fit diagnostics. No torch import or optimization."""
import copy
import gzip
import math
from .dpo import load_pairs, cache_key, scalar_loss_and_coefficient
from .sft_stage import ROOT, read, sha, require
from .sft_data import content_sha256

PLAN = 'configs/preference29_diagnostic.json'


def load_inputs():
    cfg, pairs = load_pairs(PLAN)
    require(sha(ROOT/cfg['data_path']) == cfg['data_sha256'], 'Changed training29 input')
    require(sha(ROOT/cfg['selection_path']) == cfg['selection_sha256'], 'Changed selection')
    require(sha(ROOT/cfg['reference_path']) == cfg['reference_sha256'], 'Changed S1 reference cache')
    with gzip.open(ROOT/cfg['data_path'], 'rt', encoding='utf-8') as f:
        rows = [__import__('json').loads(x) for x in f]
    require(len(rows) == len(pairs) == 29 and [r['id'] for r in rows] == cfg['task_order'], 'Wrong29 cohort/order')
    require([r['task_uid'] for r in rows] == cfg['task_uids'] and len(set(cfg['task_uids'])) == 29, 'Duplicate/wrong UID')
    selection = {x['task_id']: x for x in read(ROOT/cfg['selection_path'])['tasks']}
    byid = {p['task_id']: p for p in pairs}
    reference = read(ROOT/cfg['reference_path'])
    require(set(reference) == {p['pair_id'] for p in pairs}, 'Reference pair set mismatch')
    for row in rows:
        p = byid[row['id']]
        require(row['source_pool'] == 'training_candidate', 'Nontraining diagnostic input')
        messages = copy.deepcopy(row['responses_create_params']['input'])
        messages[0]['content'] += '\n\n'+cfg['B1_addition']
        require(messages == p['prompt_context'] and row['responses_create_params']['tools'] == p['tools'], 'Changed initial context/tools')
        require(content_sha256(messages) == selection[row['id']]['messages_sha256'] and content_sha256(p['tools']) == selection[row['id']]['tools_sha256'], 'Selection hash mismatch')
        require(selection[row['id']]['empty_reference'] == (not bool(row['ground_truth'])), 'Wrong reference stratum')
        ref = reference[p['pair_id']]
        require(ref['cache_key'] == cache_key(cfg, p), 'Reference policy/data identity differs')
        require(all(math.isfinite(ref[s]) for s in ['chosen', 'rejected']), 'Invalid reference score')
    return cfg, [byid[i] for i in cfg['task_order']], rows, reference


def score_change(chosen, rejected, ref, chosen_tokens, rejected_tokens, beta):
    require(chosen_tokens > 0 and rejected_tokens > 0, 'Missing target tokens')
    loss, _ = scalar_loss_and_coefficient(chosen, rejected, ref['chosen'], ref['rejected'], beta)
    dc, dr = chosen-ref['chosen'], rejected-ref['rejected']
    return {'chosen_logp': chosen, 'rejected_logp': rejected,
            'reference_chosen_logp': ref['chosen'], 'reference_rejected_logp': ref['rejected'],
            'chosen_delta': dc, 'rejected_delta': dr, 'relative_margin': dc-dr,
            'chosen_mean_logp_delta': dc/chosen_tokens, 'rejected_mean_logp_delta': dr/rejected_tokens,
            'mean_logp_margin_delta_diagnostic_only': dc/chosen_tokens-dr/rejected_tokens,
            'DPO_loss': loss, 'chosen_target_tokens': chosen_tokens, 'rejected_target_tokens': rejected_tokens}
