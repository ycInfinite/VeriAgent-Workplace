"""Whole-trajectory preference scores: policy tokens only, observations are context.

No torch import or model construction during data admission. Runtime scoring uses
sum log probabilities, never length-normalized rewards or environment-token loss.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
from .sft_stage import ROOT, read, require, sha, validate_example
from .sft_data import content_sha256


def scalar_loss_and_coefficient(pc, pr, rc, rr, beta):
    require(beta > 0 and all(math.isfinite(x) for x in [pc, pr, rc, rr, beta]), 'Nonfinite DPO input')
    z = beta * ((pc - pr) - (rc - rr))
    loss = max(0., -z) + math.log1p(math.exp(-abs(z)))
    sigmoid_negative = math.exp(-max(z, 0.)) / (1. + math.exp(-abs(z)))
    return loss, -beta * sigmoid_negative


def cache_key(cfg, pair):
    return content_sha256({'base': cfg['model_revision'], 'adapter': cfg['initial_adapter_sha256'],
        'pair_sha256': content_sha256(pair), 'scoring': cfg['scoring'],
        'packages': cfg['required_packages'], 'dtype': 'bfloat16', 'attention': 'sdpa'})


def load_pairs(plan='configs/dpo_probe_plan.json'):
    cfg = read(ROOT / plan)
    path = ROOT / cfg['pair_artifact']
    require(sha(path) == cfg['pair_artifact_sha256'], 'Pair artifact changed')
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        pairs = [json.loads(line) for line in f]
    require(len(pairs) == cfg['approved_pairs'], 'Wrong pair count')
    require(len({p['task_uid'] for p in pairs}) == len(pairs), 'Duplicate tasks')
    for p in pairs:
        require(p['source_pool'] == 'training_candidate' and p['dpo_data_admitted'], 'Nontraining pair')
        require(p['chosen']['verifier']['official_reward'] == 1 and p['rejected']['verifier']['official_reward'] == 0, 'Invalid preference labels')
        for side in ['chosen', 'rejected']:
            b = p[side]
            require(b['termination'] == 'assistant_final', 'Censored branch excluded from this pilot')
            require(b['messages'][:len(p['prompt_context'])] == p['prompt_context'], 'Different initial prompt')
            es = b['encoded_turns']
            require(len(es) == b['turn_count'] and sum(e['supervised_tokens'] for e in es) == b['target_tokens'], 'Incomplete branch')
            for e in es:
                require(e['task_uid'] == p['task_uid'], 'Wrong task encoding')
                validate_example(e, cfg['max_context_tokens'])
    return cfg, pairs


def turn_logp(model, example):
    """One forward graph; gather only target rows before float32 log-softmax."""
    import torch
    import torch.nn.functional as F
    device = next(model.parameters()).device
    ids = torch.tensor([example['input_ids']], dtype=torch.long, device=device)
    labels = torch.tensor([example['labels']], dtype=torch.long, device=device)[:, 1:]
    mask = labels != -100
    output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False)
    logits = output.logits[:, :-1, :][mask].float()
    return -F.cross_entropy(logits, labels[mask], reduction='sum')


def branch_score(model, examples):
    import torch
    with torch.no_grad():
        return sum(float(turn_logp(model, e)) for e in examples)


def pair_backward(model, pair, ref, beta, tolerance=.02):
    """Exact chain rule with recomputation; frees each turn graph before next turn.

    All weights must remain unchanged until both branches finish. Dropout must be
    zero. The detached coefficient is the derivative of the original pair loss,
    not a different stop-gradient objective. CPU finite-difference controls test it.
    """
    pc = branch_score(model, pair['chosen']['encoded_turns'])
    pr = branch_score(model, pair['rejected']['encoded_turns'])
    loss, coefficient = scalar_loss_and_coefficient(pc, pr, ref['chosen'], ref['rejected'], beta)
    repeated = {}
    for side, sign, expected in [('chosen', 1., pc), ('rejected', -1., pr)]:
        score = 0.
        for e in pair[side]['encoded_turns']:
            lp = turn_logp(model, e)
            score += float(lp.detach())
            (sign * coefficient * lp).backward()
            del lp
        require(abs(score - expected) <= tolerance, 'Recomputed score differs; stop before update')
        repeated[side] = score
    return {'loss': loss, 'chosen_logp': pc, 'rejected_logp': pr,
        'reference_chosen_logp': ref['chosen'], 'reference_rejected_logp': ref['rejected'],
        'relative_margin': (pc-pr)-(ref['chosen']-ref['rejected']), 'coefficient': coefficient,
        'recomputed': repeated}
