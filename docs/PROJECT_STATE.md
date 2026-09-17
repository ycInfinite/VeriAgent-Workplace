# Project state

2026-09-17 currentpreparation operational completion: tofinishuserrequest把sft之前的全部准备好,deploy viaGitHub toexisting904 in CPU/no-card mode andrun SFT-REMOTE-PREP-20260917-001 actualpackage/weight/tokenizer preflight,then shut down. This is necessary pre-SFT deployment,notGPUstartup/parameterupdate/newteacherAPI. CPUrate0.10RMB/h,30minmaximumplanningwindow(~0.05RMB),no newrental/install/modeldownload. The earlier completedteacher12-14window remainsclosed;no modelAPI resumes. GPU/SFT execution stillawaits next userdirection. Newhostvalidator bringsdeploymentto54files;local13-file manifest is retained as earlier preparation snapshot.

2026-09-17 latest request: user asked把sft之前的全部准备好. PREPARATION COMPLETE in SFT-READY-20260917-001: frozen150 whole traces reviewed byCodex only,137approved/13held; allother573 new-source traces not admitted. S1 stratifiedrandom50 andS2failure-targeted50(each10/domain) exported with155fullassistantturns/epoch;2epochs/310updates perarm planned,notexecuted. Processedtoken difference-0.67percent,targettokens+1.99percent;16overlaptasks.20CPUadmission controls and3synthetic comparison checks passed; oldBailian8turn582target export unchanged. Configs/sft_comparison_plan.json and newtrain/eval runners are prepared; GitHub whitelist adds13files but nohostdeployment/startup/modelAPI/GPU/update occurred. Existing8stepadapter preserved; futureS1/S2startfreshbase. Fixeddev24xseeds42/43 preparedforBASE_B1/S1/S2,notrun. New310stepGPUruntime/CE/VRAM/reload and Agent outcome remainunmeasured;strictcomposition/BFCLstillsealed/unqualified. Await userinstruction tostartboundedGPUexperiment; preparation is not startup/training authorization. See docs/SFT_PRETRAINING_READY_20260917.md. Oldmonitors remainpaused;lastobservedinstancesoff.

2026-09-17 noon collection COMPLETE: DEEPSEEK-SFTDATA-20260917-001 at2ca291c ran12:00:00–12:50:28 China,723/723 valid,0infra-invalid,664 official successes(91.84%),2411/2438executable calls,2443 requests/responses. Modeltariff2.12023112RMB,CPUapprox0.28,totalapprox2.40(notinvoice/storageexcluded). All723 tool/observation/state/verifier replays and2443 request/response pairs passed offline integrity. Mechanicalscreen629 unflagged pending semantics,94 flagged; NONE of the723 has full semantic approval/training admission yet.83 empty-reference tasks include80reward1;54 ofthem remain mechanicallyunflagged. Raw archive4,909,385bytes and all11 members verified locally; expandedJSONL local/remote,exactrawarchive tracked onGitHub. All3instances observedoff; bothteacher andoldGPU monitorsPAUSED;14:00 platformtimer cancelledafterearlyshutdown. No duplicate rollout,newGPU,SFT,DPO/RL. Next route: wholetrajectorysemantic quality review,then boundedSFTprotocol; no automatic training. See docs/TEACHER_FULL_POOL_RESULT_20260917.md and experiments/DEEPSEEK-SFTDATA-20260917-001/integrity_summary.json.

2026-09-17 noon collection RUNNING: actual start 2026-09-17T04:00:00.008623+00:00 (12:00:00 China), PID1398/start_ticks1926709082/boot646ab369-44aa-4cde-b48b-2ff7d518caca matches the queued worker. Snapshot 2026-09-17T04:05:25.710978+00:00: 82/723 completed,0 infrastructure-invalid,75 official successes; quality approvals remain0 and these are interim acquisition counts,not SFT results. No duplicate launch/redeployment. Keep14:00 cutoff/shutdown and currentmonitor; localSSHclosed. Evidence:evidence/deepseek/window_monitor/20260917T0405-progress.json.

Today-only723 collection ARMED at2026-09-17 10:29:27 China on904 CPU/no-card. Execution commit2ca291cde64b5c96baec2c9ebeb91e853665ae0a,40 GitHub files verified; PID1398/start_ticks1926709082/boot646ab369-44aa-4cde-b48b-2ff7d518caca survived originalSSH disconnect. Start12:00/stop14:00 China; AutoDL14:00 shutdown visibly verified. OrdinaryDeepSeek secret held only in remote process memory. At10:30:55 zero model calls; this is ARMED,not completed acquisition. Monitorveriagent-9-17 expires today14:00; oldGPU heartbeat staysPAUSED. Do not redeploy execution files while waiting/running,duplicatearm,resample,extend the window or start training. Queue/status evidence:evidence/deepseek/window_schedule_receipt.json and window_queue/. All current localSSH sessions closed. Historical earlier cancelled-noon statements refer only to completed fixed20 qualification and are superseded for this separately authorized723 run.

2026-09-17 scheduled full-training acquisition: user explicitly requested today Beijing12:00-14:00 and then all training tasks. New bounded authorization covers all743 training candidates minus20 already attempted =723,ordinary DeepSeek Flash API,unchanged B1/8192/6rounds/2048 output,no retries,CPU/no-card only. Includes83 empty-reference cases flagged for semantic review. New DEEPSEEK-SFTDATA-20260917-001 is distinct from completed qualification; do not repeat20 or enter SFT/GPU/DPO/RL. Preregistered one-shot remote process and app follow-up are being prepared; do not claim armed until a remote receipt exists. Original old GPU heartbeat remains paused.

DeepSeek qualification complete (2026-09-17): DEEPSEEK-QUAL-20260917-001 at1ded6b7d2b1cd510dd9adf77ea8076e1e16bac83 used unchanged training20/B1 once.20 valid,0infra-invalid,19official successes,60/60executable calls,65requests,88.080s,300129input/7151output,91.99percent input-cache hit. Model fee estimate0.11631784RMB. Codex whole review passes15 trajectories/48assistant turns/4229student targets; holds331/1183/980/518/1175. Existing15 Max demonstrations cover the same15 task IDs; task coverage did not double. New-provider trainer export remains pending, no training. Archive/member hashes verified; all3instances observed off. CPU session≈0.06270RMB,total≈0.17902RMB excluding storage/not invoice. See DEEPSEEK_QUALIFICATION_REPORT_20260917.md. No scheduler; cancelled noon window stays cancelled.

Immediate DeepSeek qualification prepared (2026-09-17): user explicitly cancelled the noon window and authorized the original training20 once now. DEEPSEEK-CPU-20260917-001 passed56 offline controls; all20 initial student contexts fit,max4204. Separate official DeepSeek request builder sends thinking.type=disabled and no unsupported seed; old Bailian request semantics preserved. DEEPSEEK-QUAL-20260917-001 preregistered, not yet executed. Existing904 CPU/no-card deployment next; no scheduler/GPU/training or automatic admission.

GitHub publication recovery (2026-09-17): push of5bc4d15 succeeded and includes the previously unpushed8405b54 demo audit/fixes. This resolves publication only; it does not imply deployment, new model calls or renewed interactive-client work. Current direction is ordinary API teacher qualification advice.

Latest direction (2026-09-17): user returns to ordinary API collection and nominates DeepSeek Flash. Token-Plan-only preference is superseded; stop further interactive-client work. Official Chinese pricing checked today: deepseek-flash currently maps to V4.1-Flash; off-peak RMB1/cache-miss input,0.02/cache-hit input,4/output per million,peak2x. Same historical20-attempt token volume projectsRMB0.424-0.848 without cache; quality unknown. No DeepSeek calls/credentials/configured transport or new GPU/training. See DEEPSEEK_FLASH_ASSESSMENT_20260917.md.

Interrupted-turn closure recovered: on2026-09-16 the AutoDL UI was refreshed after17:15 and all3 instances were observed off. Raw interactive-demo archive was verified and saved locally. Local commit8405b54 includes review and v2 fixes; four GitHub push attempts failed TLS handshake, so its publication and remote deployment were not confirmed then. Last verified remote execution remains318e233; old GPU monitor stays paused. Do not restart the outdated interactive route.

Interactive demo reviewed (2026-09-16): user initiated training707 in the prepared official client;3 real world actions,grounded ID,only status changed,official reward1,replay agrees. Post-hoc audit INTERACTIVE-DEMO-20260916-001 holds SFT admission: --bare ignored settings,actual context1M,max input9805,thinking255;6 main responses versus7 aggregate requests. Source success remains intact; not controlled B1. Fixed v2 profile/settings isolation and compact MCP return passed official pure config resolver and18 CPU004 checks; no corrected model rollout or training. Raw archive/member hashes preserved. See INTERACTIVE_DEMO_REVIEW_20260916.md.

Interactive handoff ready (2026-09-16): fixed318e233 deployed via GitHub with32 verified files; official Qwen Code0.23.4/Node24.19.0/MCP1.30.0 installed on904 CPU/no-card. Actual Edge JupyterLab terminal now shows qwen3.8-max and workplace connected; left for the user to initiate a task. No model prompt submitted, rollout produced, SFT data admitted or parameter updated. Native SSH acceptance session exited with0 tool calls/API time0; credentials remain ephemeral. AutoDL UI confirms shutdown2026-09-16 17:15 Asia/Shanghai,rate0.10RMB/h,total-to-timer estimate≈0.11(not invoice/completed shutdown). Old GPU monitor paused. See INTERACTIVE_CLIENT_READY_20260916.md for logs, limitations and failed-run preservation.

Interactive implementation (2026-09-16): official Qwen Code0.23.4 installed locally in ignored cache with existing Node24.19.0; isolated MCP1.30.0 installed without changing training dependencies. New single-training-task bridge supports get_task/real action/terminal verify, never calls a provider and keeps training_eligible=false. CPU audit003 passed18 controls; audit001 missing local training20 file and audit002 argument-serialization mismatch remain infrastructure-invalid, with original evidence retained. Existing904 was started in CPU/no-card mode at0.10RMB/h and SSH verified; remote GitHub deployment/client installation are next. No provider request, GPU, new model rollout or training.

Token Plan resolution preparation (2026-09-16): checked the personal overview, which explicitly permits interactive tool/extension usage and says personal subscriptions currently cannot be unsubscribed. Prepared a secret-free Qwen Code provider example and TOKEN_PLAN_INTERACTIVE_HANDOFF_20260916.md with concrete code-study tasks and an unsent support question. This is a supported interactive-development alternative, not headless/batch collection through a client wrapper. No client installed/configured, MCP bridge implemented, API called, new trajectory admitted or GPU started. Account/refund eligibility and end-to-end integration remain unverified; no pay-as-you-go fallback.

Latest teacher-channel request(2026-09-16): user insists on Token Plan. Future teacher collection has no automatic pay-as-you-go fallback. Rechecked official personal/team rules: custom automated scripts are excluded. No Token Plan collector was enabled or called; no guard removed, client spoofed, key requested or machine started. Await an allowed service usage path before more teacher sampling. The completed SFT probe and all original evidence remain unchanged.

Official-data clarification(2026-09-16): pinnedtrain1255 rows were rechecked:input roles are system+user,ground_truth is a reference action list,not complete assistant/tool interactions. Official full demonstrations or causally grounded reference reconstructions can be valid SFT sources; the current probe producer allowlist is not a universal model-generated-data requirement. Recommend auditing reuse/reconstruction before assuming all future samples need paidteacher. No new source admitted,run,parameter update or stage transition. SeeOFFICIAL_REFERENCE_VS_TRAJECTORY.md.

Teacher-cost advice(2026-09-16): recommend ordinaryAPI for the next bounded collection; current undiscounted estimate≈RMB0.332 per quality-approved trajectory. Existing responses show89.37percent input-token cache hits, but model-specific cache price and invoice remain unverified. Open-teacher self-hosting requires separate quality and all-in cost qualification. SeeTEACHER_COST_COMPARISON_20260916.md. This was advice only; no new run, machine startup or stage transition.

## Current: first real8-update LoRA probe passed; checkpoint verified and all instances off (2026-09-16)

SFT-PROBE-20260916-001 executed on the user-authorized replacement904 PRO6000 single GPU atcommit0a7eba87b1d2fe04320ee67803951e4af6169295. All8 updates completed on whole tasks707/965(8 turns,35972 processed/582 supervised tokens). Trainable parameters43646976; first manual/model CE difference0; all gradients finite,504 adapter tensors changed; frozen parameter samples unchanged. Adapter reload logits max difference0 and greedy IDs identical. Training validity gate passed; no infrastructure-invalid training run.

Mean step1.4883sec,8 updates11.9063sec,full probe33.4939sec,allocated peak26.5315GiB,reserved peak58.0918GiB,sampled GPU used peak60175MiB,30-sample utilization mean47.7percent. Process GPU-hours0.00930387,estimatedRMB0.064941 at6.98/h; this is included in total instance uptime and not additive. Model revisions/package identities and raw records are preserved. Report:docs/SFT_FIRST_PROBE_REPORT_20260916.md.

This proves parameter-update and save/reload integrity, not Agent improvement. The one trained-policy fixed-input greedy readout still invents customer_id12345678 without lookup; no tool execution/task verifier or matched pretraining greedy baseline was run for that readout. No fullS1/S2,DPO or RL. Teacher acquisition was not repeated. Monitor remains PAUSED. All3 adapter files(174661796bytes) passed local/remoteSHA256 comparison underignoredcheckpoints/. New904 and both old instances are confirmed powered off, data retained. Full instance session estimatedRMB4.58-5.04 to the shutdown request (not invoice; small completion lag possible); processRMB0.064941 is included, not additive. Receipts:evidence/sft-probe/adapter_backup_receipt.json and lifecycle_and_cost.json. Stop here pending the next research-stage decision.

## Latest: user-authorized replacement cloned and running; SSH endpoint handoff pending (2026-09-16)

User said "直接重新找一个空闲的吧，懒得等了", superseding the earlier existing-instance-only restriction for one replacement single GPU. Paused the old inventory heartbeat to avoid duplicate starts. Selected available BeijingB904 PRO6000 96GB atRMB6.98/h (single GPU,22CPU,110GB RAM,driver590.44.01), cloned system+data disk from the prepared PRO6000. New instance kl7wef5luq-6927b33c is running; platform data-copy indicator cleared and disk usage matches source31.03percent; old source and A800 remain off/preserved. No paid disk expansion, no new model data collection or parameter update.

Browser clipboard reads returned empty after copying the SSH command. Requested only the new host/port from user; no password/API key requested. Once accessible: verify copied artifacts/runtime, GitHub sync current fixed commit, duplicate-run check and remote validate-only, then execute the same2-whole-trajectory8-update probe and shut down. No research-scope expansion. Record: evidence/migration/2026-09-16/replacement_clone.json. Older zero-stock monitoring entries below are historical; monitoring is paused for this manual continuation.

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
