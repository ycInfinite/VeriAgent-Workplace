# 2026-10-12 DPO探针学习交接

今天回答的问题：**DPO到底能不能真实更新我们的Agent参数，而且在单卡上跑得起？** 本次答案是可以；还没回答“能否提高任务成功率”。

开始前：12对数据准入、25项本地检查通过，但本地没有Torch，真实梯度/显存/重载未测。你提供新克隆PRO6000后，完成了真实8步探针。

## 实际做了什么

GitHub固定commit24fe95f部署→原S1 adapter及Base权重核验→Torch梯度检查→75轮HF编码核验→固定S1 reference算分→8次LoRA更新→保存/重载→回收证据和新adapter。旧S1与其他SFT权重保持原样。本次没有teacher API、新Agent rollout、正式DPO对照或online RL。

唯一干预是固定8对DPO更新。控制：同Base+S1、seed42、beta0.1、lr5e-6、context8192、dropout0、完整assistant监督。新主机driver595.71.05；不能用此次时延直接解释与历史其他驱动的差异。

## 原始事实

- 8/8次真实更新完成，504个LoRA tensor改变，冻结参数抽样门槛通过。
- Torch整图与分轮重算梯度差0；真实policy两遍logp差0。
- 首步policy等于reference，margin0、loss=log(2)。
- 保存重载logit差0、固定greedy IDs一致。
- reference17.95秒，平均pair update9.64秒，总脚本131.20秒=0.03644GPUh。
- allocated峰值20.74GiB，reserved31.28GiB，设备采样31.97GiB；GPU利用率121样本均值87.89%。
- 无无效模型run。PATH和本地解包路径检查问题已保留，非模型失败；部署/回收占用另算，单价未知。

## 今晚只学三个机制

**1. reference是刻度。** 它固定在训练开始的S1，不随policy更新。先把它对两分支的logp算出来就能省掉第二份常驻模型；不能在后续步骤重新用已更新policy替代reference。

**2. DPO学的是相对偏好。** 第8对中chosen logp由−102.482变成−103.044，实际上更低；rejected由−54.035变成−59.370，下降更多，所以相对margin仍为正。DPO loss改善不是“每个好答案的概率都提高”。每步还是不同题，不能把8点loss当成同题学习曲线。

**3. 训练完整性和能力是两张成绩单。** 8步/梯度/重载通过说明程序确实做对了更新。要知道Agent有没有改善，仍须让它生成新tool calls、真实执行、跑固定评估，再比chosen-only SFT。当前没有任务成功率结果。

## 代表性数据与固定输出

training859正例：查12月1日两页会议→选观察到的最后会议00000252→正确改名；负例：编造12345678→工具说不存在→反问用户。这里的成功/失败是已有训练数据，不是本次新policy成绩。

本次保存重载的固定readout开始生成analytics_create_plot，但只取64token，工具调用未写完；没有执行工具或verifier。这是身份检查样本，不是新成功轨迹，也不把人为64token截断计作Agent失败样本。

## 五处代码怎么串

| 文件→函数 | 输入→输出 | 作用 |
|---|---|---|
| scripts/check_dpo_torch.py→run_controls | 小张量两分支→梯度等价检查 | 先验证实现数学 |
| scripts/run_dpo_probe.py→actual_tokenizer_check | 原messages/tools→75轮ID/mask一致 | 防止训练格式错位 |
| veriagent/dpo.py→branch_score | policy+每轮完整历史→整轨迹assistant logp和 | 工具观察只作context |
| veriagent/dpo.py→pair_backward | current/reference两分支分数→loss/偏好梯度 | 逐轮重算，不攒整条轨迹图 |
| scripts/run_dpo_probe.py→main/readout | S1+固定8对→新adapter/重载证据 | optimizer.step之后保存并检查 |

所有轮的labels前缀是-100，当前完整assistant输出才计loss；累计历史assistant不会在当前轮重复算成目标。一个pair含多个轮，所以9.64秒pair update不能和1.4秒单轮SFT直接比倍数。

## 路线判断与未支持推测

支持：固定历史数据的offline DPO链路已经真实跑通，当前8对成本小。未支持：DPO改善Agent、DPO优于追加SFT、12对已足够、80GB硬件直接兼容、泛化或no-op推理改善。

下一分叉：是否进入同S1起点的chosen-only SFT versus DPO正式小对照；正式runner与预登记仍需完成。也可以另行决定采当前policy的training失败，但不能拿dev失败凑训练pair。本轮探针完成后停止，不自动扩实验。

## 五个考核问题（不给答案）

1. 首步DPO loss为什么是log(2)，它能证明什么、不能证明什么？
2. 为什么reference不能随着policy一起更新？关闭S1 adapter有什么问题？
3. 为什么chosen概率降低，相对偏好margin仍可能提高？
4. 逐轮重算如何不改变整对DPO梯度，为什么要求dropout0？
5. 想证明DPO有额外价值，为什么要同批chosen-only SFT，而不只比较旧S1？

尚未作答，不标记学习通过。

## 证据与明天入口

执行commit24fe95f5273955e153929e1d89318d8904a98b92；原始配置configs/dpo_probe_plan.json保持不改，本次用户授权记录experiments/DPO-RESUME-20261012-001/config.json。

- experiments/DPO-PROBE-20261012-001/：config/identity、weights、torch_cpu_controls、host_preflight、reference_scores、steps、adapter_changes、reload_check、result、gpu_samples。
- evidence/dpo-execution-20261012/：GitHub同步、远端原始archive、manifest、校验及关机证据。
- checkpoints/DPO-PROBE-20261012-001/adapter/：新权重，不进Git。
- reports/dpo-probe-20261012/analysis.json：事后数值/资源汇总。
- docs/DPO_PROBE_RESULT_20261012.md：完整结果和生命周期成本。

之前的DPO准备学习文件仍保留，描述的是执行前状态；本文件是随后真实实验的交接。

最终收尾：新adapter与原始证据SHA通过；官方关机已执行，SSH不可用、连接已关闭，保护取消。容器全占用估计0.31416小时（含回收等待），单价未知，平台账单未独立确认。工程事实已齐；下一阶段尚未启动。
