# 2026-10-12：同批chosen继续SFT vs DPO，完整结果

**本轮未观察到DPO的额外收益。** 主指标非空任务三组均30/40，且逐task/seed通过与失败标签完全相同；总体S1/追加SFT/DPO为35/48、35/48、33/48。DPO新增了空任务上的不必要修改，但也有一例日期解释改善。不能把此结果扩大为“DPO普遍无效”。

两组各12次真实更新、三组144条有效评估全部完成，0条模型评估infra-invalid；两个训练前CPU导入失败单独保留。新adapter和所有原始证据已SHA校验回收。官方关机后AutoDL刷新确认D62与D47均已关机，两个SSH会话已关闭，保护已取消，旧监控仍暂停。本阶段结束，不自动加epoch、采样或进入RL。

## 实验问题与预登记

| 字段 | 本轮冻结定义 |
|---|---|
| Research Question | DPO是否比同批chosen继续SFT有额外行为收益？ |
| Hypothesis | rejected相对信息可能改善行为；12对旧Base负例可能已过于简单。 |
| Independent Variable | task-mean chosen CE vs整轨迹sum-logp DPO。 |
| Controlled Variables | 原S1起点、同12题/顺序、12updates、一遍chosen、lr5e-6、seed42、8K、原LoRA、同机dev24×42/43。 |
| Metrics | 主指标非空任务DPO−CHOSEN_SFT；总体/空任务、语义审核、调用/tokens/延迟/显存/GPUh/费用。 |
| Evidence Gate | 数据/S1身份、7项真实Torch控制、75轮HF校验、有限梯度/更新/重载、每组48有效评估。 |
| Cost Bound | 已有单96GB卡；每个训练/评估<=30min；事前估计0.55–0.85脚本GPUh+部署回收；4h保护；6.98元/h。 |
| Failure Branch | 正式模型运行失败即保留停止，不自动重跑或调整数据/超参/seed/context。 |

计划 `configs/preference_comparison_plan.json`；实际执行commit **c5cad4299236cb1f0108392efb20ccd08dafdf61**。两个训练臂均重新加载原 `SFT-S1-20261010-001`，不接8步DPO probe权重。模型Qwen3-8B revision b968826d9c46dd6066d109eabc6255188de91218，数据revision c86a908379e0a361a573c395e175d3c1aa128e6c。原SFT/probe代码、数据、adapter不覆盖。

训练采用12对已审training数据；chosen来自DeepSeek，rejected来自旧pre-SFT Base；与S1/S2训练task IDs无交集。五业务域覆盖，但没有正确no-op专门偏好对，11/12对chosen更长，存在来源/风格/长度混杂。全部assistant轮次保留，工具观察仅作context，不编造/替换观察、不截断。

两臂匹配任务、chosen曝光和任务级更新次数，**不是严格等tokens/FLOPs/GPU预算**。SFT每task的NLL除以该task全部target数，逐轮累积后更新一次；DPO额外处理rejected/reference。固定终点，无dev checkpoint selection。评估使用原B1、non-thinking、8192context、6轮、每次最多768生成tokens/整轨迹2048、temperature0.2、top_p1。

新增同机S1评估控制主机/驱动差异，未重跑S1训练。GPU为PRO6000 Blackwell96GB、driver595.71.05；Torch2.8.0+cu128、Transformers4.56.2、PEFT0.17.1、Accelerate1.10.1。所有三组在同一D62会话运行。

## 原始成绩与统计

| 条件 | 总体成功/48 | 非空/40 | 空reference/8 |
|---|---:|---:|---:|
| S1同机基线 | 35（72.92%） | 30（75%） | 5（62.5%） |
| S1＋chosen-only SFT | 35（72.92%） | 30（75%） | 5（62.5%） |
| S1＋DPO | 33（68.75%） | 30（75%） | 3（37.5%） |

每组48 valid/0 infra-invalid；共24个任务、两个seed，并非48独立任务。配对bootstrap按task簇抽样、两个seed一同保留，10,000次，固定统计seed20260917。

| 对比 | 总体差值/95%区间(pp) | 非空差值/区间(pp) | 空差值/区间(pp) |
|---|---|---|---|
| DPO−追加SFT（主比较） | −4.17 [−10.42,0] | 0 [0,0] | −25 [−50,0] |
| 追加SFT−S1 | 0 [−6.25,+6.25] | 0 [0,0] | 0 [−37.5,+37.5] |
| DPO−S1 | −4.17 [−12.5,0] | 0 [0,0] | −25 [−75,0] |

非空[0,0]来自这批任务观测到的完全一致通过/失败标签，不是总体等价证明。空任务只有4个簇，区间包含0；单训练seed、反复使用的dev、12对数据，不能宣布总体显著优劣或泛化。sealed final/BFCL/composition没有打开。

逐条二元结果变化仅出现在空任务：

- 追加SFT对S1：task122 seed43由0→1，task12 seed43由1→0；一得一失抵消。
- DPO对S1：task12两个seed均由1→0；其他二元结果不变。
- DPO对追加SFT：task12 seed42及task122 seed43均由1→0。

## 语义审核：不能只读总分

新鲜审核三组共24条空任务的生成决策和关键观察，无独立人工裁决；统计/列表观察以精确字段和聚合检查，不声称所有144条均完成完整语义标注。标准与之前空任务诊断保持一致，作为事后指标独立于官方reward。所有dev记录不可训练。

| 每组8条空任务 | S1 | 追加SFT | DPO |
|---|---:|---:|---:|
| 官方成功 | 5 | 5 | 3 |
| 完成回应且关键不修改判断有正确证据 | 4 | 3 | 3 |
| 上述通过且无观察到的错误/冗余 | 2 | 1 | 2 |

关键案例：

- **task12，条件被擅自扩大。** 用户只要求移走Leila的In Progress。查询返回空后，追加SFT seed43和DPO两个seed改移4条In Review任务。ID都来自观察，仍是错误对象/条件决策，不能归成ID hallucination。
- **task122，官方成功内有质量差异。** S1/追加SFT seed42把周二写成11月27日；DPO seed42查询到11月28日并正确比较8→4、下降50%，解释改善。但DPO seed43仍用错误星期锚，并把“今天”条件换成“区间某天最高”，错误作图。
- **task385，先行动后检查。** 三组仍在判断social是否高于direct之前作图，并把六周缩为11月。DPO seed42没有查计数就编造1250/1100；seed43查询后仍给出错误统计。官方状态验证与自然语言正确性需分开。
- **task709。** 完整事件列表全在过去，正确不删除。追加SFT/DPO seed42又作一次未来筛选，正确但在完整证据下冗余，因此strict whole-clean不通过；seed43通过。

DPO另有10条非空官方失败（5题×两个seed）已复核决定性证据：414选已Completed的最早到期任务；684漏分页或只列出客户未转交；363四周时间窗错误；1112把上周定位到十月，seed43还转发他人邮件；952未移动“当天到期”的第三条，保留官方reference与“逾期”边界解释差异，不能一概归因模型错误。414的“urgent”目标语义也需要与状态要求一起解释，不改写官方分数。

## 行为与效率指标的分母

| 指标 | S1 | 追加SFT | DPO |
|---|---:|---:|---:|
| executable/全部调用尝试（含解析失败） | 159/161 | 161/164 | 166/168 |
| schema错误/已解析调用 | 2/161 | 2/163 | 2/168 |
| 解析失败次数 | 0 | 1 | 0 |
| 未知工具名次数 | 0 | 0 | 0 |
| 平均tool steps/48轨迹 | 3.354 | 3.396 | 3.500 |
| input tokens累计 | 775142 | 779922 | 784671 |
| output tokens累计 | 15603 | 16338 | 17285 |
| 平均轨迹秒 | 12.607 | 13.697 | 14.106 |

Executable不等于业务正确；未知名不等于所有Wrong Tool，schema错误不等于全部Wrong Argument。自动grounding候选三组均0，不证明grounding已全面解决。重复候选3/4/1、premature候选13/11/14只作线索；完整语义错误率未建立。二元成功不按partial折算，部分状态修改留在events。生成未完成/轮数用尽保留为有效模型轨迹，不因失败删除。

评估采用未合并LoRA；两组adapter回收与其eval及部分DPO训练并行，可能贡献少量主机I/O耗时。时延是实测walltime，不作纯算法速度因果结论。

## 更新完整性与成本

两组各12步、504个LoRA tensor变化、43,646,976可训练参数门槛通过；冻结参数抽样/原S1文件哈希不变，重载固定logit差0、greedy IDs一致。真实Torch7控制通过，两种逐轮梯度对照差0；75轮实际HF校验通过。DPO首margin0、两遍logp差0。不同题目的逐步loss不是同题学习曲线，固定64token重载输出不是Agent评测。

| 训练资源 | 追加SFT | DPO |
|---|---:|---:|
| 平均task/pair更新秒 | 4.2958 | 10.6081 |
| reference算分秒 | 不执行 | 29.3623 |
| train含预检/保存重载秒 | 87.2991 | 191.6829 |
| allocated峰值GiB | 20.7389 | 20.7389 |
| reserved峰值GiB | 54.4082 | 35.3770 |
| 设备采样used峰值GiB | 55.0947 | 36.0635 |
| GPU利用率采样均值 | 63.525% | 83.028% |
| 脚本训练费用估计 | 0.1693元 | 0.3717元 |

SFT processed174097/targets3258，38数据forward；DPO单pass336711/5143，reference+评分+反传重算3pass=1010133 processed/15429目标曝光、225数据forward；不含内部activation checkpoint重算和固定readout，不能等同FLOPs。原SFT result的reference_seconds约10微秒只是空循环计时，无reference模型打分。显存reserved受执行顺序/缓存影响，不能由这张表推论DPO普遍省显存。

五个脚本合计 **0.63621145 GPUh，约4.4408元**。容器启动估计1791772105.5877585至关机请求1791775786.5142062，**1.02247957小时，约7.1369元**（6.98元/h）。包含部署、两次CPU故障处理、等待与回收；是嵌套成本，不能两数相加。当前容器开始晚于上一probe关机请求，本轮未由agent租用或开机；价格来自本次刷新的AutoDL详情，不倒改历史未知价格。金额非账单，存储与最终计费边界未审核。

推理费用/官方成功约S1 0.03487元、追加SFT 0.03775元、DPO 0.04115元，仅各自eval脚本，不含训练/部署，也不以语义合格数作分母。

## 故障和证据保全

880ab17首次独立Torch入口未建立项目import路径；df1680c的修复依赖本地common.py，但该文件不在远端最小白名单。两次均在模型加载前停止，0rollout/0update。永久记录 `PREF-HOST-PREFLIGHT-20261012-001/002` 与first_launch/second_launch日志。最终改成标准库自包含路径初始化，隔离8文件依赖检查通过，c5cad42的真实7项Torch控制通过。没有重试已开始的正式模型run。

五个正式run均一次完成：

1. PREF-EVAL-S1-20261012-001
2. PREF-CHOSEN-SFT-20261012-001
3. PREF-EVAL-CHOSEN_SFT-20261012-001
4. PREF-DPO-20261012-001
5. PREF-EVAL-DPO-20261012-001

原始config/identity、steps或trajectories、GPU采样、result、reference/reload/adapter_manifest保存在experiments同名目录。各run归档共48成员、操作归档31成员均SHA通过；两个新adapter共6文件在忽略目录checkpoints/，哈希与远端一致，不进Git。

- `reports/preference-comparison-20261012/paired_results.json`：三种配对对比与区间。
- 同目录 `S1_empty_review.json`、`CHOSEN_SFT_empty_review.json`、`DPO_empty_review.json`：24条新鲜语义审核。
- `DPO_nonempty_failures.json`：10条非空失败决定性证据。
- `training_resources.json`、`resources.json`：资源、token与完整成本范围。
- `evidence/preference-execution-20261012/`：GitHub同步、两个失败启动、五个原始archive、operations、adapter校验、shutdown收据。

## 路线结论

训练实现完整性获得支持；本轮“DPO提供额外任务收益”未获支持。没有证明DPO普遍无效，也没有证明SFT已经饱和。数据少、旧Base负例、相同偏好来源/长度与缺no-op对都是限制。

一个值得下阶段检验的假设是：负样本已经落后于当前S1的错误分布。原12对大量针对旧Base乱填ID，而当前baseline自动grounding候选为0，残留失败更多与日期、分页、状态条件、该做却没做相关；这只是线索，不是充分因果解释。

建议停止在这12对上堆epoch或自动上RL。下一路线优先设计当前S1在training池的小规模失败采集，用同题已审教师轨迹构建更有信息的偏好对，同时覆盖正确不修改与错误操作。需另行冻结范围并由用户决定；本轮未采新数据、未进行该阶段，也未用dev失败作训练数据。
