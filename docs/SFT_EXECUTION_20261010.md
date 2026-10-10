# 2026-10-10：首轮 S1/S2 训练与配对开发评测

两组真实 LoRA 训练各完成310次更新；BASE_B1/S1/S2各完成48条真实环境评测，144条全部有效。两组adapter保存、重载、本地哈希验证通过。官方关机命令已执行，原SSH断开且重新连接被拒绝；AutoDL控制台计费停止时间未独立核验。

这轮支持“两种SFT都改善了固定开发集表现”，**不支持“failure-targeted S2已经优于随机S1”**。没有进入DPO、RL或sealed evaluation。

## 固定实验与控制

问题：近似等训练token下，完整成功轨迹的failure-targeted选择是否比按业务域分层随机选择更有效？八项预登记见`experiments/SFT-RESUME-20261010-001/config.json`，新实例恢复见`experiments/SFT-RECOVERY-20261010-001/`。

- Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`；两组均从同一Base全新初始化LoRA，不接续旧8步probe。
- 单PRO6000 Blackwell96GB；Torch2.8.0+cu128、Transformers4.56.2、PEFT0.17.1、Accelerate1.10.1。
- 每组50完整任务、每域10题、155 assistant turn样本/epoch，两遍310更新；r16/alpha32、lr5e-5、seed42、microbatch1、无截断。
- S1/S2分别1,425,440/1,415,914 processed tokens；28,546/29,114 supervised tokens。相差−0.67%/+1.99%，不是精确等token。16任务重叠。
- 相同B1、dev24×seeds42/43、non-thinking、8192context、6轮、2048累计输出；固定最终checkpoint，无checkpoint挑选。
- 执行代码保持`f9d45c282b7cbebeedb1063e3c2c705330e0b23c`；数据revision `c86a908379e0a361a573c395e175d3c1aa128e6c`；Gym commit `83b3980b9c04379d72bbf59592d7846630f706bf`。

## 原始结果和分母

| 指标 | BASE_B1 | S1随机SFT | S2定向SFT |
|---|---:|---:|---:|
| 官方成功/全部rollout | 15/48，31.25% | 35/48，72.92% | 33/48，68.75% |
| 非空reference成功 | 9/40，22.5% | 30/40，75% | 31/40，77.5% |
| 空reference成功 | 6/8，75% | 5/8，62.5% | 2/8，25% |
| 可执行调用/调用尝试 | 137/142，96.48% | 159/161，98.76% | 224/229，97.82% |
| schema错误调用 | 5/142 | 2/161 | 5/229 |
| 未注册工具调用 | 0/142 | 0/161 | 0/229 |
| typed identifier错误候选 | 24/76 | 0/76 | 2/125 |
| 平均工具步数 | 2.96 | 3.35 | 4.77 |
| 累计input tokens | 731,438 | 775,142 | 847,225 |
| 累计output tokens | 8,579 | 15,603 | 18,730 |
| 平均轨迹秒数 | 4.36 | 12.64 | 14.98 |
| 评估GPU-hours | 0.06402 | 0.17507 | 0.20680 |

成功率为trajectory-level的官方reward=1比例；每题两次，共24个独立任务簇，不是48个独立任务。partial progress不折算正式成功。空reference单列。基础设施无效本轮0；若有则排除能力分母、保留记录且计费用。

可执行率分母为已解析call+parse错误尝试，本轮parse错误0。schema错误不是全部语义参数错误；工具名存在也不代表选对工具。typed候选只检查当前类型表成员及用户/工具上下文中的字符串可见性，不证明实体解析、范围选择或检索完整性。0候选不等于0语义错误。

原自动same-state重复候选分别6/3/7次，三次连续same-state循环候选均0；失败且主动结束候选26/13/13条。**这些不能直接作为完整语义版redundant/retry/premature指标**。新逐调用全量语义标注尚未完成；已审核案例见`representative_review.json`，不复用旧Day3标签、不把未审核记为0。

## 假设是否支持

主要对比为非空reference上的S2−S1：**+2.5个百分点，95%任务簇配对bootstrap区间[−20,+25]个百分点**。20个任务中3个改善、3个恶化，不能判定S2更好。总体S2−S1为−4.17个百分点，区间[−25,+16.67]。

S1−BASE_B1在非空任务为+52.5个百分点，区间[+30,+75]；S2−BASE_B1为+55个百分点，区间[+30,+80]。10000次task-cluster resampling中，两个seed始终留在同一任务内。这只描述已暴露开发集上的固定小样本；不是多训练seed稳定性、跨数据库泛化或sealed test成绩。

S2修复S1在414/684/1112上的官方失败，也在1/18/220等任务退化。空reference上的额外修改值得审核，但不能据此证明“定向选择导致普遍过度行动”。不因本轮分数自动扩大预算、加seed或重采样。

## 真实行为例子

- task184/seed42：BASE把Quinn Taylor当customer_id；S1先查出00000090再删除，失败变成功。
- task0/seed42：S1最终成功，但给email_search_emails传了不支持的recipient参数后才纠错，还重读已知sender。成功不等于过程无错。
- task414/seed42：S1使用真实、已观察ID，却选中Completed任务；S2按Backlog检索后匹配官方目标。Grounding不能替代条件判断；S2的Backlog限定也不能单凭reward成为通用正确规则。
- task220/seed42：S2正确查到Nadia邮箱，却虚构新客户邮箱、电话等可选信息，最终失败。
- task1/seed42：S2把列表末尾10:00事件当当天最后，即使同一观察已有15:00事件，是排序/目标选择错误。
- task12/seed42：S2查到In Progress为空后，转而把In Review的4条任务移到Backlog；接口合法、ID有来源，仍违反范围。
- task952：S1排除今天到期任务，而官方reference包含它。保留官方失败与边界歧义，不自动把它做DPO rejected。

以上为Codex单审的事后说明性案例，无独立人工裁决，不构成全量语义错误率。开发轨迹不能进入SFT/DPO训练，后续训练样本仍须来自training pool。

## 训练完整性和资源

| 指标 | S1 | S2 |
|---|---:|---:|
| 真实optimizer更新 | 310 | 310 |
| 可训练参数 | 43,646,976 | 43,646,976 |
| 首步手工CE差 | 0 | 0 |
| 改变的LoRA张量 | 504 | 504 |
| 重载最大logit差 | 0 | 0 |
| 平均step秒数 | 1.419 | 1.409 |
| 训练+保存重载秒数 | 478.89 | 474.17 |
| allocated峰值GiB | 32.14 | 29.37 |
| reserved峰值GiB | 81.73 | 56.46 |
| nvidia-smi采样最大使用GiB | 82.39 | 57.12 |
| 训练采样平均GPU利用率 | 88.83% | 89.60% |

只监督assistant target，user/tool/context的labels=-100。冻结参数抽样未变，不是逐字节扫描全部冻结权重；重载greedy IDs也一致。每epoch平均样本CE分别0.3145→0.1457、0.2881→0.1186；两组数据不同，更低CE不能替代Agent比较。

实测为96GB卡；S1 reserved峰值超过80GiB，不能声称该配置已经在A80080GB验证。allocated/reserved/设备采样不是同一口径。SFT评估使用未合并adapter，BASE没有adapter，且输出长度不同；延迟差同时包含部署开销和行为差异。

五个脚本合计0.71064 GPU-hours（约42.64分钟）。从容器PID1启动估计到请求关机约2.40小时，包含下载/安装/间隔/回收；真实账单起止与当前单价未知，人民币费用unavailable，不能沿用9月旧价或记作0。若当前单价为P元/小时，纯评估每次官方成功成本分别0.004268P、0.005002P、0.006267P元，不含训练摊销、恢复和存储。

## 恢复、无效记录和证据

用户新租实例初始盘为空。通过GitHub固定提交恢复81个文件；16.38GB权重经官方Qwen镜像传输，但逐个匹配原HF SHA256。[Qwen官方仓库](https://github.com/QwenLM/Qwen3)、[官方ModelScope模型](https://modelscope.cn/models/Qwen/Qwen3-8B)。未更改模型revision或算法代码。

保留HF慢速中断、一次ModelScope断点重连、Windows默认GBK读取失败后显式UTF8修正等操作记录；模型run无效数0。两个adapter约350MB保存于本地checkpoints，未进Git。实验归档及所有成员哈希均验证。[AutoDL官方关机方式](https://www.autodl.com/docs/save_money/)已执行，回执明确控制台计费状态未独立确认。

| 证据 | 路径 |
|---|---|
| Base轨迹/指标/身份 | experiments/SFT-EVAL-BASE-20261010-001/ |
| S1训练/评估 | experiments/SFT-S1-20261010-001/；experiments/SFT-EVAL-S1-20261010-001/ |
| S2训练/评估 | experiments/SFT-S2-20261010-001/；experiments/SFT-EVAL-S2-20261010-001/ |
| 配对统计/诊断/案例 | reports/sft-comparison-20261010/ |
| 归档/操作证据/关机回执 | evidence/sft-execution-20261010/ |
| 新主机与模型恢复 | evidence/sft-recovery-20261010/ |

本轮修改为恢复辅助脚本、离线汇总脚本、运行证据和项目文档；冻结训练/评估算法未改。下一路线应先完成残余语义failure审核，再决定training-only DPO pair准备及bounded probe；或先设计真正sealed的泛化资格验证。没有自动启动下一阶段。


补充诊断盲点：S2 task363/seed42重复创建同一图表直到轮数上限，但每次都会修改analytics._plots_data，所以原same-state循环检测始终为false。已人工确认该例的重复行动；“state changed”不等于“任务有进展”。原始自动指标保留，不把候选循环数0写成真实循环率0，也不在本轮中途修改harness。
