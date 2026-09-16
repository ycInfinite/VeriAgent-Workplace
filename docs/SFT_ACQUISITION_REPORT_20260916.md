# 2026-09-16：迁移完成，采集完成，停在数据审核

**SFT未执行，参数更新为0。** 用户选择保留原先的整条轨迹监督方案，先停在数据审核；未采纳选择正确片段的备选方案。新PRO6000和旧A800均已在AutoDL确认关机，磁盘和原始证据保留。

## 实际执行与文件

按用户要求通过“更多→跨实例拷贝数据”，只将旧A800数据盘中的 `/root/autodl-tmp/veriagent-workplace-sft-20260910` 复制到新实例数据盘。未复制或清空系统盘，未删除源数据。平台显示拷贝完成，新盘占用从0变为31.02%。

用户随后明确批准新机开机及固定采集/条件SFT。新GPU实测为 **RTX PRO6000 Blackwell Server Edition**，94.973GiB显存、compute capability12.0、driver590.44.01；Python/Torch等版本与复制venv匹配。35个部署文件、5个权重分片校验通过，BF16矩阵计算通过。

执行 `SFT-ACQUIRE-20260916-001`：固定training20、五域各4、B1通用提示、seed42，8K/6轮/2048累计输出，模型与工具版本不变。真实模型生成动作、真实工具执行，完整保存状态、观察与verifier。没有改变运行时代码或原始轨迹。

新增结果与审核在该实验目录；迁移/费用证据在 `evidence/migration/2026-09-16`，回传归档与日志在 `evidence/sft-acquisition`。状态、预算、决策、假设与每日交接同步更新。

## 原始结果

| 指标及分母 | 结果 |
|---|---:|
| 有效轨迹 / 尝试轨迹 | 20/20 |
| Infrastructure-invalid | 0/20 |
| 官方成功 / 有效轨迹 | 3/20，15% |
| 空reference任务 | 0，全部需要动作 |
| 结构可执行调用 / 调用尝试 | 47/51，92.16% |
| Schema-invalid / 调用 | 4/51 |
| 未知工具 / parse错误 | 0 / 0 |
| 平均工具步数 / 平均轨迹时间 | 2.55 / 4.006秒 |
| 累计输入 / 输出tokens | 306,647 / 3,310 |
| 采集运行时间，含加载 | 88.021秒，0.02445GPU-hours |
| Torch allocated峰值 | 16.519GiB |
| GPU采样used峰值 / 平均利用率 | 18,547MiB / 78.11%，85个样本 |
| 按6.98元/小时估算运行费用 | 0.1707元 |
| 每次官方verified success运行费用 | 约0.0569元，分母3，仅采集进程 |
| 整条轨迹SFT质量批准 | 0/3成功轨迹 |

全部轨迹在线状态与重放一致；推理前后权重采样指纹不变。19条assistant_final、1条round_limit；后者是有效模型预算内失败，不能剔除为基础设施故障。没有质量批准样本，因此每条质量批准成功的成本不可定义。

这是新training任务，不能将88秒与Day3不同dev任务的耗时直接相比，推导跨GPU加速倍数。

## 三条成功的质量审核

审核者为Codex，没有独立人工裁决。保留官方reward不变；以下是训练过程质量判断，不把状态成功改写成任务失败或infra-invalid。

| task_id | 真实过程 | 审核决定 |
|---|---|---|
| 450 | 先观察到多日engaged_users<10；第2轮生成无效`engaged_users_count`枚举，工具拒绝；第3轮改为`user_engaged`成功 | 不批准整条监督，避免把错误枚举作为正目标；图像只是模拟路径，不是PNG实物证据 |
| 1183 | ID来自观察，两次删除正确；但把“所有未来会议”搜索缩为12月，随后声称全部完成 | 完整示范暂缓：policy可见信息没有解释排除年底以后事件的依据；固定状态恰好匹配不证明范围论证可靠 |
| 707 | 第1轮编造`customer_id=12345678`；失败后搜索取得`00000046`，正确更新为Proposal | 不批准整条监督，避免把虚构ID作为正目标 |

原门槛是至少两个不同training任务、所有监督轮次都合理，当前没有通过。没有为了执行SFT而把不合格审核字段改成true。

## 假设、提案与停止决定

采集假设的官方成功数量部分达到3，但“至少两个完整高质量示范”的质量部分未获支持。模型执行链可用，并不意味着可直接训练的数据已经足够。

曾明确提出另一个目标：仅使用450的第1、3轮和707的第2、3、4轮，共2任务、5个正确决策片段、245监督tokens、22,406 processed tokens；保留原始历史，错误轮只作上下文。它会改变登记的监督单位，所以只保存为提案，未执行。

用户决定：**保持原方案，先停在数据审核。** 因此未采用选择性监督，没有新采样、换题、改prompt/模型/context，也没有创建或执行SFT probe run。下一步需要另行决定完整高质量轨迹来源；当前不自动推进。

## 停机与费用

开机确认框显示6.98元/小时。采集本身约0.17元。开机确认前至确认关机后的保守观察窗口约16.82分钟，按小时价线性换算约1.96元；包含少量未运行时间，不是实际账单或账单上限。未查看结算明细，不含其他时段/独立存储。两种费用范围不能相加。

开机确认完成前的一次SSH公钥读取因banner不可用失败，已保留为preflight attempt，未传密码，不计入模型invalid。关机后SSH断连，随后浏览器刷新确认两台均已关机。

## 证据身份与路径

- 执行commit：`bc5aa55c3b97174822893c789b236cf5e43fcaf3`，先通过GitHub固定ref同步，再跨实例迁移。
- 模型：`b968826d9c46dd6066d109eabc6255188de91218`；Gym：`83b3980b9c04379d72bbf59592d7846630f706bf`；数据：`c86a908379e0a361a573c395e175d3c1aa128e6c`。
- [配置](../experiments/SFT-ACQUIRE-20260916-001/config.json)、[身份](../experiments/SFT-ACQUIRE-20260916-001/identity.json)、[原始轨迹](../experiments/SFT-ACQUIRE-20260916-001/trajectories.jsonl)、[结果](../experiments/SFT-ACQUIRE-20260916-001/result.json)。
- [完整轨迹审核](../experiments/SFT-ACQUIRE-20260916-001/quality_review_full_trajectory.json)、[未采用提案](../experiments/SFT-ACQUIRE-20260916-001/selected_turn_proposal.json)、[用户决定](../experiments/SFT-ACQUIRE-20260916-001/route_decision.json)。
- [迁移/关机](../evidence/migration/2026-09-16/platform_copy.json)、[费用窗口](../evidence/migration/2026-09-16/lifecycle_and_cost.json)、[回传哈希](../evidence/sft-acquisition/acquisition-20260916-receipt.json)。

成功与失败20条全部保留；未触碰dev/final/BFCL或旧tau2项目。模型权重和凭据不上传GitHub；公开模拟环境的实验结果、审核与状态按用户授权同步至私有项目仓库。
