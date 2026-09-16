# Project state

[GPU_WATCH_LAST_CHECK] 2026-09-16T05:50:52.910422+00:00 — A800 and PRO6000 both still have0 available GPUs and remain powered off; authorized8-step SFT probe unexecuted; monitor remains active.

Monitoring update(2026-09-16): user requested ongoing GPU checks. Active current-thread heartbeat `veriagent-gpu-sft-probe`,every15 minutes; existing A800 prioritized, existing PRO6000 also checked. It may continue the already authorized bounded8-step probe when inventory permits, with duplicate-run checks and shutdown afterward. No new rental or expanded phase. Unchanged inventory remains quiet; stop/pause after probe completion or actionable training failure. Creation is verified in the app; no new inventory result or training run is implied. Computer/app and authenticated local browser are required.

## Current: teacher data qualified; authorized SFT probe blocked by GPU inventory (2026-09-16)

TEACHER-ACQUIRE-20260916-001 completed on the new host in no-card mode atccc890d:20 valid,18 official successes,63/63 executable calls,80 API requests,202.121sec,387839 input/9023 output provider tokens,estimatedRMB4.978896. Full Codex quality review approves15 complete trajectories/57 assistant turns; five held/failed(331,1183,980,518,1175). No independent human adjudication. Raw reward/records unchanged.

TEACHER-ADMISSION-CPU-20260916-001 at5fd411b passed16/16 negative controls. The exact probe chooses whole tasks707/965:8 turns,35972 processed/582 supervised tokens,max4741. Remote d429eb6 deployment27-file hash check and validate-only admission passed. New local exact-selection assertions require these same source/task/token identities before a future run. Teacher raw IDs are not passed off as student sampled IDs.

User authorized routine operations, and after an approval interruption explicitly authorized the existing A800 to perform the two-task/eight-step LoRA probe and shutdown. PRO6000 and then A800 both returned0 available GPUs. Neither GPU started; both instances are powered off, no-card session ended, no new rental. SFT-PROBE-20260916-001 remains planned/unexecuted, optimizer updates=0. This is an external inventory blocker, not a remaining quiz, data gate or GPU-start authorization requirement for that A800 probe. Do not re-ask its same authorization; check availability and redeploy latest source when execution resumes. No S1/S2/DPO/RL expansion.

Report: docs/TEACHER_ACQUISITION_REPORT_20260916.md; current handoff: docs/daily/2026-09-16-learning-handoff.md. GitHub data-provenance rejection was resolved with public NVIDIA source hashes/220 email-address matches; a later A800 startup rejection was resolved by explicit user approval, after which actual inventory was checked. Known deployment network failures retained in operational_events.json. No company material/final/BFCL cases used, no secrets saved.

## Latest: ordinary API collector ready; no-card startup and hidden key entry pending (2026-09-16)

User confirmed ordinary pay-as-you-go API access and supplied the Beijing workspace endpoint. Implemented CPU-only Bailian collector, fixed20 preregistration and an explicit four-file GitHub deployment extension. TEACHER-COLLECTOR-CPU-20260916-001 at16a36e9 passed55/55 offline controls using old training707 solely as a replay fixture. No external request, new teacher rollout, quality approval or parameter update. Both instances were again observed off in AutoDL this turn. Remaining handoff: user-authorized no-card startup → GitHub fixed-ref sync and remote preflight → user hidden terminal key entry → bounded acquisition and full-quality review. No autoGPU/SFT. See docs/TEACHER_API_HANDOFF_20260916.md. User-pasted credential was not stored or tested; rotation was recommended.

## Current: teacher preparation passed; ordinary API access pending (2026-09-16)

User resumed progress and named Bailian qwen3.8-max via Token Plan. TEACHER-PREP-20260916-001 at b1f67b34b5fc18dd8e607ade68524332d58c4193 passed CPU checks:20/20 fixed training prompt/tool identities,69/69 visible turns encoded without dropping turns,5/5 negative controls. Existing unapproved trajectories were format fixtures only; training approvals remain0. One canonical target differs from the original sampled IDs, so cross-model formatting is explicitly distinguished from exact generation reconstruction.

Official Token Plan personal/team rules exclude custom batch scripts. Ordinary pay-as-you-go access is needed for the proposed teacher collector; no silent billing switch. No API call, new model rollout, GPU startup or parameter update occurred in this preparation. API collector and teacher-aware trainer admission are not yet end-to-end implemented or validated. Report: docs/TEACHER_PREPARATION_REPORT_20260916.md. Both instances' last confirmed state remains powered off. The earlier stop remains historical; selective-turn supervision is still declined and full-trajectory quality requirements remain active.

## Current stop: full-trajectory SFT quality gate failed (2026-09-16)

User authorized cross-instance copy from old A800 to new PRO6000, then explicitly approved startup and fixed20 acquisition/conditional8-step SFT. Copy and35-file/5-weight rechecks passed; PRO6000 Blackwell BF16 runtime passed. SFT-ACQUIRE-20260916-001 at commit bc5aa55:20/20 valid,3/20 official successes (450,1183,707),88.021sec,3310 output tokens,~RMB0.1707 process estimate. Raw results unchanged.

Full-trajectory quality approvals=0:450 contains an invalid enum before recovery;707 invents an ID before recovery;1183 deletes correct records but its visible scope evidence does not justify limiting all future meetings to December. Codex review, no independent human adjudication. User declined a two-task/five-correct-turn alternative and chose to retain the original objective, stopping at data review. Do not adopt selective targets, add sampling, relax gates or update parameters without new direction. SFT started=false; updates=0.

Both new PRO6000 and old A800 are confirmed powered off; data retained. Report: docs/SFT_ACQUISITION_REPORT_20260916.md. Earlier preparation/startup permissions below are historical, not permission to restart after this stop decision.

Pricing review (2026-09-16): inspected live AutoDL hourly listings in the user's logged-in browser. PRO6000 96GB is the suggested balanced candidate (member/list RMB6.98/7.35 per hour); plain A800 in its dedicated zone is the lowest-hourly-cost checked option (5.59/5.88). Beijing-B A800-NVLink is7.98/8.40; northwest-B H8009.98/10.50. No instance rented, started, migrated or benchmarked; prepared host state was not changed. Price/performance remains an inference pending workload measurements. See docs/GPU_PRICE_CHECK_20260916.md.

## Latest: no-card remote preparation completed (2026-09-10)

GitHub transfer completed: private repo metadata/owner verified; local commit bc5aa55c3b97174822893c789b236cf5e43fcaf3 pushed successfully and the host downloaded 20 approved execution files directly from GitHub at that exact ref. SHA256 and Git blob IDs matched. No dev/final cases or account credential sent; temporary URLs not persisted. Remote bundle_manifest now records GitHub as code transport and that commit, retaining prior deployment manifest. See docs/GITHUB_TRANSFER.md and evidence/sft-remote/github_sync_receipt.json. The original anonymous clone attempt failed for lack of host GitHub authentication and was preserved; fixed-ref authenticated download succeeded without repository visibility/credential-storage changes.

Publication resolved: after the disclosure scope was explained, the user explicitly requested GitHub file transfer. Commit bc5aa55c3b97174822893c789b236cf5e43fcaf3 was successfully pushed to the specified repository. Use GitHub for subsequent code/configuration sync at pinned commits; model weights and credentials stay out of Git. The earlier rejection is preserved as history in evidence/sft-remote/git_publication_status.json, not a current blocker.

User supplied a new personal AutoDL no-card host and waived monetary gating for current SFT progression. All fixed model files (5 shards, 16,381,516,776 bytes) and four tokenizer/config artifacts verified. Independent venv uses Torch 2.8.0+cu128, Transformers4.56.2, PEFT0.17.1; imports passed without initializing CUDA or constructing a model. Training20 actual Transformers prompt/token checks and a scripted training-task tool/reset smoke passed. Final deployed code 4e5f9102aadf01eb35d6f852e496e466442a75d3; evidence in evidence/sft-remote. Details: docs/SFT_NO_CARD_HANDOFF.md.

Remaining external step is user switching the prepared instance to GPU mode; do not ask again for monetary approval or a mandatory price. Then verify one 80GB-class GPU, collect fixed training20, explicitly review quality, and execute the prepared eight-update LoRA integrity probe if its data gates pass. Price/cost remain null when unavailable. No new model trajectories or updates have occurred yet; no automatic S1/S2/DPO/RL expansion. Older price/approval statements below are historical and overridden for this current scope.

## Current experiment progress: SFT data preparation (2026-09-10)

User explicitly requested experiment progress with coarse teaching. CPU experiment SFT-PREP-20260910-001 passed: 75 existing trajectories / 200 generations reconstructed; 200 prompt hashes and exact generated targets matched; fixed prefill stays masked in the input; all 75 dev trajectories rejected from training; 7 negative controls passed. No parameters updated. Fixed 20 training_candidate tasks (4 per domain), all initial prompts 4177–4204 tokens. Acquisition bundle dist/sft-acquisition-537b1876.tar.gz is ready and validated. See docs/SFT_PREPARATION_REPORT.md.

Next execution: user-provided single A800/A100 80GB instance and actual price → fixed B1-candidate training-only collection (20 tasks, seed42, 1800-second process bound, <=RMB30) → explicit success/grounding/target-scope review → eligible data export → first bounded LoRA integrity/cost probe. No new model rollout, approved training corpus or SFT trainer execution yet. Do not ask the learner to complete fine-grained quizzes before progressing. Historical Q0 limitations remain; this preparation does not establish formal B1/composition qualification.

The following learning/Day 3 entries are retained context, superseded where the current execution direction above differs.

Learning correction (2026-09-10): the user reports the material before Day 3 is mostly understood and wants to move into SFT. The earlier context/mask warm-up question is superseded, not a blocker and not graded as passed. Current learning is SFT-A: LoRA structure, forward/backward/optimizer update, parameter-change evidence and save/reload. The new self-contained lesson is docs/learning/05-first-lora-sft.md; code is educational and unexecuted. No parameter update or new GPU execution is inferred from this learning request.

Latest competition steering (2026-09-08): the user targets internship applications from December, is already working on ARC-AGI-3, and prefers waiting for Milestone 2 publication before further focused work. Do not treat BDCI as their selected contest. Official rules require milestone prize candidates to open-source notebooks by the milestone deadline; Milestone 1 winner methods were published in the July 6 official article. Waiting for Milestone 2 open solutions is a plausible interpretation, not a user-confirmed detail. No new experiment authorization.

Competition scouting (2026-09-08): public-source screening is saved in docs/learning/2026-09-08-agent-competition-shortlist.md. CCF BDCI CareerSim is the leading domestic candidate; AWS Agents for Humans is an international application candidate. Final-result dates, entry deadlines, and participant-count units are distinguished. No registration, external message, experiment, training, or research-stage transition occurred.

Learning update (2026-09-08): the user returned after a three-day gap and requested a consolidated learning file. docs/learning/2026-09-08-return-to-project.md integrates lessons 1–4, Day 3 evidence, code walkthroughs and staged assessment. No new model experiments, remote connections or parameter updates. Assessment remains ungraded; start with the new A1–A5. The research state below is unchanged.

Learning delivery preference: the user studies with GPT on a phone at night without opening the laptop. The same learning file now embeds 21 source excerpts with explanations, task 0/task 18 evidence and real token/label rows. Both mechanism and code-tracing questions can be answered from that single document. Source code is distinguished from unexecuted teaching examples; no learner answers have been graded.

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

Delivery Git status: Day 3 evidence, reviewed results and learning materials are committed in 5a5dec8aa8c4980a8ef218e78828918c27183167. Two earlier attempts timed out before process creation; that temporary block is resolved. The user supplied https://github.com/ycInfinite/VeriAgent-Workplace.git as the project remote. GPU-run source identity remains cb4067c; the delivery commit does not represent a rerun.

Hardware/real-tool execution passed for this inference configuration. B0 failed the minimum unique successful state-changing task count (3 versus 4). B1 is a conditional candidate (5 successes/15 failures in one seed); CRM/Project Management state-changing tasks remain all failures. B1 repeatability is not established by a second seed.

Current split remains Q0-SPLIT-20260904-003: training 743; dev 85; checkpoint validation 93; composition reserve UNQUALIFIED 181; quarantined train relatives 153; filtered sealed final 540; quarantined exposed relatives 5. No final/BFCL evaluation. Semantic leakage freedom is not proven.

All Day 3 trajectories and the real preference learning pair are DEV data, not training eligible. A verified no-op can still use bad grounding. B0/B1 system prompts differ and must not silently become a common-prompt preference pair.

Training gate added: canonical role-only targets include four forced non-thinking prefill tokens that were inputs during generation. Align actual trainer labels and per-turn conditioning before SFT/DPO. No CE/LoRA update/save-reload/online RL claims are established.

Next learning: docs/learning/05-first-lora-sft.md, starting with LoRA and the full update sequence. Old A/B/C assessment remains ungraded and does not block the user's requested learning progression. Next engineering decisions remain baseline prompt, weak-domain training-data source, composition protocol and actual trainer alignment; new paid runs/parameter updates still require authorization and the RMB 30 rule.

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
