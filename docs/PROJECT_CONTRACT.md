# 项目约定

2026-10-12 DPO PREPARATION authorized by user, COMPLETE LOCALLY (no GPU execution). DPO-PREP-20261012-001 freshly reviews13 historical training pairs and replays26 branches:12 data-admitted,271held for round-censored rejected trajectory (valid policy failure,notinfra-invalid). 38chosen/37rejected assistantturns,3258/1885targets,336711processed,max5431;wholeassistant masks and originalobservations retained. DPO-CONTROLS-20261012-003 passes25 CPU gates;localTorch absent,realautograd/HF-host/8Bscore/VRAM/update/reload untested. New bounded8-update probe uses exactS1 forpolicyandfrozenreference,beta.1,lr5e-6,8192,one96GBGPU;precomputedreference andper-turn recomputation,notonlineRL. Chosen-onlySFT matchedcontrol is a future design,notexecutedfullmatrix. Seven-fileGitHubwhitelist prepared,no deployment/startup/API/modelupdates;oldmonitorspaused. Do not assume this preparation authorizesGPUtraining/newrental/currentpolicyrollouts orDPOformalstage. See docs/DPO_PREPARATION_20261012.md and docs/daily/2026-10-12-dpo-learning-handoff.md. Earlier DPO-deferred entries are superseded only for this preparation scope.

2026-10-12 S100/MIX100 COMPLETE on user-provided clone PRO6000 96GB, execution64d6610. Each310 real updates;504LoRA tensors changed;frozen samples unchanged;reload logit diff0. Eachdev24x42/43:48valid/0infra-invalid. S100 official32/48(nonempty27/40,empty5/8);MIX40/48(32/40,8/8). MIX-S100 overall+16.67pp CI[0,33.33],nonempty+12.5pp[-5,27.5],empty+37.5pp[0,75];only4empty taskclusters. Fresh empty semantic audit:both4/8 supported completed no-change and2/8 whole-clean;MIX8/8 official includes wrong dates/window/arithmetic,not reliable reasoning proof. S100 versus historicalS1 no improvement demonstrated;host/driver595.58.03 vs580.142 confound. ScriptGPUh0.638604;container-startestimate toshutdown1.015973h;hourlypriceunknown,RMBnull. Actualdeviceusedpeaks88.896/91.685GiB,80GBfitnotproven. Bothadapters/rawarchives locallySHAverified;officialshutdownissued,SSHunavailable,consolebillingnotindependentlyverified;newguardcancelled,oldmonitorspaused. PreserveOct10registered IDs(actualOct12timestamps),no rerun/newteacher/DPO/RL/automaticnextstage. See docs/SFT_EXTENSIONS_20261012.md and docs/daily/2026-10-12-learning-handoff.md. Earlier pending entries are historical.

2026-10-12 用户提供新克隆实例connect.westd.seetacloud.com:38654并要求继续；允许在该自有单卡执行已冻结S100→MIX100，不自动租其他实例或进入DPO/RL。已核验主机autodl-container-afzl2bg1l8-cc9c6860，PRO6000Blackwell96GB，旧缓存和依赖齐全，9模型/Tokenizer哈希匹配。驱动595.58.03不同于历史S1的580.142，S100对旧S1有额外主机/驱动混杂；S100与MIX100同新机比较。固定部署commit64d6610，GitHub临时URL发生两次404，保留传输故障并有界重试；尚未启动模型运行。复用未使用的Oct10预登记runIDs，实际时间记录Oct12。新4h资源保护已启用、旧监控不恢复；时价未知，计入部署/等待占用。见experiments/SFT-EXTENSION-RESUME-20261012-001/config.json。

2026-10-10 空reference审核与MIX100准备完成：用户要求审核原83条training候选、准备合格不修改数据与混合100对照，原S100不变、等GPU再跑。NOOP-REVIEW-20261010-001全部83有处置：29通过/54暂缓；58完整可见语义复核，25在结构/调用错误门槛暂缓，不声称全语义审核。29条共86assistant样本/423984processed/10560target，原响应/观察/完整mask/8K准入通过，无新API/采样。MIX100固定80原S100+20合格no-op、五域各20题、1epoch310updates；processed1450298(+1.3869%)、target28695(+1.3707%)、max7756，context仍8192。MIX100-PREP-20261010-001的16项CPU控制及10文件部署白名单通过；实际HF/GPU/CE/梯度/显存/重载/Agent效果未测。只新建configs/sft_mixed100_plan.json和独立入口，原S100三项hash不变、核心代码未改。未来先完成S100再MIX100；不重跑旧S1/S2、不自动租卡/开机/库存监控或DPO/RL。资料见docs/NOOP_MIX100_READY_20261010.md；本轮GPU/API/updates均0。

2026-10-10 下一阶段：用户明确选择“先做100条SFT规模检查”，随后报告GPU无空位，要求提前完成其他准备。S100本地准备已完成，等待资源；不自动租卡、开机或创建库存监控。执行计划固定为同Base全新LoRA、原S1的50条加50条已审任务、1epoch/310updates，processed1,430,459（对S1+0.3521%）、target28,307（−0.8372%）、max7208。dev24×42/43不变。DPO暂缓，13个历史training偏好对仅CPU候选，未训练。POSTSFT-AUDIT-20261010-001完成库存/28条官方失败归因/候选检查；SFT-SCALE-PREP-20261010-001因CRLF身份检查停止，永久保留，002重编码和13项CPU控制通过。只使用configs/sft_scale_plan_v2.json，旧v1不部署。新增7文件GitHub白名单已准备；尚未远端部署、实际Tokenizer/GPU预检、CE/梯度/重载或Agent评测。下一次资源可用时按已选S100范围执行，不重跑已完成S1/S2，不扩大数据/context或进入DPO/RL。See docs/SFT_SCALE100_READY_20261010.md。

2026-10-10 SFT comparison COMPLETE on user-provided single PRO6000 96GB. SFT-S1/S2-20261010-001 each310updates,504changedLoRAtensors,frozenparametersamplesunchanged,save/reloadlogitdifference0;bothadapterslocallySHAverified. BASE/S1/S2dev24xseeds42/43 completed144valid/0infra-invalid;officialsuccess15/48,35/48,33/48;nonempty9/40,30/40,31/40. PrimaryS2-S1 +2.5pp,task-cluster95%CI[-20,+25]pp:targeted-superiority NOTestablished. ScriptGPUhours0.71064;container-startestimate-to-shutdownrequest2.39992h,priceunknown. Officialshutdownissued,existingSSHclosed and newconnectionrefused;platformbillingstatusnotindependentlyverified. NoactiveSSH/watchdog;oldmonitorsstaypaused. Preservefrozenexecutionf9d45c2 andallfiveIDs;do notrerun orautoenterDPO/RL/teachercollection. Fullsemanticratespending;freshillustrativecaseauditstored,nooldlabelsreused. Sealedfinal/BFCL/compositionstillunmeasured. See docs/SFT_EXECUTION_20261010.md and docs/daily/2026-10-10-learning-handoff.md.

2026-10-10 user supplied newly rentedpersonalinstance connect.westd.seetacloud.com:46158 for authorizedS1/S2stage. This supersedes existing904-only assumption for thisuser-providedreplacement;do notrentadditionalinstances. SSHpinned,hostnameautodl-container-y4c4dlvw4m-1184c432,onePRO6000Blackwell96GB/driver580.142/torch2.8.0+cu128;empty50GiBdatadisk. Restored81verifiedfilesviaGitHub6.4MBarchive atfad11e1,execution source stillf9d45c2. Newroot/root/autodl-tmp/veriagent-workplace-sft-20261010; isolatedvenv reusesimageTorch andinstallsfixedotherpackages. Sameb968826Qwen3-8B weightsrestoring,no newteacherdata/modelpolicycalls/parameterupdatesyet. GPUinstanceisalreadyallocatedbyuser;setup/waitingcostmustbeincluded,rateunknownnotzero. Keepfrozen50tasks/310updates anddev24seeds42/43;newrunIDs20261010;stoponformalrunfailure. BrowserunavailabledoesnotblockauthorizedSSHwork. Credentialsremainnon-echoing/notinfiles. Seeexperiments/SFT-RECOVERY-20261010-001/.

2026-10-10 latest userdirection进行下一阶段 authorizes the already-frozen bounded S1/S2 training and matcheddevelopment evaluation onone existingqualifiedGPU; earlierwaitfortrainingdirection issatisfied for thisscope. No newrental/model/context/tasks/seeds/sweeps/teacherAPI/DPO/RL inferred. SFT-RESUME-20261010-001 passed freshlocalS1/S2whole-dataadmission andBASE_B1evalinput checks. Plan/code/data remainfrozen,executioncommitf9d45c2. NewplannedIDs use20261010 (BASEeval,S1train/eval,S2train/eval); none started. Currentbrowser connectionfailed3times; userchose restoreAutoDLbrowser butretry stillfailed. Cannotassume SeptemberinstancesoroldSSHportsremainowned/available. NoGPUstartup,remoteauth,modelcall orparameterupdate thisturn;botholdmonitorsremainpaused. Resume actualinventory/assets checks when browser/accessreturns,thenexecute boundedmatrix sequentially andpreserve/shutdown;no repeatconfirmation solely for existing authorized training or budgetthreshold.

2026-09-17 FINAL pre-SFT readiness: userrequestedallpreparation is complete locally AND onexisting904 CPU/no-card host. SFT-REMOTE-PREP-20260917-001 passed atf9d45c282b7cbebeedb1063e3c2c705330e0b23c:54GitHub-syncedfiles/69totaldeploymenthashes,9weight+tokenizerfiles,exacttorch2.8.0+cu128/Transformers4.56.2/PEFT0.17.1/Accelerate1.10.1;actualTransformerstemplate/inputIDs/targets match155samples ineacharm. NoLLMconstruction/CUDAinit/modelAPI/update. Both50task/310plannedupdatearms remainNOTTRAINED. Receiptsdownloadedand3SHA256verified;904andothertwoinstancesoffobserved;1455backuptimerremoved;SSHclosed;monitorspaused. AddedCPUpreparationcostapprox0.03RMB,notinvoice. Preparedexecutioncommitf9d45c2 isalreadyonhost; do notrerun immutableCPUpreflight001 orold8stepprobe. Nextrequiresuserinstructiontoexecute boundedGPUtraining/eval;noautomaticnewstage. LocalSFT-READY result isearlierCPU-onlysnapshot;thisentryrecords subsequentactualdeployment/preflight. See docs/SFT_PRETRAINING_READY_20260917.md.

2026-09-17 currentpreparation operational completion: tofinishuserrequest把sft之前的全部准备好,deploy viaGitHub toexisting904 in CPU/no-card mode andrun SFT-REMOTE-PREP-20260917-001 actualpackage/weight/tokenizer preflight,then shut down. This is necessary pre-SFT deployment,notGPUstartup/parameterupdate/newteacherAPI. CPUrate0.10RMB/h,30minmaximumplanningwindow(~0.05RMB),no newrental/install/modeldownload. The earlier completedteacher12-14window remainsclosed;no modelAPI resumes. GPU/SFT execution stillawaits next userdirection. Newhostvalidator bringsdeploymentto54files;local13-file manifest is retained as earlier preparation snapshot.

2026-09-17 latest request: user asked把sft之前的全部准备好. PREPARATION COMPLETE in SFT-READY-20260917-001: frozen150 whole traces reviewed byCodex only,137approved/13held; allother573 new-source traces not admitted. S1 stratifiedrandom50 andS2failure-targeted50(each10/domain) exported with155fullassistantturns/epoch;2epochs/310updates perarm planned,notexecuted. Processedtoken difference-0.67percent,targettokens+1.99percent;16overlaptasks.20CPUadmission controls and3synthetic comparison checks passed; oldBailian8turn582target export unchanged. Configs/sft_comparison_plan.json and newtrain/eval runners are prepared; GitHub whitelist adds13files but nohostdeployment/startup/modelAPI/GPU/update occurred. Existing8stepadapter preserved; futureS1/S2startfreshbase. Fixeddev24xseeds42/43 preparedforBASE_B1/S1/S2,notrun. New310stepGPUruntime/CE/VRAM/reload and Agent outcome remainunmeasured;strictcomposition/BFCLstillsealed/unqualified. Await userinstruction tostartboundedGPUexperiment; preparation is not startup/training authorization. See docs/SFT_PRETRAINING_READY_20260917.md. Oldmonitors remainpaused;lastobservedinstancesoff.

2026-09-17 noon collection COMPLETE: DEEPSEEK-SFTDATA-20260917-001 at2ca291c ran12:00:00–12:50:28 China,723/723 valid,0infra-invalid,664 official successes(91.84%),2411/2438executable calls,2443 requests/responses. Modeltariff2.12023112RMB,CPUapprox0.28,totalapprox2.40(notinvoice/storageexcluded). All723 tool/observation/state/verifier replays and2443 request/response pairs passed offline integrity. Mechanicalscreen629 unflagged pending semantics,94 flagged; NONE of the723 has full semantic approval/training admission yet.83 empty-reference tasks include80reward1;54 ofthem remain mechanicallyunflagged. Raw archive4,909,385bytes and all11 members verified locally; expandedJSONL local/remote,exactrawarchive tracked onGitHub. All3instances observedoff; bothteacher andoldGPU monitorsPAUSED;14:00 platformtimer cancelledafterearlyshutdown. No duplicate rollout,newGPU,SFT,DPO/RL. Next route: wholetrajectorysemantic quality review,then boundedSFTprotocol; no automatic training. See docs/TEACHER_FULL_POOL_RESULT_20260917.md and experiments/DEEPSEEK-SFTDATA-20260917-001/integrity_summary.json.

Today-only723 collection ARMED at2026-09-17 10:29:27 China on904 CPU/no-card. Execution commit2ca291cde64b5c96baec2c9ebeb91e853665ae0a,40 GitHub files verified; PID1398/start_ticks1926709082/boot646ab369-44aa-4cde-b48b-2ff7d518caca survived originalSSH disconnect. Start12:00/stop14:00 China; AutoDL14:00 shutdown visibly verified. OrdinaryDeepSeek secret held only in remote process memory. At10:30:55 zero model calls; this is ARMED,not completed acquisition. Monitorveriagent-9-17 expires today14:00; oldGPU heartbeat staysPAUSED. Do not redeploy execution files while waiting/running,duplicatearm,resample,extend the window or start training. Queue/status evidence:evidence/deepseek/window_schedule_receipt.json and window_queue/. All current localSSH sessions closed. Historical earlier cancelled-noon statements refer only to completed fixed20 qualification and are superseded for this separately authorized723 run.

2026-09-17 scheduled full-training acquisition: user explicitly requested today Beijing12:00-14:00 and then all training tasks. New bounded authorization covers all743 training candidates minus20 already attempted =723,ordinary DeepSeek Flash API,unchanged B1/8192/6rounds/2048 output,no retries,CPU/no-card only. Includes83 empty-reference cases flagged for semantic review. New DEEPSEEK-SFTDATA-20260917-001 is distinct from completed qualification; do not repeat20 or enter SFT/GPU/DPO/RL. Preregistered one-shot remote process and app follow-up are being prepared; do not claim armed until a remote receipt exists. Original old GPU heartbeat remains paused.

用户目标：真正掌握 trajectory → eval/failure analysis → post-training data → SFT/LoRA → DPO → 可选 online RL → generalization/cost 的完整机制。核心对照为相同训练预算的 random verified SFT 与 failure-targeted SFT。RL 不是项目成立条件。

## 当前授权

2026-09-17 即时资格测试授权：用户指定原20道training任务并提供普通DeepSeek访问，最终明确“不用保留时间窗口”。取消早先12–14点限制，立即按DEEPSEEK-QUAL-20260917-001单次原20题执行。允许必要的既有904无卡启动、GitHub固定提交部署、API采集、证据审核和关机；不另外增加smoke题、不GPU/训练/重采样。Key只经隐藏输入进入远端环境。未创建定时任务。

2026-09-17 最新方向：用户明确放弃Token Plan路线，改回普通API，并提出DeepSeek Flash作为候选、询问性价比。这覆盖下文旧的“只用Token Plan、不回普通API”偏好。本轮仅作官方价格/能力核验和成本建议；报价假设DeepSeek官方API，实际平台与凭据未配置，不复用任何阿里云Key，不自动执行新采集/GPU/训练。停止继续搭建交互客户端，保留旧证据和15条合格教师轨迹。

2026-09-16 渠道要求：用户明确要求后续rollout使用Token Plan，不再把普通按量API作为默认后备。官方more-tools/Token Plan FAQ仍排除个人版和团队版的自定义自动化脚本用途；当前没有据此启动批量采集、移除端点保护或伪装客户端。不自动切换扣费渠道，不请求新的Key；待有服务允许的使用方式再接入。原8步SFT完成事实与历史费用不改写。

2026-09-16 原8步probe授权已执行完成：替代904 PRO6000上的SFT-PROBE-20260916-001通过，进入证据/adapter保全与关机收尾。后续新数据规模、正式SFT对照/Agent评测、DPO/RL仍需路线登记，不将本次完成授权无限延伸。旧库存监控保持暂停，防止重复训练。

2026-09-16 替代实例授权：多次库存均为0后，用户明确“直接重新找一个空闲的吧，懒得等了”。据此寻找并使用一台有库存的80GB/96GB级单卡AutoDL替代实例，允许必要的按量租用/克隆或项目迁移，覆盖此前仅限两个既有实例及不新租/不克隆限制。保持旧机数据并关机；仍是原固定学生、两条完整轨迹、8步LoRA probe，完成保全证据后关机，不扩大实验。旧库存heartbeat在人工执行此路线时暂停防重复。

2026-09-16 监控授权：用户要求“你随时监控一下”。已建立当前对话每15分钟heartbeat，检查两个既有实例库存；按既有明确授权继续固定8步probe，不新租、不重复采集/训练。无变化安静，有库存并开始执行、完成、出现新故障或需要人工操作时通知；完成/需路线决定的训练失败后暂停监控。保持电脑与本地应用运行、AutoDL浏览器登录；不能保证离线时监控。

2026-09-16 A800明确授权：PRO6000库存不足后，自动审批拦截A800启动入口；用户随后对“已有A800单卡、2条完整轨迹、8步LoRA、完成后关机”的具体问题回复“允许已有 A800 执行 8 步 probe”。据此继续该既有实例上的单卡probe，覆盖历史的GPU开机/更新等待；不租新机、不扩大矩阵。

2026-09-16 常规操作覆盖：针对“新PRO6000无卡开机并继续部署采集”的具体询问，用户回复“继续，以后不用管即可”。本轮既定SFT推进内的开关机、部署、采集等常规步骤不再重复确认；不推定新增租赁、多卡、换大模型、扩大context/任务、改监督目标或自动进入DPO/RL。凭据继续隐藏输入，仅临时进程使用，不落盘或回显。此条覆盖下文历史的开机等待，但保留实验质量和阶段门槛。

2026-09-16 普通API确认：用户回复已有普通按量Key，并提供北京工作空间Base URL。允许在固定20题教师路线准备该端点；Key不写入文件/Git/日志，聊天所贴Key建议撤销换新，通过远端终端隐藏输入。两台实例本轮重新确认均关机，仍不自动开机；下一执行步骤需要无卡实例可用。代码和CPU检查已完成，不把这些当教师成绩或SFT资格。

2026-09-16 API补充：用户指定百炼 qwen3.8-max，现有渠道为 Token Plan。已核验官方个人版/团队版规则均排除自定义自动化脚本；固定20题采集需要适用的普通按量API，不能暗中改扣费渠道。平台/模型已知，适用凭据和远端进程接入尚未落实。CPU准备已完成；没有付费API请求、新rollout或参数更新。下条“平台/模型待提供”仅描述较早状态。

2026-09-16 继续指示：用户随后要求“进行下一步”，并确认有个人公网API。恢复完整高质量轨迹的数据来源准备，保留整条监督门槛和固定20题/B1；不采用之前未获同意的正确片段方案。具体API平台和模型ID仍待用户提供，Key不得进入聊天/文件/Git。当前只做CPU请求隔离与学生格式审计，不据此开机、调用未确认API或更新参数。

2026-09-16 当前停点：固定20条采集后，整条轨迹质量门槛未通过。用户明确“保持原方案，先停在数据审核”，未采纳正确片段监督提案。停止在此，不自动追加采样、放宽审核、改变mask或执行更新；新旧实例均已关机，数据保留。此前条件probe授权不覆盖停止后的自动重启。

2026-09-16 迁移与开机：用户明确要求通过AutoDL“更多→跨实例拷贝”将旧A800项目迁至新PRO6000实例；拷贝完成后又明确回复“允许开启并继续”，授权开启新单卡并执行固定20条采集→质量审核→通过后8步LoRA probe。此为明确开机授权，不是自动租新实例或扩大实验；旧A800数据保留，旧机保持关机。新机开机确认框显示6.98元/小时。

2026-09-10 文件传输：在明确说明待发布代码、学习文档与公开环境实验准备记录的范围后，用户回复“记得用github传文件”。据此使用指定 ycInfinite/VeriAgent-Workplace 私有仓库推送并在远端拉取固定 commit 文件；不再对同一已说明范围重复确认。密码、模型权重和缓存不入 Git；训练主机只下载执行白名单，保持 dev/final 隔离。私有仓库匿名 clone 不可用时，用现有本地 Git 登录向 GitHub 取得临时只读文件链接，远端直接从 GitHub 下载并校验；不传账号凭据，不保存临时链接，不自动修改仓库可见性。

2026-09-10 最新预算覆盖：用户提供新的个人 AutoDL SSH 无卡实例并要求继续，随后明确“无需顾虑预算，继续使用”。当前 SFT 推进不再以 RMB30 或未知报价作为等待确认的门槛；保留单卡/固定模型/上下文/rollout/阶段范围，实际资源仍记录，未知单价与费用写 null/不可用而非 0。无卡模式下完成上传、依赖、固定权重下载和检查，不在无卡模式加载 8B 或擅自调用未核实的实例切换接口。下方较早金额条款在本轮被此授权覆盖。

2026-09-10 最新指示：用户要求直接推进实验进度，教学保持粗颗粒。开始 SFT 的数据、编码与训练入口准备，将首次小规模训练 probe 做到可执行、可审查；不再以旧学习题/考核阻挡工程。GPU 尚未准备，用户询问选型；建议单张 A800/A100 80GB，先无卡准备。执行前仍需实际实例、报价、合格 training 数据、完整性检查和登记配置；不自动租卡/开机，不自动扩大为正式 S1/S2、DPO 或 RL。单次预计超过 RMB 30 的确认线不变。

2026-09-04：完成租 GPU 前全部可做工作；结束后提供适合学习一个月的新手的学习材料，并考核。允许小型官方源码、任务数据、CPU 依赖和 tokenizer 准备；不租 GPU、不下载大模型、不使用付费模型 API、不做训练、不自动进入后续阶段。

后续授权：用户提供个人 AutoDL SSH 访问并明确要求完成 Day 3 全流程，允许在该实例准备环境、下载固定模型、执行 smoke、48 条 B0 与满足预登记条件时的 24 条 B1。继续保留单次预计超过 RMB 30 的审批线；不做 SFT/DPO/RL 参数更新，不扩大模型/卡数/context/seed。凭据不进入项目、Git、日志或聊天回显。

## 固定边界

- 单卡上限 1×A800 80GB；候选约 8B，LoRA/QLoRA，有限 context。
- 总预算约 RMB 1000–2000；单次预计超过 RMB 30 必须明确获批。
- 保留旧 tau2 项目为 Hard-environment Base Qualification Audit，不操作旧目录。
- 只使用公开个人项目资料。公司数据、源码、技能、Prompt、API、测试及内部结论禁止混入。
- API key 只允许远端进程环境，不写文件/Git/日志/聊天。
- BFCL final cases 不用于任何训练、prompt 调试、taxonomy、pair、RL 或 checkpoint selection。
- 所有模型行为结论必须来自真实模型 rollout。脚本回放只证明工具/verifier 性质。
- 在线 RL 必须证明当前权重 rollout → reward → update → 新权重 rollout；离线轨迹不冒充 online。

## 训练与评价

- SFT 的 system/user/tool/environment 内容默认 labels=-100；assistant tool calls/response 是监督目标。
- DPO pair 共享任务与初始条件，各自工具 observation 仅作为 context；检查 policy-token log-prob mask 和冻结 reference 身份。
- S1/S2 控制模型、token、step、adapter、eval 和 seed；分别报告 processed/context/supervised tokens 和采集成本。
- 不能把 reward=1 等同高质量/grounded，也不能把 loss 下降等同 task success。
- 保留成功、失败、无效 run 原始证据；无效 run 不计能力指标，但计费用。

## 长期产物

维护 PROJECT_STATE、ENVIRONMENT_AUDIT、EXPERIMENT_PROTOCOL、FAILURE_TAXONOMY、DECISIONS、HYPOTHESES、COMPUTE_BUDGET、experiments/registry.jsonl 和 docs/daily/YYYY-MM-DD-learning-handoff.md。

每日结束停止新实验，handoff 应包含核心问题、前后状态、执行、变量、结果、代表轨迹、结论/推测、3–5 个代码函数导读、学习点、5 个无答案面试题、路线分叉及证据身份。
