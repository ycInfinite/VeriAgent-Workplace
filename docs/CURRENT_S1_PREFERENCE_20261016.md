# 当前S1六对偏好对照预登记 — 2026-10-16

最终状态：六对对照已完成，证据与两份adapter已回收核验。下方八项保留执行前登记内容；实际结果见后文。

【Research Question】

Do six reviewed currentS1 failure pairs improve exposed-dev behavior beyond the same chosen-only SFT data?

【Hypothesis】

CurrentS1 errors may provide useful relative information; six pairs may be insufficient and any gain is exploratory.

【Independent Variable】

Task-mean chosen-only CE versus whole-trajectory sum-logp DPO, both from exact originalS1.

【Controlled Variables】

Same six tasks/chosen exposure/order,oneepoch6taskupdates,lr5e-6,seed42,beta0.1,8192,originalS1,host/driver;fixeddev24x42/43.

【Metrics】

Primary paired nonempty DPO minus chosenSFT success;overall/empty, fresh semantic audit,tokens/VRAM/latency/GPUh;single exposed-dev experiment.

【Evidence Gate】

Six reward-gap data hashes,originalS1,train/dev isolation,HF all39 turns,Torch gradient controls,6finiteupdates,save/reload,144valid evals.

【Cost Bound】

One already-running userPRO6000;each script1800s and process pipeline<=9000s;engineering estimate0.55-0.80scriptGPUh plus setup/retrieval;rateunknown;KEEP_INSTANCE_ON, no poweroffguard.

【Failure Branch】

Stop pipeline on formal integrity/infrastructure failure;preserve partial output;no retries,extra data,seeds,tuning or automatic nextstage.

固定任务顺序：[1000, 51, 349, 1076, 1194, 473]。两组各6次更新，原S1同机新baseline与两组最终adapter各48条dev评估；不从中选checkpoint。相同chosen数据暴露和更新次数，不是相同tokens/FLOPs；不与旧12对做负例来源的单变量因果比较。

六对包含两个正确不操作示范（1000/51），但只覆盖analytics/calendar。702另存，不参加这轮训练。当前开发集已经多次暴露，所有结论仅限探索性机制检查。

13CPU准备检查通过，39个canonical assistant轮次；6对最大序列5885。实际HF模板/mask、Torch梯度、S1权重、训练更新/保存重载都在远端执行前后检查。原12对配置/入口、原S1、旧adapter不修改。

GitHub只新增同步五个白名单文件；比较汇总和准备脚本仅本地。流水线每个模型脚本1800秒，进程总上限9000秒，任一步正式失败停止，保留证据，不自动重试。用户要求保留机器开机，没有关机保护。当前时价未知，RMB留null，报告继续占用。

来源：experiments/CURPREF-PREP-20261016-001/；configs/current_s1_preference_plan.json；执行commit在远端identity中记录。

## 实际执行结果

执行commit：`6b7898e9c9ca4d82f95e00bf40b1ec0ecbf528f7`。单PRO6000 Blackwell96GB/driver595.71.05。两个训练臂分别从原S1重新开始，一遍六题、各6更新；没有用chosen-only新权重初始化DPO。702同奖励pair未使用，没有新教师API或新的training采集，没有online RL。

| 模型 | 非空reference | 空reference | 总体 |
|---|---:|---:|---:|
| 原S1，同机基线 | 30/40 | 5/8 | 35/48（72.92%） |
| S1 + chosen-only SFT | 30/40 | 6/8 | 36/48（75.00%） |
| S1 + DPO | 31/40 | 3/8 | 34/48（70.83%） |

三组各48有效、0基础设施无效，共144条。每组是24任务×两个seed，不能当作48个独立任务。SFT414/seed42六轮耗尽，仍是有效policy-budget失败，计入分母；不是基础设施超时。其他143条为assistant_final。partial progress不折算额外成功奖励。

预登记主比较 DPO−chosen-only SFT：非空 **+2.5pp，task-cluster bootstrap95%CI[0,+7.5]pp**。仅684/seed42改变了非空成败，不能宣称稳定方法优势。总体−4.17pp，CI[−12.5,+4.17]pp；空任务−37.5pp，CI[−50,−12.5]pp，但空任务只有4个task clusters，这个离散bootstrap区间不是跨任务/跨seed泛化保证。

SFT−原S1总体+2.08pp，CI[0,+6.25]pp；非空逐task-seed结果完全相同，CI[0,0]是样本中差值全零，不是总体等价证明。本次原S1的48个可见messages和成败均与Oct12同配置S1一致；重复基线不增加独立样本量。

## 行为变化与语义核验

- **684/seed42，DPO改善**：基线与SFT找到四名客户后只列出结果；DPO纠正最初的字面OR查询，查询Akira邮箱并实际把49/162/96/198四个观察到的ID重新分配。另一seed仍失败，所以不是稳定学会了该类任务。
- **122/seed43，SFT和DPO官方改善**：不再画图，拿到reward1，但仍把周一Nov27当星期二，并检查了无关的total visits；日期推理没有修复。
- **122/seed42，DPO退步**：明确说条件不满足，仍以“展示趋势”为由画图。
- **12/seed42，DPO退步**：观察In Progress为空，仍擅自把In Review的113/157移到Backlog。
- **709/seed43，DPO退步**：相对Nov30，把过去Nov14说成未来并删除该会议。

全部24条空任务、9条DPO非空官方失败、三组684/seed42、SFT唯一轮限失败414/seed42，共37/144条完整可见轨迹做了新鲜语义复核。由Codex单人审核，无独立人工复核；不是144条全语义率。

| 空任务诊断（分母均8轨迹，4任务簇） | 原S1 | chosen-only SFT | DPO |
|---|---:|---:|---:|
| 官方成功 | 5 | 6 | 3 |
| 有正确证据支持、完成且不修改状态 | 4 | 4 | 2 |
| 整条可见轨迹无已发现语义错误 | 2 | 2 | 1 |

完整轨迹计数错误等也会使whole-clean不通过。例如Leila共有20任务，模型反复说成12/17/18。385三组都把6周当一个月且先画图后判断；实际所查30天social/direct为69/182，各类编造求和不能当成功推理。

DPO剩余9个非空官方失败：414两seed选择Completed任务；363两seed日期窗错误；1112两seed用错月份并转发了Leila的邮件；684/seed43 OR筛选/分页/不执行；952两seed则保留“当天到期是否overdue”的reference边界疑点，不把这两条简单定为模型错。SFT414/seed42能识别Completed不应选择，却对已有完整结果逐日重复查询，最终耗尽六轮未执行。相同reward0不等于相同failure。

## 更新完整性与资源

14项本地准备控制通过；实际Torch七项检查通过，DPO和chosen-only CE的逐轮梯度与整图对照差均为0。两个训练臂各检查39个真实HF模板/IDs/labels；只监督完整assistant目标，观察作为context。每臂6真实更新、504个LoRA张量变化，冻结参数抽样和原S1文件保持，adapter保存重载logit差0。DPO首步margin0/loss=ln2，重算logp差0，固定reference cache未变。

| 训练 | 总脚本秒 | 平均更新秒 | allocated/reserved峰值GiB | 设备采样峰值GiB |
|---|---:|---:|---:|---:|
| chosen-only SFT | 56.546 | 4.168 | 21.071 / 34.941 | 35.628 |
| DPO | 122.121 | 11.791 | 21.128 / 34.668 | 35.354 |

DPO固定reference前向16.466秒。模型仍8B、原LoRA，无额外框架。两臂匹配任务、chosen暴露和更新次数，**没有匹配总tokens/FLOPs/GPU-time**。39个canonical轮次、184485 processed tokens是一次数据表示，不是DPO多次前向的全部GPU计算量。chosen targets1774，rejected2858；六步每步不同任务，loss序列不是固定集前后学习曲线。

| Eval | 工具可执行 | 平均工具步 | 输入/输出tokens | 平均轨迹秒 |
|---|---:|---:|---:|---:|
| S1 | 159/161 | 3.354 | 775142 / 15603 | 11.027 |
| chosen-only SFT | 163/165 | 3.438 | 783097 / 15798 | 11.366 |
| DPO | 168/170 | 3.542 | 792247 / 16961 | 12.255 |

未知工具名均0；schema-invalid各2次；identifier自动未grounded候选分别0/76、0/80、0/81；相同状态重复调用候选3/3/1，自动retry-loop0/0/0。这些不是完整人工wrong-tool/wrong-argument/identifier/redundancy语义率。自动premature候选13/11/14只是reward0且assistant_final，不能直接报告为真正提前终止率。

三组eval分别550.601/567.942/610.575秒。五脚本合计 **0.529940 GPU小时，约31.8分钟**。本矩阵首次资源观察至备份结束约0.739890小时；容器估计启动至备份结束1.406065小时，后者还包含此前25题采集和闲置。三个口径不可相加。GPU实际单价未知，RMB=null，存储另计，不冒用旧实例价格。若时价p元/小时，则本矩阵观察窗口约0.739890p元，非账单。

推理GPUh/官方成功：S1=.00436985，SFT=.00438226，DPO=.00498836；不含训练/数据采集/部署/闲置，也不是语义合格成功分母。大adapter传输在全部GPU运行结束后进行，较小的已完成结果下载与后续运行部分重叠；时延不作纯算法因果解释。96GB当前范围实测，不构成80GB实机资格。

## 假设、故障与下一分叉

观察到一个非空任务seed改善，但DPO总体低于chosen-only SFT，并在不该操作时出现更多动作。**本轮没有建立DPO整体优于chosen-only SFT的证据。** 也不能宣称DPO普遍无效、当前策略负例无用或模型已饱和。只有6对、两个业务域、1774 chosen targets、单训练seed、已经暴露的dev，统计和覆盖都很有限。旧12对与新6对同时改变任务和数量，不能当作“旧Base负例 vs 当前S1负例”的单变量实验。

`CURPREF-BOOT-20261016-001`保留一次CPU入口导入故障：6dd6172引用远端未部署的common.py，在任何模型运行前退出。修复为stdlib Path定位后，独立导入和14项控制通过，再以6b7898e执行所有正式ID一次；没有重跑正式实验。该故障不计Agent失败，但占用时间没有抹去。

下一阶段建议先冻结新增training任务批次，扩大当前策略偏好数据的行为覆盖、审核条件约束；不在这6对上直接加epoch或反复调beta。若更重视完整项目收尾，可先设计未见组合/最终held-out评估资格。两条路线均需新登记和用户选择，本轮不自动开展。RL未启动，sealed final/BFCL/combination仍未测。

## 保存与机器状态

65个原始归档成员、两份adapter共6文件全部SHA256核验。原S1和旧12对/旧adapter未修改。保存时pipeline已退出，nvidia-smi无计算进程、显存0；SSH已关闭。**按照用户要求保留实例开机，没有关机命令、模式切换或关机guard，后续继续计费。**

- 训练：`experiments/CURPREF-CHOSEN-SFT-20261016-001/`、`experiments/CURPREF-DPO-20261016-001/`。
- 评估：`experiments/CURPREF-EVAL-{S1,CHOSEN_SFT,DPO}-20261016-001/`。
- 原始归档/哈希/资源收据：`evidence/current-preference-execution-20261016/`。
- 配对统计/逐案语义记录：`reports/current-preference-20261016/`。
- 粗颗粒学习交接：`docs/daily/2026-10-16-current-preference-learning-handoff.md`。

新增配置、独立六对runner/pipeline、五文件GitHub白名单及本地统计/显示/校验入口；原训练算法模块`veriagent/dpo.py`和旧12对入口未改。执行期间未修改部署文件。最终停止新实验。
