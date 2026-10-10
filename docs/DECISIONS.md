# Decisions

2026-09-17 即时DeepSeek资格测试完成：19/20官方成功、整轨迹质量15/20，API估算0.1163元。建议作为下一轮主教师候选；同15个任务的替代轨迹不算新增任务覆盖，不自动训练。5条hold的原始reward不变。停止在新provider训练导出准入之前，所有实例已关机；用户取消的12–14窗口不恢复。

2026-09-17 用户改回普通API并提出DeepSeek Flash候选；停止继续投入Token Plan客户端路线。先按官方API核价并建议固定20题资格测试，不把低单价等同高质量、不自动调用API。旧Token-Plan-only偏好被覆盖，历史数据和已完成SFT不变。详见 DEEPSEEK_FLASH_ASSESSMENT_20260917.md。

2026-09-16 首条官方客户端交互成功，但不扩大采样或直接入SFT。保留reward1，同时标记8K/non-thinking配置未生效和日志口径差异；事后审核不冒充B1预登记。修复--bare配置加载、关闭建议请求、紧凑化完整JSON，仅做离线/CPU验证。已有15条合格API示范不受影响。

2026-09-16 交互接入完成交接：采用官方客户端真实交互入口，部署318e233，现有904仅无卡运行。Codex侧栏没有实际显示受控SSH终端，改在Edge的JupyterLab打开Qwen界面并核验workplace connected；由用户亲自发起任务，不自动发送模型提示。17:15定时关机已由AutoDL确认。没有任何新模型成绩/SFT批准，也不将此路线包装成自动采集。详见 INTERACTIVE_CLIENT_READY_20260916.md。

2026-09-16 直接落地交互路线：安装固定官方Qwen Code0.23.4与隔离MCP1.30.0，采用单training任务、六次真实工具调用上限、结束后不可重置的工具桥。保留客户端交互与人工发起要求，不通过PTY/脚本提交Token Plan提示词。904仅无卡准备，GitHub同步白名单增加五个已审查文件；不改旧采集器保护或训练准入。CPU001/002无效记录保留，003通过18项。

2026-09-16 套餐使用方案：补充官方明确允许的交互式编程/智能体扩展路线，优先用于本项目代码理解、训练数据审核和单任务开发调试。准备无Key的客户端配置与未发送客服问题；不把换客户端包装批量采集当合规方案，不安装/登录/代发工单或启动模型实验。个人版官方不支持退订，特殊退款不作保证。详见 TOKEN_PLAN_INTERACTIVE_HANDOFF_20260916.md。

2026-09-16 Token Plan要求：记录用户指定套餐渠道，并停止将普通按量API当作默认后备；这不等于套餐已支持批量脚本。官方规则复核仍明确排除该用途，因此没有修改采集器端点白名单或执行新请求，也不伪装为允许的编程客户端。等待适用服务路径，不把一次HTTP成功推导为用途授权。

2026-09-16 官方数据澄清：不把当前probe的模型/API producer白名单扩大成“官方/人工/脚本示范不能SFT”。当前锁定文件只有任务和reference动作，707等缺前置lookup及观察；565等参数可从问题确定的子集可能低成本重建。未来先审计可复用比例，完整官方示范直接审查、缺失过程再补齐，明确source并保持training切分。没有自动改准入或重训，详见OFFICIAL_REFERENCE_VS_TRAJECTORY.md。

2026-09-16 教师部署咨询：当前建议继续普通API教师；本地8B原20题0完整示范批准，不能因原始生成便宜就直接替代Max。其他开放教师需质量/总费用资格后再决定部署。已记录缓存命中证据与未知专属折扣，不更改原实验费估算、不启动新采样/部署；该建议不是正式下一阶段实验授权。

2026-09-16 首次SFT已完成：在替代904 PRO6000上按固定0a7eba8执行原2条整轨迹/8步LoRA probe，全部完整性门槛通过。真实参数更新与checkpoint重载成立；不以不同样本loss首尾变化推导能力提升，不把仍有假ID的单次greedy读出算完整Agent评测。保存adapter及原始证据后关机，监控保持暂停，后续正式学习/评测阶段不自动启动。

2026-09-16 替代单卡：用户不再等待旧机库存，明确要求找新空闲实例。选择同地区904机PRO6000 96GB、6.98元/小时，克隆原PRO6000系统盘和数据盘，避免重配Torch/权重；同区A800-NVLink报价7.98且不必更换已验证架构。仅1卡、不付费扩容，源机保留关机，旧库存heartbeat暂停。复制完成，尚未更新参数。

[GPU_WATCH_LAST_CHECK] 2026-09-16T05:50:52.910422+00:00 — No route/configuration change: preserve existing instances, do not rent or duplicate runs; continue the existing15-minute monitoring.

2026-09-16 定时监控：应用户要求创建当前对话15分钟heartbeat `veriagent-gpu-sft-probe`，优先检查既有A800并兼查PRO6000。复用已授权的两条完整轨迹/8步单卡probe，先查registry/进程防重复，完成保全证据并关机后暂停监控；无新租赁或扩大阶段。库存不变不通知；本地机器/App/浏览器登录不可用时不虚称监控成功。

2026-09-16 真实教师与库存停点：普通百炼qwen3.8-max固定20题18成功，15完整轨迹批准；学生输入严格采用完整707/965两条、共8轮/582目标tokens，保留上下文mask，不使用此前被拒的选择性片段。16项负向CPU准入与远端检查通过。按用户常规操作授权结束无卡模式，PRO6000库存0；自动审批曾拦A800入口，用户明确允许A800执行8步，随后A800也显示库存0。两机关机、参数更新0，等待既有GPU可用；不重复同一A800审批、不租新实例、不扩大实验。

2026-09-16 发布审查：工作场景邮箱字段曾触发自动审批疑虑；检查13个官方源文件哈希、220个输出邮箱均在NVIDIA公开CSV、初始状态与官方环境相同，附公开数据卡Synthetic/CC BY4.0证据，随后同一GitHub推送获批。没有通过改传输工具绕过拒绝，没有混入公司材料。

2026-09-16 普通API采集器：用户确认普通Key及workspace端点后完成有界CPU采集入口，保留原strict工具schema和真实工具状态；禁用自动重试，截断动作不执行，APIusage与学生tokens分账。55项无网络检查通过；GitHub白名单只扩展4个已审查执行文件。两机仍关机，等待用户允许无卡启动和终端隐藏Key输入。没有把聊天密钥写入项目，也没有扩大教师任务或自动训练。

2026-09-16 教师来源准备：按用户“进行下一步”恢复完整轨迹数据准备；新增teacher_request隔离参考答案、CanonicalTeacherEncoder将全部可见assistant决策按固定学生模板编码。CPU审计20题/69轮及5项负向检查通过，但不批准旧数据。用户指定百炼qwen3.8-max/Token Plan；官方套餐不支持本项目自定义批量脚本，先落实普通按量API访问，不自动切计费、不改为通过编程工具代跑批量任务。学生仍Qwen3-8B、固定20题/B1，正确片段方案仍不采用。来源及待执行方案见TEACHER_PREPARATION_REPORT_20260916.md。

2026-09-16 实际采集与停止：用户批准跨实例拷贝和新PRO6000开机；20条完成，3条官方成功、0条整轨迹SFT批准。提出2任务5正确片段的单独方案后，用户要求保持原方案、停在审核。没有改变监督目标或更新参数；GPU已关闭，原始轨迹、提案和决定保留，后续路线待新指示。

2026-09-16 查价建议：基于AutoDL当前列表，综合候选PRO6000 96GB，小时费用优先则普通A800专区；不为当前单卡任务优先选更贵的北京B区A800-NVLink。H800是否省总费用需实测吞吐超过PRO约43%的加速。此为推荐而非已迁移决定，没有租卡或变更实验。

2026-09-10 传输方式：用户明确要求 GitHub 传文件，bc5aa55 已推送并被远端按固定ref下载20个执行文件。仓库经官方接口确认为private，匿名clone失败；采用本地既有Git登录取得临时文件链接、远端直接GitHub下载并验SHA256/Git blob。账号凭据不传远端，链接不落盘，不修改仓库可见性。保持执行白名单和模型/venv/数据隔离，不以SFTP打包作为默认代码同步方式。

2026-09-10 无卡阶段：用户提供新实例，并明确覆盖金额审批；不再要求价格才能前进。复用现有 torch2.8，独立 venv，下载固定 Qwen3-8B 并校验，完成20题远端tokenizer/CPU工具检查。准备8更新LoRA入口，保持数据审核门槛。无卡限制下不加载模型或尝试绕过 GPU 权限，下一步待用户切回 GPU；不扩大实验矩阵。

2026-09-10 实验推进：按用户最新指示改为实验优先、粗颗粒教学。采用逐轮真实输入/输出编码，CPU 200/200 核对通过；固定 training pool 的 20 题用于下一次单 seed 数据采集。B1 仅为 probe 候选；不把 dev 成功加入训练，不依据模型结果换题，不扩大为正式对照或 RL。新实例选择 A800/A100 80GB，实际价格待用户提供。

2026-09-10 学习安排（已按用户更正）：用户说明 Day 3 前内容基本掌握，直接进入 SFT-A 的 LoRA 与真实更新机制，不再把基础 mask 复习题作为入口。发布第五课；旧考核未评分但不阻挡学习推进。教学代码未执行，无参数更新授权变更。进度记录在当日 handoff 和 ASSESSMENT_STATUS。

| ID / 日期 | 决策与理由 | 状态 |
|---|---|---|
| D001 / 2026-09-04 | 固定 Gym/NVIDIA 数据集，不使用浮动 latest 或新 Nexusflow prepare 入口 | 已执行 |
| D002 | 直接调用官方工具/verifier，采用小型本地适配层采集状态；不安装完整 Ray/训练框架 | CPU 路径已验证；不声称原生 NeMo launcher 验证 |
| D003 | BFCL 只读取协议与版本文档，cases 未下载 | 保持 sealed |
| D004 | 相似候选和模板亲缘保守隔离，原始数据及原清单保留 | SPLIT-003 生效 |
| D005 | 按写操作任务与 no-op 任务分开评价；不再用总体 20% 门槛单独放行 | 写入模型资格计划 |
| D006 | CPU 原始 24-task 样本用于环境检查；未来模型 pilot 重新按最终清单固定 20+4 分层 | 无模型结果参与选题；保留前版 |
| D007 | 学习 fixture 永不进入 SFT/DPO 数据：它来自 dev 且由脚本生成 | 已写 eligibility=false |
| D008 | strict composition held-out 不成立为已验证事实；181 条只是预留 | 需用户路线决定 |
| D009 | 无 GPU、无模型权重、无训练；接下来先学习、考核 | 当前停点 |
| D010 | 模型 pilot reference 调用最多 4 次，排除明显不适合六轮预算的任务；保留原 draft | SPLIT-003；不保证额外 prerequisite 总长度 |
| D011 | 用户允许继续推进；先准备单卡选型、只读远端 preflight 和独立 smoke 计划 | 待个人平台/实例报价；付费与后续阶段边界不变 |
| D012 | 用户明确 AutoDL 与 Day 3 纯推理范围；24GB 4090 单并发优先，80GB 留作后续训练规划 | 工程估算，需实测；无卡模式用于文件/轻量准备，不加载 8B |
| D013 | 按用户重申的 Day 3 范围准备资格测试；学习/考核和组合泛化保留为独立待办，不额外充当付费审批条件 | 实际价格/预算确认仍必需；未授权参数更新 |
| D014 | 用户授权个人实例 Day 3 全流程，确认 1.98 元/小时；复用 torch 2.8+cu128，选 Transformers 4.56.2/SDPA | 单卡运行完成；无 vLLM/Ray/参数更新 |
| D015 | B0 48 条有效，动作任务成功不足；按预登记条件只执行一次 B1 | paired seed 42 净增 3 个恢复成功；不再调 prompt |
| D016 | 75 条证据取回并核验后执行关机，SSH 被远端关闭 | 约 1.73 元会话估算；不含先前开机/独立存储 |
| D017 | 语义标签由 Codex 逐条复核，保留自动候选及 v1 分析；v2 修正 reviewer 说明和两个 B1 primary labels | 不宣称独立人工复核；原始结果不变 |
| D018 | 发现四个强制 non-thinking prefill tokens 与 policy 输出/target 的差异 | SFT/DPO 前必须做逐轮 conditioning / trainer mask 对齐 |
| D019 / 2026-09-08 | 用户中断三天后需要恢复学习；整合四课、真实证据与分阶段考核，并明确 CPU/模型历史边界 | 已生成学习合订本；原材料保留，未新增实验，未评分 |
| D020 / 2026-09-08 | 用户夜间只用手机与 GPT 学习；同一 Markdown 内嵌关键源码、逐段变量讲解、真实轨迹/token 证据和无需仓库的考核 | 21 段源码摘录；教学算例明确标注，无实验代码修改或训练 |
| D021 / 2026-09-08 | 按仍可报名、12月前正式出结果筛选Agent/后训练赛事；报名人数与队伍数分开，单题日期优先于聚合摘要 | 已保存官方来源清单；建议优先CCF BDCI职场Agent，未报名或切换研究路线 |
| D022 / 2026-09-08 | 用户补充目标是12月投实习、已做ARC-AGI-3并等待Milestone2发布；据此撤回把BDCI作为默认主赛的建议 | 核实里程碑奖金要求截止前开源；等待开源方案是合理推断，具体M2公告发布日期未查到 |

待用户选择：A. 保留 Workplace 做 grounded lookup→state mutation 的数据选择研究，收窄泛化主张；B. 后续独立设计少量受控 composition 任务并审计其语义；C. 若严格组合泛化不可让步，比较其他环境。未自动选择 B/C 或开始生成任务。


## 2026-09-17 remaining-pool window preparation

Select ALL remaining training723 using domain-interleaved frozen order,exclude prior20,include empty-reference83 with held admission. User explicitly expanded acquisition scope. Hard stop today14:00; no resumption/next day or parameter update.


### Actual queue verified 2026-09-17

The one-shot worker is actually armed at2ca291c,with hard UTCwindow and duplicate directory guard. App follow-up exists and expires today; platform14:00 shutdown set. Private GitHub publication and deployment succeeded after preserved TLS/404 and stale-authorization review failures. Do not redeploy the waiting worker.


### 2026-09-17 first running observation

User said开始; verified the original worker instead of launching another. Same source/protocol/window, no experiment-variable changes.


## 2026-09-17 completed723 acquisition

Completed exactly723 once. Keep all59 official failures and all raw successes. Mechanical629 are NOT approvedSFT;94 flagged needreview. Noautomaticresampling/training. Savedexactarchiveplusmemberhashes,insteadofduplicating81MB expandedJSONL inGit. CPUoffandbothmonitorspaused;timerremoved.


## 2026-09-17 pre-SFT readiness

FirstboundedSFTcomparison uses fixed150manualreview candidates(30/domain),137 approved. S1/S2each50wholetrajectories/155turns,2epochs310updates;whole-target policy unchanged. Domain-stratifiedrandom versus frozenfailurecoverage heuristic;MILP onlymatchesdata/stepbudget,no modeloutcometuning.13holds include6pagination,3math,1dateboundary,1crossdomainID,1out-of-rangepage,1unexecutedverificationplan. Unreviewedremainingdata held,notdeclaredwrong. NoGPUexecutionorremotedepoyment; nextstartrequires userdirection.


### Final actual-host SFT preparation

Finaloperationalpreparation completed on904CPU/no-card withf9d45c2.54GitHubfilesplus15existingvendor/data allhashchecked,actualtokenizer155+155matches,9modelaux/weightchecks. No packageinstallation/modelconstruction/API/GPU/training. Hostoff,timerremoved. Preserve2rawdownload404attempts and3rdsuccess.


## 2026-10-10 resume

User requests nextstage; treat as authorization for the concretelyprepared S1/S2+matcheddev matrix. Keepall50tasks/155turns/310updates andseedprotocol frozen. PreferexistingownedGPU; no newrental inferred. Resourceaccessiscurrentlyunavailable,notadatagatefailure.
