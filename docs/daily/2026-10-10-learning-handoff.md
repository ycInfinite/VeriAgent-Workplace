# 2026-10-10 Learning Handoff：真正完成首轮 SFT 对照

## 1. 今天回答了什么

不再只是“LoRA能否更新”：今天完成S1/S2各310次真实更新，并让三个policy在同一dev24×两seed上真实调用工具。**两种SFT都改善了开发集，尚无证据说明定向选数据优于随机选数据。**

| Policy | 全部成功 | 非空reference成功 | 空reference成功 |
|---|---:|---:|---:|
| BASE_B1 | 15/48 | 9/40 | 6/8 |
| S1随机SFT | 35/48 | 30/40 | 5/8 |
| S2定向SFT | 33/48 | 31/40 | 2/8 |

S2−S1主要指标为+2.5个百分点，按任务成簇的95%配对区间[−20,+25]个百分点，包含0。不能宣布定向策略胜出。144条模型评测无基础设施无效记录；这是开发集，不是sealed/generalization结果。

## 2. 开始前和实际执行

之前已有教师采集、137条完整轨迹审批、两组各50任务的数据准备和旧8步完整性probe，但没有正式S1/S2结果。今天你提供新租PRO6000 96GB，初始没有缓存；通过GitHub恢复固定代码和数据、核验16.38GB原模型，依次执行BASE评估→S1训练/评估→S2训练/评估。

两组都从原Base新建LoRA；旧probe没有接着训练。输入、模板、mask、实际Tokenizer、包版本、参数变化、重载检查全部通过。两个adapter约350MB已回收到本地，哈希匹配。执行官方关机后原SSH断开，端口拒绝连接；控制台计费状态未独立核验。后续整理在本地完成。

## 3. 唯一变量和控制变量

研究变量是完整轨迹选择：S1按业务域分层随机，S2按旧Base真实failure覆盖启发式选择。不是更换模型、prompt、LoRA或训练次数。

两组各50任务、每域10题、155个assistant turn样本，2epochs/310steps；r16、alpha32、lr5e-5、训练seed42。processed tokens相差−0.67%，监督tokens相差+1.99%，有16任务重叠。必须说“近似等token”。训练seed仅1个；评估seed42/43不能冒充两次独立训练。

## 4. 从数据到参数：今晚直接看这些代码

### 文件一：veriagent/teacher_data.py → CanonicalTeacherEncoder.encode

输入：此前的messages、工具schema、当前一轮assistant回答。输出：模型input_ids、labels、attention_mask及计数。下面是实际返回逻辑的核心节选：

```python
return {
    'input_ids': prefix_ids + target_ids,
    'labels': [-100] * len(prefix_ids) + target_ids,
    'attention_mask': [1] * (len(prefix_ids) + len(target_ids)),
    'prefix_tokens': len(prefix_ids),
    'supervised_tokens': len(target_ids),
    'processed_tokens': len(prefix_ids) + len(target_ids),
}
```

prefix包含system、user、此前assistant、tool observations；它们仍参与前向计算，但本样本不在这些位置计算CE。target是当前完整assistant轮，包括tool call或最终回答和EOS。`-100`是loss忽略标记，不是输入token被删除。

“整条轨迹监督”通过给每个assistant轮都创建一个样本实现。第2轮的样本里，第1轮assistant是上下文；第1轮自己的样本已经监督过它。不会只挑正确片段。长对话的prefix会在多个样本重复计算，所以processed tokens约142万，真正target只有约2.9万。

### 文件二：veriagent/sft_stage.py → validate_example / schedule

输入：编码样本与seed/epoch；输出：通过门槛的样本和冻结训练顺序。关键校验来自实际代码：

```python
require(labels[:prefix] == [-100] * prefix,
        'Context tokens must have labels=-100')
require(labels[prefix:] == ids[prefix:],
        'Assistant targets changed or selectively masked')
require(e['training_eligible'] is True
        and e['source_pool'] == 'training_candidate',
        'Nontraining input')
```

每组50个任务不等于50个训练样本：总共155个assistant轮。microbatch1且不累积梯度，因此155×2=310次optimizer更新。loader还校验原轨迹SHA、审批、任务身份、token计数和重新编码结果，防止静默换数据或混入dev。

### 文件三：scripts/run_sft_comparison.py → main

输入：冻结arm数据、Base权重、LoRA配置；输出：adapter、310步日志、身份和重载证据。下面是实际训练循环的关键节选，省略了计时和错误处理：

```python
optimizer.zero_grad(set_to_none=True)
output = model(**batch, use_cache=False)
loss = output.loss

# 只在第1步独立核对模型内部的 causal CE
labels = batch['labels'][:, 1:]
mask = labels != -100
manual = F.cross_entropy(
    output.logits[:, :-1, :].detach()[mask].float(),
    labels[mask],
)

loss.backward()
torch.nn.utils.clip_grad_norm_(
    list(trainable.values()), cfg['max_grad_norm'],
    error_if_nonfinite=True,
)
optimizer.step()
```

因果语言模型用位置t的logits预测位置t+1，所以logits去最后一位、labels去第一位。mask只保留target位置。手工CE使用detach用于核对，**真正反传的是output.loss**，不是manual。

LoRA只让43,646,976个参数可训练，Base冻结。每组504个LoRA张量改变，冻结参数抽样未变。首步只有部分LoRA张量出现非零梯度可以来自LoRA初始化，不等于断图；随后两组均观察到504个非零梯度张量。

S1/S2平均step为1.419/1.409秒；训练+保存重载为478.89/474.17秒。两组保存后重新加载，固定logits最大差0、greedy IDs一致。重载检查只证明权重身份与加载链路，不证明Agent更强。

### 文件四：scripts/evaluate_sft_comparison.py → main；scripts/run_day3.py → inference_trajectory

输入：固定dev任务、seed、Base或指定adapter。输出：模型生成、真实工具执行、数据库变化、终止、official verifier、tokens和latency。实际顺序可以读成：

```python
model.eval()
model.requires_grad_(False)
for seed in ev['seeds']:
    for row in rows:
        r = inference_trajectory(
            model, tok, row, run_cfg, seed, 'B1',
            source_pool='development',
        )
        # 保存完整r，检查infra_invalid；没有optimizer更新
```

核心不是让模型预测reference文本，而是执行它生成的tool calls，再检查最终环境状态。失败也永久保存；不能只留下成功demo。单条超过context或轮数上限按协议终止，不自动截断observation或加预算。

### 文件五：scripts/compare_sft_evaluations.py → main

输入：三个完整48条结果和policy身份；输出：同任务、同seed的差值与配对区间。程序先要求数据hash、seed、GPU、包、代码commit一致，S1/S2训练GPU和代码也一致。

一个任务的两个seed相关，所以先得到每个任务0/0.5/1的成功比例，再重采样24个任务簇（主要指标20个非空任务），不能假装有48个互相独立任务。这个区间不涵盖不同训练seed、不同训练样本抽取的全部不确定性。

## 5. 最值得理解的真实轨迹

**成功改善：task184，seed42。** BASE直接执行：

```json
{"name":"customer_relationship_manager_delete_customer",
 "arguments":{"customer_id":"Quinn Taylor"}}
```

工具返回未找到，模型停止。S1改为：

```text
search_customers(customer_name="Quinn Taylor")
→ observation: customer_id="00000090"
→ delete_customer(customer_id="00000090")
→ Customer deleted successfully
→ official reward=1
```

名字到记录ID的映射来自真实observation，说明轨迹行为有具体变化。

**成功但有错：S1 task0。** 先查Carlos邮箱，再误传email_search_emails不支持的recipient参数；收到错误后去掉该参数，找到正确邮件并回复成功。schema error仍计入模型错误，不能因reward1删掉它。

**Grounding不够：S1 task414。** 查到了真实task ID，却选中Completed任务作为最紧急任务。S2在本题匹配官方目标，但这不证明它每次都懂“紧急”。

**更会行动也可能越界：S2 task12。** 查到Leila的In Progress为空，仍去查In Review并修改4条任务。ID有来源、接口合法、执行成功，任务却失败。

**不要强归因：task952。** S1只移动今天之前到期的任务；reference还包含今天到期的任务。官方失败原样保留，但是否把这当模型错误或DPO rejected，需要先澄清“逾期”边界。

## 6. 路线结论、尚未支持的推测、成本

首轮SFT训练与开发评测阶段已完成。S1是当前开发比较中的较稳健参照，不据此自动宣布它是最终最优checkpoint。S2主要指标只多1条成功，同时出现退化。现在应该解释行为差异，而不是自动增加epochs、样本或seed。

S1/S2的样本平均CE都下降，S2最终CE更低但总体成功率更低；两组数据不同，不能横向拿CE判优。平均轨迹延迟为BASE4.36秒、S1 12.64秒、S2 14.98秒；SFT输出更长且adapter未合并，不能把全部延迟差归因于Agent规划。

五个实验脚本合计0.71064 GPU-hours，容器启动估计到关机请求约2.40小时。后者包括下载、安装、间隔和证据回收。当前单价未知，人民币金额未估造。96GB卡已验证；S1 reserved峰值81.73GiB，不能声称80GB卡已通过同配置。

严格tool-composition、官方validation、BFCL仍未用于此次训练/评测；跨数据库记忆、泛化、多训练seed稳定性尚未回答。全量语义wrong-tool/wrong-argument/redundancy/premature指标仍需新逐条标注，不能以自动候选数替代。

## 7. 今晚三个知识点

1. context参与前向计算，与context进入loss，是两件事；掌握labels、shift、mask。
2. 参数更新、保存重载、Agent成功，是三层不同证据。
3. 相同总分可以隐藏不同failure；近似等预算的配对比较也可能得不到策略胜负。

## 8. 五个面试追问（不给答案）

1. 50条任务为什么会变成155个训练样本和310次更新？这怎样影响processed token成本？
2. 手工CE为什么要错位一格并排除-100？manual.detach为什么不会阻断实际训练？
3. task414说明grounded identifier和correct action有什么区别？
4. S2非空任务31/40优于S1的30/40，为什么还不能宣布S2胜出？
5. 你怎样挑选下一轮DPO pair，同时避免把环境语义歧义、infra failure或dev案例拿来训练？

未收到你的答案，也没有判定你已通过考核。考核不阻挡已授权实验；今晚可以把这份文件交给GPT逐题追问。

## 9. 明天需要确认的路线

建议先做本轮残余failure的完整语义审核，再以training pool准备可核验的DPO pairs和小规模训练完整性probe。另一条路线是先补真正sealed泛化资格设计。本轮没有自动开始DPO、RL、新teacher采样或新GPU实验。

## 10. 精确证据入口

执行commit：`f9d45c282b7cbebeedb1063e3c2c705330e0b23c`。冻结配置：`configs/sft_comparison_plan.json`。原预登记：`experiments/SFT-RESUME-20261010-001/config.json`。

实验ID：`SFT-EVAL-BASE-20261010-001`、`SFT-S1-20261010-001`、`SFT-EVAL-S1-20261010-001`、`SFT-S2-20261010-001`、`SFT-EVAL-S2-20261010-001`。各自experiments目录含config/identity/result和raw。

完整结果：`docs/SFT_EXECUTION_20261010.md`。配对统计和新审核：`reports/sft-comparison-20261010/`。原始归档/操作日志/关机证据：`evidence/sft-execution-20261010/`。原恢复过程：`evidence/sft-recovery-20261010/`。adapter：`checkpoints/SFT-S1-20261010-001/adapter/`与S2同名目录，均不进Git。


补充诊断盲点：S2 task363/seed42重复创建同一图表直到轮数上限，但每次都会修改analytics._plots_data，所以原same-state循环检测始终为false。已人工确认该例的重复行动；“state changed”不等于“任务有进展”。原始自动指标保留，不把候选循环数0写成真实循环率0，也不在本轮中途修改harness。

## 当天后续：已选择100条SFT，GPU缺货时完成全部本地准备

当前路线以这一段为准：你明确选择先做100条SFT规模检查，DPO暂缓。随后你告知没有GPU空位，本轮没有再开机、租卡、调用API或训练。

今天后半段回答的问题：不是“137条够不够”的抽象判断，而是能否用现有已审数据，准备一个近似相同预算的100条对照。结果是可行：原S1的50条保留，再加50条；100×1epoch=310steps，对比原50×2epochs=310steps。processed tokens +0.3521%，target tokens −0.8372%，max sequence7208。更改的是任务多样性与重复次数，不能称为所有其他训练维度都不变。

实际执行了数据库存核验、28条SFT官方失败初步归因、13个历史training偏好对候选编码、100条完整轨迹重新导出、训练/评测入口与部署白名单准备。13项CPU控制通过，包含拒绝dev、拒绝context计入loss、拒绝选择性target、以及训练/重载/rollout循环AST一致。第一次CPU准备因CRLF/LF原始hash不同停止，保留001失败和精确脚本快照；002证明只有换行差异后通过。没有重跑任何旧模型实验。

原始数字：已采集743个不同training任务（20+723）；主批723中审核150、通过137、暂缓13、未审573。原S1/S2实际各50、重叠16、合计84不同任务，主批另有53条已审且两组未用。旧20题另有15条教师质量通过记录，不等于自动加入当前训练导出。

本轮没有新success/failure模型轨迹；使用已有SFT评测做分析。S1的13条官方失败中2条“今天到期是否逾期”仍归因待定；S2的15条失败主要是日期条件、排序、虚构可选属性和范围越界。不要把28条失败分母的归因，冒充全144条或所有call的语义错误率。

13个DPO候选来自同一training任务的旧Base失败与DeepSeek成功；chosen/rejected监督tokens3489/2071，最长分支5431，初始上下文、工具和状态一致。它们只证明CPU格式可用，负例并非当前S1产生；没有GPU log-prob、梯度或DPO更新。后续若用这些新增任务做DPO，要设置相同chosen数据的继续SFT对照，否则新数据与偏好目标混杂。

今晚额外理解三个入口即可：

| 文件→函数 | 输入→输出 | pipeline作用 |
|---|---|---|
| scripts/prepare_sft_scale.py→main | 已冻结100条清单+原教师记录→310编码样本与v2配置 | 不重新采样，把已审完整轨迹转换为可训练输入 |
| veriagent/sft_scale.py→load_inputs | S100配置/样本/审批→验证后的样本与一次遍历顺序 | 防止换数据、漏掉assistant轮、dev泄漏或改mask |
| scripts/compare_sft_scale_evaluations.py→main | 未来S100与原S1结果→配对差值/区间 | 检查同条件与允许的代码差异，不因commit不同就随意比较 |

关键代码节选：

```python
# S100的每个assistant样本只出现一次
order = schedule(len(examples), cfg['epochs'], cfg['seed'])
require(len(order) == cfg['optimizer_steps_per_arm'] == 310,
        'Scale schedule changed')

# 原S1全部任务必须留在新100条里；禁止重新挑一个更好看的50条基线
require(s1 <= {x['task_uid'] for x in selection['tasks']},
        'Not nested original S1')
```

新增知识点：数据条数、assistant样本数、监督tokens和processed tokens是不同量；固定预算下增加不同任务会减少重复；CPU准入与真实GPU训练完整性仍是不同证据。

五个新增追问（不给答案）：
1. 100条各看一遍与50条各看两遍，究竟控制了什么、改变了什么？
2. 为什么已采集743条，仍只先用已审100条，而不直接训练全部官方成功轨迹？
3. token约束下按SHA目标选出的新增50条，能否宣称是均匀随机样本？
4. 为什么旧Base的失败不一定代表当前S1仍然会失败？
5. 为什么DPO添加新任务时，需要同样chosen数据的继续SFT对照？

下一步只等GPU资源可用，按已选S100范围部署预检→310步→48条eval→保全关机，不重新讨论是否“允许相同实验”。如果缺卡持续，不自动新租或开启库存监控。DPO/额外扩大到全部137条等路线尚未执行。

证据与配置：`experiments/POSTSFT-AUDIT-20261010-001/`；`experiments/SFT-SCALE-PREP-20261010-001/invalid_run.json`；`experiments/SFT-SCALE-PREP-20261010-002/result.json`和`cpu_controls.json`；**执行配置只用`configs/sft_scale_plan_v2.json`**。完整开跑步骤见`docs/SFT_SCALE100_READY_20261010.md`。拟用GPU experiment_id为`SFT-S100-20261010-001`和`SFT-EVAL-S100-20261010-001`，目前未执行。


数据覆盖补充：137条已审轨迹中空reference为0；S1/S2/S100也均为0。因而100条扩充未增加空reference任务覆盖。“这可能关联无需修改时过度行动”只是待检验的机制假设，不能由相关性作因果结论。保持当前S100冻结；未来若补合法no-op/约束拒绝样本，须单独审核和登记对照，不能悄悄改变本轮100条。证据：experiments/POSTSFT-AUDIT-20261010-001/noop_coverage.json。

口径注意：空reference与执行后无状态变化不是同一概念；137条中有1条教师执行没有状态变化。因此这里只确认“空reference子集未覆盖”，不声称所有合法no-op语义样本完全为零。state_change_coverage.json保留了该核验。

## 当天后续：83条空reference准入审核与MIX100

核心问题：能否从已有真实teacher轨迹中找出“有依据地不修改”的示范，并在不改变原S100的前提下准备混合对照？结果是29条通过、54条暂缓，混合100条已配出20条no-op+80条原S100。两组都仍未训练，GPU仍等待空位。

开始前：原137条已审池没有空reference任务，S100已冻结。实际审核：83条全部有处置，其中58条完整可见语义复核，25条在结构/调用错误门槛暂缓，不能说这25条都做了完整语义复核。通过的29条全部检查完整assistant轮与观察。对完全重复的观察用精确hash引用已展示内容，保留无损观察字典和原始轨迹。

主要暂缓原因：错误调用15、任务计数错11、context/encoding/round不完整10、重复核验7、求和错误4、错误比较并画图3，其余4类各1。80条官方成功中51条未通过整条SFT监督门槛。没有改reward、没有修正文案、没有把错误前缀mask掉后冒充完整好轨迹。

代表性通过：task17完整查询后发现最低值恰好3，正确区分<3与<=3，不画图；task51查到Anaya近7天已有会议，不新建；task329确认Nia没有InProgress，保持其他列表不变。代表性暂缓：task44不画图的结论正确，但声称51/54、实际求和48/51；task94正确判断没有InProgress，却算错任务分类数量；task47给PM查询传了不支持的page参数。

实验变量：从原S100替换20条行动任务为20条合格不修改任务。控制：100题、每域20、1epoch、310updates、同Base全新LoRA、原B1/8K/6轮/2048输出/dev24×两seed。processed1450298，相对S100+1.3869%；target28695，+1.3707%；max7756仍在8K。不能说只改变标签，实际任务内容和被移除的行动覆盖也改变了。

三段今晚可直接读的代码：

```python
# scripts/prepare_noop_mixture.py → main
# 输入：原始轨迹、人工判定和审批；输出：完整可训练样本与混合清单
if j['decision'] != 'approve':
    held.append(entry)
    continue
assert r['verifier']['official_reward'] == 1
assert r['termination'] == 'assistant_final'
assert r['events'] and all(not e['state_changes'] for e in r['events'])
assert all(c['executable_gate'] for c in r['call_diagnostics'])
```

这组assert证明结构和执行事实，**并不能自动判断推理正确**；例如task44通过状态门槛仍会算错数字，需要前面的完整语义判定。

```python
# veriagent/sft_mixed.py → load_inputs
# 输入：冻结混合数据和原S100清单；输出：通过准入的数据与训练顺序
require(len(base & {x['task_uid'] for x in selection['tasks']}) == 80,
        'Must retain80 originalS100')
require(sum(x['empty_reference'] for x in selection['tasks']) == 20,
        'Must include20 reviewednoops')
```

这些empty_reference标记用于数据审核与计数，不送进模型的input_ids。学生仍需自己根据任务和工具观察作决定。

```python
# scripts/check_noop_mixture.py → main
# 输入：实际导出数据和代码；输出：16项CPU控制回执
checks['no_held_task_selected'] = not (
    {x['task_uid'] for x in quality['held']}
    & {x['task_uid'] for x in selection['tasks']}
)
```

另有context不计loss、dev不能训练、完整target不能选择性删减，以及训练/重载/rollout循环AST一致检查。都通过也不能替代GPU上的真实CE、梯度、显存、重载和Agent成绩。

今晚三个学习点：任务成功与示范质量分开；不修改需要证据但不意味着必须零工具调用；混入no-op要同时测错误行动和错误不行动。

五个追问（不给答案）：
1. 为什么task44的reward=1仍不适合整条SFT？
2. 直接停止和查清楚之后停止，在最终状态相同的情况下如何区分？
3. 为什么保留原S100不变，另建MIX100，而不直接修改原训练集？
4. 加20条no-op同时移除20条行动任务，会引入怎样的解释限制？
5. 只有4个empty开发任务时，如何避免把一次提升夸大成普遍克制能力？

下一步等资源可用：先S100，再MIX100，各自全新Base、独立实验ID。没有自动租卡、开机、库存监控、teacher采样或DPO/RL。本轮GPU/API/参数更新均0；新mix最长序列7756，显存需实机核验。

证据：`experiments/NOOP-REVIEW-20261010-001/`与`experiments/MIX100-PREP-20261010-001/`；配置`configs/sft_mixed100_plan.json`；完整准备报告`docs/NOOP_MIX100_READY_20261010.md`。源仓库commit18486681c862d445e40ab9c42945c6308fab8b8a，执行过的CPU脚本SHA在identity/result中。拟GPU ID为SFT-MIX100-20261010-001、SFT-EVAL-MIX100-20261010-001，尚未执行。此前SFT学习内容全部保留。
