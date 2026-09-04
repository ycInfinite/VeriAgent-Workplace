# Project state

## Current: Day 3 completed (2026-09-04)

All model jobs finished; 75 real-model trajectories were downloaded and hash-verified. AutoDL shutdown command succeeded and SSH was closed by the remote host. No parameter updates; no automatic next stage.

- Model: Qwen/Qwen3-8B b968826d9c46dd6066d109eabc6255188de91218; official Gym core 83b3980b9c04379d72bbf59592d7846630f706bf.
- GPU-run code commit: cb4067c3e0dd21723d5664e7ccd27cdd3120c51e. Later changes are offline analysis/metadata improvements, not reruns.
- Q0-SMOKE-20260904-001: 3 valid rollouts, 1 success.
- Q0-B0-20260904-001: 48/48 valid, 11/48 success; state-changing stratum 5/40; seeds 42/43.
- Q0-B1-20260904-001: 24/24 valid, 8/24 success; state-changing stratum 5/20; seed 42.
- Paired B1 vs B0 seed 42: 8/24 vs 5/24, three improvements (0,1,18), no regressions. All gains are recoveries after an initial error.
- All 75 have online/replay agreement; weight hashes and unchanged parameter samples verified; trainable parameter count=0.
- Allocated peak 17.17 GiB; sampled GPU used peak 19.80 GiB. Managed-session cost estimate ~RMB 1.73 at user-confirmed RMB 1.98/hour; model-run part ~RMB 0.31, included in that total.

Authoritative report: docs/DAY3_REPORT.md. Semantic labels: reports/day3-reviewed-v2 (Codex review, not independently human-adjudicated). Caveats: evidence/day3/metadata_notes.json. Raw results unchanged.

Delivery Git status: final staging/commit attempts timed out twice in automatic permission review before process creation. The new evidence/reports are saved in the working directory but not committed. GPU-run source commit remains correctly recorded; do not claim a final delivery commit exists.

Hardware/real-tool execution passed for this inference configuration. B0 failed the minimum unique successful state-changing task count (3 versus 4). B1 is a conditional candidate (5 successes/15 failures in one seed); CRM/Project Management state-changing tasks remain all failures. B1 repeatability is not established by a second seed.

Current split remains Q0-SPLIT-20260904-003: training 743; dev 85; checkpoint validation 93; composition reserve UNQUALIFIED 181; quarantined train relatives 153; filtered sealed final 540; quarantined exposed relatives 5. No final/BFCL evaluation. Semantic leakage freedom is not proven.

All Day 3 trajectories and the real preference learning pair are DEV data, not training eligible. A verified no-op can still use bad grounding. B0/B1 system prompts differ and must not silently become a common-prompt preference pair.

Training gate added: canonical role-only targets include four forced non-thinking prefill tokens that were inputs during generation. Align actual trainer labels and per-turn conditioning before SFT/DPO. No CE/LoRA update/save-reload/online RL claims are established.

Next: read docs/learning/04-day3-real-trajectories.md and submit its five answers (assessment still pending, score/pass null), then decide baseline prompt, weak-domain training-data source and composition protocol. New runs/training require a new instruction and the RMB 30 rule.

## Historical CPU/preflight snapshot (superseded by the current state above)

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

Latest user steering: Day 3 remains inference-only and provider is AutoDL, with no-card mode available for uploads. Recommend RTX 4090 24GB at concurrency 1 for this bounded probe; the earlier 80GB recommendation was oriented toward later training. No-card mode limits and cost verified from official docs. Actual price, instance, image and access are still missing. See docs/GPU_HANDOFF.md and scripts/gpu_preflight.py. No remote paid action/model download has occurred. Learning and assessment remain pending; no pass is claimed. Composition scope still needs resolution before formal generalization claims.
