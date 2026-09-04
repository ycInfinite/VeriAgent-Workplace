# Project state

Updated: 2026-09-04. Stage: CPU preparation/audit completed; learning handoff prepared; waiting for learner answers and a research-scope decision.

GPU rental/model weights/training: NOT AUTHORIZED. No LLM has run. All current trajectories are scripted CPU evidence, excluded from post-training eligibility.

## Completed

- Pinned official sources/data/tokenizer, hashes and local Git history.
- Actual 1255/545 record inventory; exact/lexical overlap screens; conservative exclusion with exposure history.
- 138 scripted environment trajectories on 24 dev tasks: reset/isolation/state/replay checks passed; raw evidence retained.
- 955 training/dev initial prompts tokenized (4112–4153 tokens); actual tool fixture 4536 tokens, 89 supervised. Nine mask checks passed.
- Eight minimal adapter/wire-contract checks passed. Native NeMo HTTP/Ray and Linux GPU stack NOT tested.
- SFT/DPO/GRPO feasibility and cost plans; model qualification card prepared but not executable authorization.
- Beginner learning sequence, read-only CLI, assessment questions/rubric and daily handoff.

## Active evidence

| Experiment | Meaning |
|---|---|
| Q0-DATA-20260904-001 | Official row structure and initial split |
| Q0-ENV-20260904-001 | Tool/verifier scripted properties |
| Q0-TOKENS-20260904-001 | Tokenizer/mask and dev learning fixture |
| Q0-CONTRACT-20260904-001 | HTTP/schema/no-op/lexical overlap diagnostics |
| Q0-SPLIT-20260904-001 | Preserved earlier pilot draft, superseded for model selection |
| Q0-SPLIT-20260904-002 | Preserved domain-balanced pilot, superseded after round-budget screening |
| Q0-SPLIT-20260904-003 | Current candidate pools and dev24; reference actions at most 4 |

Current pools: training 743; dev 85; checkpoint validation 93; composition reserve UNQUALIFIED 181; quarantined train relatives 153; sealed filtered official validation 540; quarantined final relatives of exposed dev examples 5.

## Unpassed gates

1. Strict seen-tool/unseen-composition generalization is not established. Schema visibility and reference action signatures are insufficient. No synthetic tasks generated or semantics changed to force it.
2. Model success/failure regime, training integrity and GPU costs are unknown. Empty-action success means qualification must evaluate state-changing tasks separately.
3. Semantic absence of leakage is not proven; known lexical candidates were conservatively removed. The 540-item filtered final subset must not be reported as the full official benchmark.
4. Learner assessment is awaiting A1–A5 answers; score/pass remain null.

Latest user steering: continue progress; preparing the single-GPU handoff and requesting personal platform/instance pricing details. See docs/GPU_HANDOFF.md and scripts/gpu_preflight.py. This does not authorize paid rental, model downloads or training. Learning and assessment remain pending; no pass is claimed. Composition scope still needs resolution before formal generalization claims.
