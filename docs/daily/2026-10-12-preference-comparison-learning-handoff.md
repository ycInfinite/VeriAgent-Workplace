# 2026-10-12 学习交接：DPO没有自动带来提升

今天的核心问题：**学了同一批好轨迹后，再利用坏轨迹，是否比只做SFT更有效？** 本次小对照没有观察到额外收益，这也是有效研究结果。

## 开始前与实际执行

开始前：SFT主对照及8步DPO完整性探针完成；12对偏好数据已审，正式效果对照尚未跑。

今天：两组都从原S1重新开始，第一组只用同批chosen继续SFT，第二组用chosen/rejected做DPO，各12次task级更新。另做同机S1基线；三个模型各dev24×两个seed，共144条有效轨迹。保存两组新adapter、SHA校验后关机，AutoDL刷新已确认D62和D47都OFF。没新采teacher、没online RL、没打开final/BFCL。

控制：同12题、顺序、chosen曝光、原S1、LoRA、lr5e-6、seed42、8K；DPO beta.1。唯一研究变量是追加训练目标；DPO额外算rejected/reference，所以不是严格等算力。

## 原始成绩

| 条件 | 全部/48 | 非空/40 | 空reference/8 |
|---|---:|---:|---:|
| S1 | 35 | 30 | 5 |
| S1＋chosen-only SFT | 35 | 30 | 5 |
| S1＋DPO | 33 | 30 | 3 |

主指标DPO−追加SFT在非空任务上为0pp，三组40条非空通过/失败标签完全相同。按任务簇bootstrap得到[0,0]是这批观测没有差值变化，不能推出所有未来任务等价。总体DPO−追加SFT为−4.17pp，区间[-10.42,0]，只有24任务/4空任务簇，不能宣布普遍优劣。

追加SFT总分没变，但task122 seed43由失败变成功、task12 seed43由成功变失败，抵消了。DPO对原S1的两条新增官方失败都是task12的两个seed。

## 代表性成功和失败

正确改善：task122 seed42，DPO正确把周二定位到11月28日，比较8→4是下降50%，有依据地不画图。S1/追加SFT虽也不画图，却把周二写成11月27日。因此同样reward1，解释质量不同。

明显回归：task12只让移动Leila的In Progress。查询为空后，DPO两个seed都擅自改移4个In Review任务；追加SFT seed43也如此。ID来自真实观察，但操作对象条件错了，不应叫“幻觉ID”。

其他失败：DPO仍会漏客户第二页、只列出却不转交、把四周写成五周/五天、把上周写成十月。task952对“当天到期是否逾期”与官方reference有边界解释差异，保留官方失败但不能简单说全是模型错。

新鲜审核24条空任务：S1/追加SFT/DPO有依据完成不修改分别4/3/3，整条严格干净2/1/2；无独立人工复核。没有把144条都冒充完整语义审核。

## 粗颗粒理解两个训练目标

SFT只提高chosen的概率；本轮按每个task所有目标token平均：

```python
# 实际训练循环的核心
for ex in pair['chosen']['encoded_turns']:
    nll = -turn_logp(model, ex) / pair['chosen']['target_tokens']
    nll.backward()
optimizer.step()  # 一整道题所有assistant轮次后更新一次
```

DPO用相对初始S1的好坏分数差：

```python
# 教学简化式，实际实现见veriagent/dpo.py
margin = (policy_chosen - policy_rejected) - (reference_chosen - reference_rejected)
loss = -log_sigmoid(0.1 * margin)
```

两者都只对完整assistant目标计分，User/Tool observations的labels=-100。观察仍然参与上下文并影响梯度，只是不被直接当作要预测的监督标签。DPO不是简单“把失败答案换成成功答案再SFT”。

## 为什么没提升仍然有价值

今天支持的是：两组真实更新与评估完整，当前12对没有提供额外任务收益。不能推出DPO普遍无效，也不能说SFT饱和。

值得检验的下一假设：我们用的是旧Base失败，大量是乱填ID；S1可能已经学会这些。当前S1自动grounding候选为0，剩余失败更多是时间、分页、状态条件。负样本即使真实且明显更差，也未必能教会当前模型尚不会的东西。这个解释有线索，但还不是因果结论。

因此，下一步优先考虑当前S1在training池的失败数据，而不是直接给这12对加很多epoch。还要覆盖正确不操作与错误修改。dev只分析，不拿来训练；新采样需另行冻结范围，今天没开始。

## 代码学习地图

| 文件→函数 | 输入→输出 | 在pipeline中做什么 |
|---|---|---|
| scripts/check_preference_torch.py→run_controls | 小张量两目标→7个梯度/mask检查 | 模型加载前验证数学实现 |
| veriagent/dpo.py→turn_logp/pair_backward | 自己分支的完整历史→分数/偏好梯度 | 工具观察作context，不拼错分支 |
| scripts/run_preference_comparison.py→main | 固定S1+12pair+condition→新adapter | 两臂各自12步，不接probe权重 |
| scripts/evaluate_preference_comparison.py→main | 同dev24/seed+三个固定policy→轨迹/reward | 真实工具与状态验证 |
| scripts/compare_preference_evaluations.py→main | 同task/seed成绩→配对差与区间 | 任务簇抽样，不把seed当独立题 |

两组各504个LoRA tensor变化，保存重载logit差0；DPO首margin0、两遍logp差0。loss变化不是Agent成功率变化。

## 成本和故障事实

五脚本合计0.63621GPUh，按AutoDL观察6.98元/h约4.44元；含部署/等待/回收的实例占用估计1.02248小时、约7.14元，非账单且两数不能相加。DPO平均每pair步10.61秒，追加SFT每task步4.30秒；DPO需要更多forward。两组权重下载和部分训练/评估重叠，时延含可能的I/O影响，不拿来宣称纯算法速度。

有两次训练前CPU入口导入失败，修复自包含路径初始化后，隔离最小部署检查通过。两次都0模型/0rollout/0update，原始故障永久保留，费用计入实例时间。正式五个run均一次完成，144评估0infra-invalid。

## 今晚三个知识点

1. 数据真实、偏好正确、对当前policy有信息，是不同要求。
2. 指标总数相同可能掩盖逐题得失；官方成功可能掩盖错误解释。
3. 方法对照需要同起点/同数据控制，并明确是否真的等算力。

## 五个面试追问（不给答案）

1. 为什么DPO必须与同批chosen-only SFT比较，而不只与旧S1比较？
2. 三组非空都是30/40且区间[0,0]，能证明总体等价吗？
3. 真实旧Base失败为什么可能不是当前S1的好训练负例？
4. task12的ID完全有依据，为什么动作仍然错？如何设计相应训练对而不泄漏dev？
5. 你如何报告这次DPO没有收益的结果，而不造提升、也不过度宣称DPO无效？

尚未作答，不标记考核通过。

## 路线与证据

本阶段到此完成。下一分叉是是否设计当前S1在training池的小范围失败采集；不自动执行新采样/训练/RL或解封测试集。

实际执行commit：c5cad4299236cb1f0108392efb20ccd08dafdf61。初始880ab17和第一次修复df1680c的CPU失败不删除。

- configs/preference_comparison_plan.json：八字段、模型/data revision、顺序、两组12步与三组评估。
- experiments/PREF-EVAL-S1-20261012-001/、PREF-CHOSEN-SFT-20261012-001/、PREF-EVAL-CHOSEN_SFT-20261012-001/、PREF-DPO-20261012-001/、PREF-EVAL-DPO-20261012-001/：原始config/identity/logs/steps或trajectories/result。
- experiments/PREF-HOST-PREFLIGHT-20261012-001/002：两次CPU故障。
- reports/preference-comparison-20261012/：paired_results、三组empty_review、DPO_nonempty_failures、资源报告。
- evidence/preference-execution-20261012/：五个run archive、operations、同步/权重校验/关机收据。
- docs/PREFERENCE_COMPARISON_20261012.md：完整实验报告。

AutoDL已确认两台实例OFF，所有新权重本地SHA通过；没有GPU继续空跑。
