# 偏好数据覆盖扩充：固定91题 — 2026-10-16

最终状态：91题采集与偏好数据扩充完成。本轮未训练。执行代码固定ebd0880；传输器缓存修复单独提交1c752dc。以下八项为执行前登记，实际结果见后文。

【Research Question】

Can the remaining reviewed teacher pool broaden currentS1 preference coverage beyond the first six reward-gap pairs?

【Hypothesis】

Additional tasks across five domains and empty-reference conditions may yield useful currentS1 negatives;pair yield and quality are unknown.

【Independent Variable】

Expand the fixed training cohort from prior25 to91 previously uncollected tasks;no policy update.

【Controlled Variables】

Exact originalS1/B1/tools/state/modelrevision;seed42,8192context,6rounds,768percall/2048totaloutput;oneattempt/task.

【Metrics】

Valid/success counts bydomain/reference;tool validity/tokens/latency/VRAM/GPUh;pair yield and failure/tool-signature coverage.

【Evidence Gate】

Existing teacher approvalhashes;excludeS1training50 andprior25;officialtrain pool;actualHF fit;realtools/replay;fresh full pair review before admission.

【Cost Bound】

One already-running userPRO6000;91rollouts;3600sprocesslimit;estimated0.35-0.70scriptGPUh based on25-task probe;hourlypriceunknown;KEEP_INSTANCE_ON.

【Failure Branch】

Stop andpreserve infrastructure failure;holdcensored/ambiguous/badchosen;no resampling/newteacherAPI/DPOupdates/RL/test.

## 固定数据范围

全取已审教师池中未用于原S1训练50题、也未用于前25题采集的剩余91题；不是按本轮模型分数挑题。原S1、B1、seed42、8192、六轮和2048累计输出不变。

| 业务域 | 非空reference | 空reference |
|---|---:|---:|
| analytics | 13 | 17 |
| calendar | 14 | 0 |
| CRM | 16 | 1 |
| email | 9 | 0 |
| project management | 15 | 6 |

共67非空+24空，47种教师实际工具序列，教师轨迹2–5轮；这些是示范统计，不是最小依赖深度或严格泛化组合。所有91初始context在预留768输出后均可放入8192，最大初始4203；预登记时实际HF检查仍待上机；执行时91个初始context已通过，新增偏好全分支的训练侧HF检查仍未执行。

## 审核边界

全部182个teacher/S1分支机械回放。候选奖励差pair和所有最终准入same-reward pair必须完整、重新审核两分支。24个空reference的S1轨迹全审条件/克制；未重新做完整pair审核的非空reward1记录只标screened-not-admitted，不声称全部182条语义合格。没有新teacher API、没有DPO更新、没有重采或换题。

保留此前6个reward-gap和1个same-reward；新增数据分开保存，并按task_uid构建去重累计视图，不混入旧Base12对，也不改旧训练配置。

## 资源与操作记录

旧A61界面观察到OFF/freeGPU0，SSH20057不通，开机未成功；用户随后提供新33142克隆。新主机66jy6yyh5q-8afb2424，PRO6000 Blackwell96GB，driver595.58.03，与此前595.71.05不同。原S1三文件SHA和包版本一致，无GPU计算进程和匹配项目shutdown guard；没有新租/模型下载。该主机已由用户开机，继续遵守KEEP_INSTANCE_ON。

两次GitHub临时下载URL在新config处404，均发生在模型调用之前，永久保留S1-EXPAND-DEPLOY-20261016-001/002。第三次请求使用新metadata缓存键，仍校验固定commit、blob SHA、白名单和SHA256；不得把传输修复写成模型实验重跑。

当前时价未知，费用保留null；预计0.35–0.70scriptGPUh只是依据前25题的工程估计，该句为预登记时的估算；实际结果见后文。没有假定新增pair数量，不能把91个任务当91个pair。

## 实际执行与原始结果

`S1-EXPAND-ACQUIRE-20261016-001`在新主机执行一次，commit `ebd0880da7cd983f51c8059d5abc35a281c39f7b`。95个GitHub文件核验通过，仅四个新增采集文件；实际HF检查91个初始context均通过。原S1权重、B1和生成限制保持，参数requires_grad=False，参数抽样前后一致，收尾时原S1三文件SHA仍匹配。

| 指标 | 结果 / 分母 |
|---|---:|
| 有效轨迹 / infra-invalid | 91 / 0 |
| 官方成功 | 65/91（71.43%） |
| 非空reference成功 | 55/67 |
| 空reference成功 | 10/24 |
| 已解析工具调用 | 277 |
| 可执行调用 / 已解析调用 | 272/277 |
| 严格可执行率（现有实现口径） | 272/279（97.49%） |
| schema-invalid / 未知工具名 | 5 / 0 |
| 解析失败尝试 | 2 |
| identifier未grounded自动候选 | 3/113含identifier调用 |
| 相同状态重复调用候选 / 自动retry-loop | 5次 / 0轨迹 |
| assistant_final / round_limit / generation_incomplete | 87 / 2 / 2 |
| 平均工具步数 / 平均轨迹秒 | 3.044 / 12.356 |
| 累计输入 / 输出tokens | 1,397,249 / 28,873 |

严格率分母按原实现将277个解析出的调用与2个解析失败response相加；每个失败response计一个尝试，不猜其中潜在调用数。不能把这个混合口径默认为纯call-level比例。自动premature候选25只表示reward0且assistant_final，不等于25个真正提前停止错误。schema-valid和identifier-grounded也不等于业务对象选对。

4条未完整结束都是有效模型预算/格式失败，不从任务分母剔除。1036失败；811/416/329因没有改变数据库而得到reward1，但仍不完整。特别是811/329已经生成“改动全部Nia任务”的越界意图，只因多tool块截断且严格门禁没有执行，才保持空reference所需状态。不能把奖励成功理解成模型学会正确克制。没有把partial progress折算为部分成功。

这些是预选training池的采集统计，不是dev/final泛化分数；新旧批次任务分布和主机驱动不同，不能把比例差异归因于模型变化。

## 新增准入与累计数据

全部182个教师/S1分支的观察、异常、状态前后哈希、状态diff与奖励离线回放一致。完整可见语义复核覆盖36条S1（全部24空任务与12条非空失败）及28条教师，共64条；由Codex单人审核，无独立人工审核。55条非空reward1只做机械筛查，未作新语义准入，不声称182条全部人工审核。

| 类型 | 此前 | 新增 | 累计 |
|---|---:|---:|---:|
| 成功/失败 reward-gap | 6 | 23 | **29** |
| 同reward、明确语义优劣 | 1 | 3 | **4，单独保存** |

新增奖励差产率23/91=25.27%；若按所有官方失败作分母，为23/26。新增全部准入26/91=28.57%，但其中3对没有奖励差，不能混写。

| 累计29个reward-gap的业务域 | pairs |
|---|---:|
| analytics | 15 |
| calendar | 7 |
| CRM | 2 |
| email | 3 |
| project management | 2 |

奖励差数据从两个域扩到五个域，包含15个非空、14个空reference任务；22种chosen工具调用序列、16个工具名。调用序列数量不是独立技能数。analytics仍占15/29，分布并不均衡。1069与956是不同措辞，却有完全相同的非空reference动作；已在coverage.json记录。不能把所有空reference简单按`[]`合成同一个语义家族，它们条件不同。

| 数据文件类型 | chosen targets | rejected targets | processed tokens | 最长序列 |
|---|---:|---:|---:|---:|
| 新增23奖励差 | 8082 | 8751 | 662293 | 8073 |
| 累计29奖励差 | 9856 | 11609 | 846778 | 8073 |
| 新增3同奖励 | 877 | 624 | 80708 | 7040 |
| 累计4同奖励 | 1310 | 981 | 125953 | 7194 |

完整assistant工具调用和回答作为目标；user/system/tool observations作为context，labels=-100。没有截断关键上下文，没有丢掉错误前缀或改写教师。最长8073接近8192限制；这里只通过canonical CPU编码，并未做这批长序列的实际HF全分支训练预检或显存资格实验。

11个新增CPU数据控制通过：29+4唯一任务、training隔离、旧数据不变、完整终止/mask、全部182回放、审核期间85条固定组快照与最终原始数据一致。现有reward-gap loader成功读取29对，并按预期拒绝同奖励4对；后者不能悄悄混入旧训练入口。

## 暂缓和未准入项

- 1036、811、416、329：完整性门槛未过，保留有效模型失败和所有原始内容，不训练。
- 1135：教师混用“当前值”与“持续高于基准”的解释，原问题过去时条件也有歧义；暂缓，不以reward1替代判定。
- 50：教师算对engaged users的−50%，但用“下降所以不满足”跳过与session-duration增长率的比较。观察中的后者是−13.01%，当前不画图结果正确，解释却不足以作为可靠完整监督。复核修改了最初草稿判断，原草稿保留在review_revisions；没有篡改旧SFT历史记录。
- 19、727、201、665：S1有依据正确不操作，未硬造偏好；教师没有本轮重新全文复核。
- 55条非空reward1：保留为screened-not-admitted，不给未审核数据加质量标签。

24个空任务中，官方成功10/24；有依据、完整结束的正确不修改5/24（19/727/201/1080/665），整条无已发现语义问题4/24（1080错误地遗漏InReview状态）。另有408/141虽然reward1却分别比较错星期日期、漏掉大部分时间窗；3条不完整reward1不能算正确完成。

## 代表性新信号

- 1020/31/17：严格大于、小于不能把等于或更大的值混进去。
- 176：已明确算出条件不满足，仍然“顺手”画图；这是条件遵守问题。
- 368：推迟两小时应15:30→17:30，S1却改13:30。
- 973：漏掉Lead状态限制，改了Qualified/Won/Lost客户；ID有依据仍会越界。
- 689：把OR写成一个字符串，再以第一页的五个结果代表42个客户。
- 1006：邮件ID正确，收件人却捏造为sofia@atlas.com，而不是查出的sofia.santos@atlas.com。
- 30/1226：时间窗、发送者和接收者必须同时满足，工具返回成功不代表业务成功。
- 666：所有数据已观察到，却把Nov29当成早于Nov28，选错最紧急任务。
- 358：把Yuki和Carlos的同名任务、日期、状态混在一起，错误重分配；教师明确检查Backlog未来日期后不操作。

同奖励408/141/1080优化的是比较依据、时间覆盖、回答事实准确性；不是新的状态成功奖励信号。以前的702仍单独保留。

## 成本、故障与主机状态

采集脚本1152.553秒=0.32015370 GPUh。allocated17.978GiB、reserved23.127GiB；设备采样峰23.806GiB，1053个样本平均GPU利用率62.66%（含检查/加载）。182分支CPU回放29.627秒，导出5.118秒，人工审核耗时另计。

新实例容器启动估计至备份结束0.57718577h；首次项目观察至备份0.53510566h；三个时间口径不能相加。时价未知，RMB=null，非账单，存储另计。若实际时价p元/h，保存时整机占用估计0.57719p元。每新奖励差pair约0.0139197scriptGPUh；每官方成功约0.00492544scriptGPUh，都不含历史教师、人工审核、部署和闲置。采集中小快照下载与后续推理重叠，时延不是纯算法比较。

两个GitHub404故障在模型前保留；metadata缓存键修复后第三次同步通过，不是模型重试。另一个本地统计片段括号错误在执行前发生并记录，修正后重算；不计模型/正式采集无效。91条模型轨迹只采一次。

原始归档29成员全部SHA核验，旧S1三文件仍匹配，采集进程已退出、GPU无计算进程。SSH已关闭。**按用户要求保留新实例开机，没有关机/模式切换/关机guard，后续仍可能持续计费。** 新主机driver595.58.03，不同于前25题的595.71.05，该差异随数据来源保留。

## 证据与下一步

- 原始91条：`experiments/S1-EXPAND-ACQUIRE-20261016-001/`。
- 182分支回放：`experiments/S1-EXPAND-REPLAY-20261016-001/`。
- 新增/累计数据、全91条处置和11CPU控制：`experiments/S1-EXPAND-REVIEW-20261016-001/`。
- 奖励差数据入口：`configs/preference_expanded_data.json`，GPU_training_authorized=false。
- 原始归档、传输与资源收据：`evidence/preference-expansion-20261016/`。
- 人工判断、覆盖与语义诊断：`reports/preference-expansion-20261016/`。

累计29对已准备好进行下一阶段预登记，但尚未训练。下一步应先检查整批真实HF模板、8073长序列显存与固定训练预算，再设计同数据chosen-only SFT对照DPO；不能由“数据更多”直接宣布模型提升。旧6对、旧12对及旧权重均不改，不自动进入训练/RL/sealed测试。
