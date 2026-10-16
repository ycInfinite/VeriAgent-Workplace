# Compute budget

2026-09-17 实测DeepSeek固定20：65请求，300129输入（276096缓存/24033未缓存）、7151输出；高峰费率估算0.11631784元，15条质量通过对应0.00775452元/条。采集88.080秒。904无卡0.10元/小时，UI开机00:48:13.970UTC到关机请求01:25:51.157UTC约0.06269964元；合计≈0.17901748元，非账单、不含存储/审核工时。三台均已确认关机。无GPU/参数更新。

2026-09-17 普通DeepSeek官方API选型估算：当前deepseek-flash(V4.1)每百万tokens空闲输入未缓存1元/缓存0.02元/输出4元，高峰2倍。沿用旧20次教师实验的387839input/9023output，未缓存估算0.423931–0.847862元；沿用75%完整合格率时1000合格约28.26–56.52元。都是跨模型情景估算，非DeepSeek实测或账单；CPU/审核工时另计。新模型调用/GPU使用0，计算见deepseek_flash_cost_20260917.json。

补记上轮收尾：2026-09-16定时关机后已通过AutoDL刷新观察到全部3台关机。904无卡约16:09至17:15，费用估计约0.11元，非账单；不能把关机后的状态描述成仍在运行。

2026-09-16 用户真实交互：6条主线响应合计48280input/796output（含255thinking），缓存38445、API耗时22.984秒；客户端聚合为7次/58620input/798output/24.467秒，差额来源未完全对齐，疑为后续建议。不用低口径代替总消耗，不将套餐Credits换算为未经核验的RMB。无新GPU/训练；本轮后续审计/修复无新模型调用，904待证据保存后关机，原17:15定时关机仍保留。

2026-09-16 交互交接：904无卡按0.10元/小时运行，AutoDL已确认北京时间17:15自动关机；按约16:09启动估算总计≈0.11元，非账单且未观察到最终关机。GPU0；Codex没有提交模型任务，首次CLI验收退出显示API时间0秒、工具调用0。留在网页中的人工会话若由用户发送任务，后续会消耗套餐Credits，应单独记录；未知额度不写成无限免费。

2026-09-16 交互接入实施：本地固定客户端/隔离SDK安装和CPU检查，API请求0、GPU0。904无卡启动确认价0.10元/小时、最低0.01元；会话尚未结束，最终CPU费用待计时，不能记为零。没有续费、套餐升级或新GPU租赁。

2026-09-16 套餐使用方案准备：仅本地文档/配置与官方来源核验，新增模型API请求和GPU使用均0。订阅剩余额度、实际账单和特殊退款资格未读取；个人版官方不支持退订。配置没有按量API后备，交互式调用未来消耗套餐Credits，不写成免费或无限。客户端集成时间与每条示范成本未测。

2026-09-16 用户要求Token Plan后，没有发起新API请求或开机，新增实验费用0；不自动回退到普通按量计费。套餐Credits消耗/可用性未实测，不把订阅价或既有额度写成免费无限采样。

2026-09-16 补充第三条教师数据路线：官方完整示范可审查后使用；现有reference的可观察子集可通过真实工具执行重建，可能减少API支出，但重建/审核工程成本与覆盖率未测。此前0.332元/批准是当前API路线的估算，不是项目每条训练样本的必需成本。本次只读取既有官方train结构，新增API/GPU/工具执行均0。

2026-09-16 教师成本复核：建议下一轮有限采集继续普通API，以每条质量批准轨迹计算成本。现有20题/15批准的未折扣模型费4.978896元≈0.332元/批准；100/300/500条合格轨迹的同分布线性预算约33/100/166元。新检查发现346624/387839输入tokens命中缓存(89.37%)；qwen3.8-max缓存单价官方要求查看控制台，不套其他模型的10%/20%规则，实际账单未核验。自部署按6.98元/计费小时需超过约21条同标准合格轨迹/小时才能低于此未折扣API估算。详见TEACHER_COST_COMPARISON_20260916.md；无新费用或运行。

2026-09-16 本次会话已收尾：新904实例与旧两台都已确认关机。用创建观察时间区间05:56:21–06:00:15UTC和关机请求UI时间06:39:39.186UTC，按6.98元/小时估算整机会话约4.58–5.04元，关机完成延迟可能增加少量费用，非实际账单。此范围包含0.064941元训练进程费，不能相加；本轮没有新教师API费用。约175MB adapter本地与远端备份哈希一致，不入Git。

2026-09-16 首次SFT实测：PRO6000单卡8步，平均1.4883秒/步；实际更新总计11.9063秒，完整probe含加载/保存/重载33.4939秒=0.00930387GPU-h，按6.98元/小时估算0.064941元。allocated峰值26.5315GiB、reserved峰值58.0918GiB、sampled used峰值60175MiB，30点平均利用率47.7percent（整个probe范围）。实际实例开机包含迁移、认证、GitHub重试和adapter备份，最终窗口见evidence/sft-probe/lifecycle_and_cost.json；进程费用包含其中，不能相加。没有再次调用教师API。

2026-09-16 替代实例：用户明确授权另找空闲单卡，创建并克隆北京B904 PRO6000 96GB。创建页最终费用6.98元/小时，免费50GB数据盘，付费扩容0，日常磁盘加价0。复制/准备/等待计入新实例运行费用；8步训练进程仍最多1800秒，即按此价至多3.49元进程费用，其他上线时间另计。旧两机均关机，没有双GPU训练。最终会话时长及账单待收尾。

[GPU_WATCH_LAST_CHECK] 2026-09-16T05:50:52.910422+00:00 — Inventory-only check; new GPU-hours/model-API calls/paid experiment charges=0; Codex account usage not included.

2026-09-16 定时检查：创建15分钟库存heartbeat，没有启动GPU或发模型API请求，本次新增GPU/API实验费用0。后台检查会使用Codex账户配额，未将该产品用量折算成GPU费用；有卡执行时按实际设备价格记录，完成后关机。无新租赁或套餐变更。

2026-09-16 TEACHER-ACQUIRE-20260916-001：80真实API请求、0重试、387839输入/9023输出、202.121秒，按已核验12/36元每百万tokens估算4.978896元。每官方成功约0.2766元，每完整质量批准约0.3319元；没有扣缓存/免费额度，不是账单。无卡会话约23.5分钟×0.10元/小时≈0.0392元（保守观察窗口），合计本轮约5.02元；独立存储与本对话产品不含在内。公开来源审查/文件传输等待包含在无卡窗口，不计GPU。PRO6000与A800均无卡可用，GPU计算0、SFT更新0，不产生SFT进程费用。未来A800实际启动价需现场记录，不能套用PRO的6.98元/小时。

2026-09-16 采集器回归：TEACHER-COLLECTOR-CPU-20260916-001禁止网络、未加载模型，新增GPU-h/API调用/付费实验费用均0；不含本对话产品用量或独立存储。用户确认普通按量API，但尚未请求；实际费用仍未产生。两台AutoDL关机状态本轮再次查看，后续只需无卡模式承载CPU环境/API循环。

2026-09-16 教师准备：CPU运行2.0213秒，GPU-h=0、付费API调用=0、新实验费用=0（不含本对话产品和独立存储账单）。官方北京普通qwen3.8-max价格为输入12元/百万tokens、输出36元/百万tokens，来源https://help.aliyun.com/zh/model-studio/model-pricing，核验2026-09-16。按先前20题306647输入/3310输出直接代入约3.80元，仅为量级参照；教师tokenizer/调用轮数不同，不能当预测。若按100万输入/40960输出估算则13.47456元，规划约4–15元，无缓存/免费额度抵扣；不是硬上限或账单。Token Plan不支持自定义批量采集；普通API访问未落实，尚未产生该费用。真实请求必须记录供应商usage/异常请求/重试费用，使用学生8192上限不能冒充供应商token上限。

2026-09-16 实测：启动确认价6.98元/小时；SFT-ACQUIRE-20260916-001运行88.021秒、0.02445GPU-h，费用估算0.1707元。含审核等待的保守观察窗口16.82分钟，线性换算约1.96元，包含少量未运行时间，不是账单；两项不相加。SFT更新0，两台已确认关机。证据见evidence/migration/2026-09-16/lifecycle_and_cost.json。

2026-09-16 实时报价快照：AutoDL按量单卡列表，普通A800专区5.59/5.88元每小时、北京B区PRO6000 96GB 6.98/7.35、北京B区A800-NVLink 7.98/8.40、西北B区H800 9.98/10.50（前者会员展示价，后者原价）。用户实际会员权益未推断，库存和价格可变；详见GPU_PRICE_CHECK_20260916.md。仅查价，未租卡/迁移/启动GPU。此前90GPU小时是宽松预算额度，不是已测或必需运行时间；完整机时应在实际SFT/DPO probe后按tokens和吞吐重算。

2026-09-10 GitHub文件同步：只做认证、固定ref文件下载和哈希检查，没有GPU模型计算。实例状态仍按已知无卡准备阶段记录；价格未提供，持续实例费用不估为0。金额门槛的用户覆盖不改变记录资源与费用范围的要求。

**2026-09-10 最新覆盖：用户明确免除当前 SFT 推进的金额门槛，不再因为 RMB30 或缺少报价等待确认。** 保留单 GPU、固定模型、20 条采集/8 次更新及各 1800 秒进程限制；不自动扩展范围。新无卡实例 0.5CPU/2GB，已完成依赖、16.38GB 固定权重下载和 CPU 检查。实际单价/账单未提供，当前无卡准备费用为 null/未知，不是 0；没有 GPU 计算或参数更新。后续照常记录 wall time、GPU-hours、已知价格和费用范围。以下早期报价/金额审批是历史记录。

2026-09-10 SFT-PREP-20260910-001：CPU 审计约 3.97 秒，GPU-hours=0，新增付费 GPU/API 费用=0；采集包 81,809 bytes。下一轮固定采集最多 20 条、进程硬上限 1800 秒，费用上界为 0.5×实际小时单价，超过 RMB30 不自动启动。新 A800/A100 80GB 的型号、报价和实例尚待用户提供；SFT 训练费用仍须 probe，未沿用旧 4090 价格。实例空闲/准备/存储与进程费用分开核算。

2026-09-10 互动学习：只读本地材料并记录讲解进度，无远端操作、新实验或参数更新，新增付费 GPU/API 费用为 RMB 0。

同日 SFT 学习模块补充：只查阅公开官方文档并编写 Markdown 教学代码；未安装 PEFT、加载训练模型或运行代码中的 optimizer。SFT step time 和训练费用仍未实测。

2026-09-08 学习整理：只读取既有证据、更新文档，新增付费 GPU/API 费用为 RMB 0。未连接实例或核验新的平台账单；以下实测与费用估算仍属于 2026-09-04。

同日内嵌源码与手机学习版本仍为本地文档整理；未加载模型、执行训练或新增付费实验。

更新：Day 3 已完成。按用户确认的 1.98 元/小时，受控会话从 SSH 创建到发出关机命令约 0.872 GPU-hours，估算 RMB 1.73；其中三次模型运行含加载共 0.158 GPU-hours，约 RMB 0.31（已包含在 1.73 中，不能相加）。未访问实际账单，未包括更早的开机时间、独立存储费用及本地电费。没有付费模型 API 调用。

CPU 阶段官方源文件 33.14MB、tokenizer/config 11.43MB；Day 3 在远端新增约 16.38GB 权重，本地仍未下载权重，BFCL cases 始终未下载。CPU 依赖留在本地项目 .venv；远端另建独立 .venv 并复用镜像 PyTorch，没有更改全局已安装包。

规划价格 p=RMB 10/GPU-hour 只是占位，不是平台报价。租用前重新核价。单次预计超过 RMB 30 必须明确批准；无自动续费/多卡/扩大模型/context/seed。

| 档位 | S1/S2 各自 processed tokens | DPO pairs | 数据采集 output tokens | GPU-h 预算额度 | p=10 加余量 |
|---|---:|---:|---:|---:|---:|
| 低预算 | 2M | 150 | 0.5–1M | 45 | 约 550 元 |
| 正常 | 5M | 300 | 1–2M | 90 | 约 1100 元 |
| 扩展 | 8M | 500 | 2–3M | 140 | 约 1700 元 |

这些是额度，不是测出的耗时。额度包括 rollout、训练和评测，最终根据 probe 重算。扩展版最多预留约 10h 给获批 RL；p=15 时该档超过 2000，必须缩减/取消 RL。

SFT 的 processed token 与 supervised token 分开记；已测的单条学习 fixture 4536/89 不能当作整个训练集平均比例。DPO 按 chosen/rejected 两支分别计 token，reference forward 的时间也计入。rollout 的多轮累计输入会重复包含前缀，不能与一次 SFT 序列 token 混算。

此前 Q0 的 RMB 80/2–5 GPU-h 是粗规划。用户后续授权既有实例上的 Day 3，实际远低于该估算；没有把 RMB 80 当作超 30 元实验的默认授权。已关机，下一阶段另行规划。

AutoDL 补充（2026-09-04）：实际 1×4090 24GB、并发 1 已完成测试，报价为用户确认的 1.98 元/小时。本次接入时已是 GPU 模式，准备/下载时间计入上述 1.73 元估算。无卡模式官方说明为 0.1 元/小时（0.5 核/2GB RAM），可作为后续准备优化，不能把这次准备时间虚记成无卡费用。此前 2–5 GPU-h 是粗估，不替代实测。

| 必测项 | 当前值 |
|---|---|
| peak VRAM / utilization | 本轮 allocated 最大 17.17 GiB；nvidia-smi sampled used 最大 19.80 GiB；B0/B1 sample mean utilization 60.7%/63.3% |
| policy generated tokens / trajectory length / rollout wall time | 75 条共 11,186 output tokens；B0 324.66 秒、B1 214.07 秒（各含加载）；详见 DAY3_REPORT |
| SFT / DPO step time | 未测 |
| GRPO rollout / update time | 未测 |
| adapter load/save consistency | 未测 |
| cost per verified LLM success | B0 约 0.0162 元，B1 约 0.0147 元，仅含各 run wall time；不包含准备费用，以官方 state reward=1 为分母 |

正式 GPU probe 必须记录设备型号、驱动/CUDA/框架版本、prefill/output tokens、冷启动、并发、显存峰值、总 wall time、账单小时及 RMB。

2026-09-08赛事筛选：仅公开网页与规则检索，新增付费GPU/API实验费用为0；不含本对话产品用量。未购买算力、未报名付费赛事，未来参赛训练成本未估算或授权。

同日ARC Milestone规则补查仍为公开网页只读检索，新增付费GPU/API实验费用0。


## 2026-09-17 remaining-pool window preparation

Noon723 API extrapolation from20: cache-matched2.102445RMB; no-cache11.883698RMB; runtime3184.10s. These are estimates,not caps or invoices. CPU/no-card0.10RMB/h including waiting/preflight; no GPU. At14:00 preserve partial/unknown usage. User current budget waiver retained.


### Actual queue verified 2026-09-17

Actual model/API usage at10:30:55 =0; CPU-only instance awaitingstart,0.10RMB/h. Startupapproximately10:14,shutdownlatest14:00 givesrough0.38RMB CPUwindow excludingstorage; actual end/costpending. GitHub transfersfailed once404 butrecovered; includeCPUwaitinginfinalcost.


### 2026-09-17 first running observation

Running snapshot: 266 requests,1233564 input/30873 output,known API tariff estimate0.23098112RMB; CPU session excluded/not invoice. GPU0/updates0. Final totals pending.


## 2026-09-17 completed723 acquisition

Final新增723:2443calls,input11374350/output283925,cachehit10601856/miss772494,knownmodelestimate2.12023112RMB,unknownusage0. CPUwaiting+deployment+collection+retrievalapprox0.28,totalapprox2.40excludingstorage/notinvoice. Acquisition3028.688734s,modelcostperofficialsuccess0.00319312RMB;qualityapproved-costnull. GPU0/updates0. Earlier20qualificationcostseparate. OfflineUTF8auditfailurepreserved,noAPIorGPUcost.


## 2026-09-17 pre-SFT readiness

SFT-READY CPU-only actual newAPI0/GPUhours0/parameterupdates0/noinstancestart. FutureS1=1,425,440processed/28,546supervisedtokens,S2=1,415,914/29,114,310updates each. Longestsequence7208 vs priorprobe4741; newpeakVRAM/step time unknown. Planning2train+3devconditions roughly0.75-1.5GPUh,notmeasured. Hardlimits60min/trainarm,30min/evalcondition; actualhourlyprice optionalandunknowncostnull. No automatic launch,sweep,contextgrowthorbudgetchange.


### Final actual-host SFT preparation

Additional actual-host preparation:904CPU0.10RMB/h,roughly14:26–14:43plusshutdownconfirmation;estimated0.03RMBincludingGitHubretries/idle/preflight/retrieval,notinvoice/storageexcluded.52.73scheckprocessincluded. NoAPI/GPU/modelupdates.


## 2026-10-10 resume

2026-10-10resume localchecks only:GPUhours0/newAPIcalls0/updates0; noinstancestart. CurrentGPUprice/inventory/cache unknown,do not reuseSeptemberavailability ascurrentfact. Prior0.75-1.5GPUh remainsestimate,not actualusage.

### 2026-10-10 新租实例后续执行

用户随后提供已租 PRO6000 96GB 实例，恢复代码/环境/16.38GB 原权重，10:28:14 中国时间启动新 BASE_B1。上述 resume=0 仅描述较早本地检查时点；实际 GPU 实例在恢复期间已计费，不能继续记作0。单价未知，金额 unavailable；最终分开报告脚本实测 GPU-hours 与包含安装/下载/检查/回收等待的实例占用时长。无需因旧30元门槛重复询问，用户此前的本阶段预算豁免仍有效。


## 2026-10-10 actual complete resource record

BASEeval230.489s,S1train478.891s,S1eval630.250s,S2train474.173s,S2eval744.487s;sum2558.289s=0.710636GPUh. ContainerPID1startestimate1791594575.89 toofficialshutdownrequest1791603215.6105056 gives2.399922h;notverifiedbillingstart/end. Includes restore/install/idle/gaps/retrieval. Currenthourlyrateunknown,RMBnull. S1/S2meanstep1.419334/1.409406s;allocatedpeak32.1356/29.3690GiB,reserved81.7305/56.4648GiB. Devicepollmax82.3857/57.1201GiB;meantrainGPUutil88.83/89.60%. Actual96GBonly,notproofof80GBfit. Inferencecostperofficialsuccess inGPUh:BASE0.0042683,S1 0.0050020,S2 0.0062667;multiplyactualhourlyrate,exclude training/setup/storage. UnmergedLoRA andlongeroutputs confoundpurelatencybehaviorattribution. NoDPO/GRPOtime measured.


## 2026-10-10 下一轮准备成本

本轮本地CPU检查：新增GPU-hours0、API0、参数更新0，没有远端开机。POSTSFT审核主脚本2.29s，S100成功准备主脚本12.04s，另有格式/准入检查；这些不是整轮人工/CPU总耗时。拟执行S100训练+评估约0.3–0.4scriptGPUh，基于同卡前轮估算，不是实测；部署/预检/回收另计，时价未知。硬上限训练60min+评估30min。用户报告缺卡，尚无新增GPU费用。


## 2026-10-10 NOOP83与MIX100离线准备

本轮GPU0/API0/参数更新0。NOOP导出与一次MILP主脚本4.20s，其他审核/编码/CPU检查另有本地耗时；无付费采集。MIX100一遍310步：processed1450298,target28695,max7756。相对S100两种token分别+1.3869%/+1.3707%。未来每组train+eval估计0.3–0.5scriptGPUh（非实测），max7756显存需重新实机验证；训练<=60min、48条eval<=30min。单价未知，人民币不估造。

## 2026-10-12 S100/MIX100实际资源

单PRO6000 96GB：S100 train474.931s/eval733.446s，MIX train484.854s/eval605.742s，总0.638603822GPUh。容器启动估计→官方关机请求1.015973377h；项目首次观察→请求0.949223273h。包括部署404重试/等待/回收，非平台账单。当前时价未知，RMBnull；若时价p则占用近似1.016p，存储另计，不能复用旧价格。推理GPUh/官方成功S100=.006366716、MIX=.004206543，不含训练/部署且非语义合格分母。

S100/MIX step1.4082/1.4321s；allocated32.136/33.381GiB，reserved88.209/90.998GiB，设备采样used88.896/91.685GiB；train利用率采样94.19%/88.95%。96GB已验证，不能据allocated声称80GB直接可跑。当前未测DPO/GRPO。620updates/96validrollouts/0infra-invalid，0新teacherAPI。原始resource报告与关机收据位于reports和evidence/sft-extension-20261012。保护已取消、官方关机已执行、SSH不可用；控制台计费状态未独立确认。

## 2026-10-12 DPO准备

DPO本轮GPUh0/API0/parameterupdates0；26branch CPU回放+编码主脚本5.608s，非整个审核总耗时。8pair probe单次数据经过204089processed（chosen111571/rejected92518）、3376targets，reference/无梯度/重算需多次forward。未来0.05–0.15scriptGPUh仅估计，1800s脚本上限，部署等待另计，时价未知。只准备96GB方案，80GB未资格。无远端开机/租用，旧监控未恢复。

## 2026-10-12 DPO实机8步完成

DPO-PROBE-20261012-001：reference17.9496s、8pair平均9.64436s，总131.19964s=.03644435GPUh。allocated20.7389/reserved31.2793GiB，121采样util均87.8926%、设备used峰31.9658GiB。容器启动估计→关机请求.31416227h，项目首次观察→请求.24397338h；含部署/网络等待/约175MB权重回收，非平台账单。实际时价未知、RMBnull；若p元/h则全占用约.3142p，存储另计。单pass204089processed/3376targets，三pass612267/10128曝光，另有固定readout2×64tokens。无Agent评估，cost per verified success未定义。当前8对96GB实测，不等同80GB/全8K资格。

## 2026-10-12 正式小偏好对照完成

本轮五脚本GPUh.63621145，按新读AutoDL6.98/h估计4.4408元；实例启动估计→关机请求1.02247957h约7.1369元，包含部署/两CPU导入故障/等待/回收，不是账单，两数不可相加。CHOSEN_SFT/DPO训练87.299/191.683s，平均task/pair步4.2958/10.6081s；DPOreference29.3623s。allocated均20.7389GiB，reserved54.4082/35.3770，设备used55.0947/36.0635，采样util63.525%/83.028%。基线/SFT/DPO eval629.493/681.509/700.378s。备份IO与训练/评估部分重叠，时延不作纯算法因果解释；96GB当前范围实测，不推定全8K/80GB。API0，新training24updates，eval144valid0infra。

## 2026-10-12 S1新失败采集准备与等待

本阶段只有本地CPU准备，GPUh0/API0/updates0；两台已有实例开机库存检查均freeGPU0，没有开机成功。未新租/监控。未来25rollouts估计0.12–0.25scriptGPUh（非实测），若沿用上次6.98/h约0.84–1.75元脚本费用，部署回收另计，执行时重新核验单价。准备停留不等于开着GPU等待。


## 2026-10-16 当前S1 training25采集

实际329.248秒=.09145779script GPUh，逐轨迹合计307.687秒；输入408835/输出8634，89模型轮/90工具步。allocated17.363GiB、reserved19.482、设备采样20.161；306样本平均利用率66.163%含加载/检查。无参数更新/教师API。50分支CPU审核主脚本11.781秒，另有人工阅读/完整性检查，不是全部审核耗时。

容器估计启动至保存0.46774573h，首次项目观察至保存0.30999296h，不与脚本时长相加；时价未知/RMBnull。每官方success .00508099script GPUh，每奖励差pair .01524296script GPUh（不含审核/闲置）。用户明确保留开机，保存后持续占用GPU计费、无关机guard，SSH已关闭；上述小时数不是最终账单。后续本地审核期间机器闲置也计实例费用。证据resource_summary.json和远端preservation.json。


## 2026-10-16 六对currentS1方法对照

两训练总时56.54565/122.12143秒，meanstep4.16751/11.79140秒；DPOreference16.46562秒。allocated21.0707/21.1283GiB，reserved34.9414/34.6680，设备采样峰35.6279/35.3545。五脚本总0.52994010GPUh（31.8分钟）；三eval550.6005/567.9415/610.5753秒。144valid0infra、12actualupdates、0teacherAPI。一次CPU启动故障纳入实例占用，未产生模型调用。

矩阵首次观察至备份收据0.73988955h，容器估计启动至收据1.40606495h（含此前25题采集及闲置）；不要相加。时价未知/RMBnull/非账单。推理GPUh/官方success S1=.00436985、SFT=.00438226、DPO=.00498836，不含训练/采集/部署。大adapter下载在所有计算完成后，小结果下载曾与后续运行重叠；延迟不作纯算法因果解释。按用户keep-on保留实例、SSH已关、无计算进程/关机guard；此后继续计费。原始resource_summary.json完整保留。
