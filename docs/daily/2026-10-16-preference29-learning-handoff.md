# 2026-10-16 学习交接：29对偏好训练与同chosen对照

## 1. 核心问题

从当前S1失败中得到的29对数据，能否让DPO比只学习相同chosen的SFT更有效？先前6对和12对实验没有证明稳定整体优势，这次扩大覆盖，不预设答案。

## 2. 开始前状态

29个奖励差pair已经完成两分支审核、实际HF179回合检查和最长8073tokens反向资格。14空reference、15非空，五域不均衡。4个同奖励语义pair单独保留。原S1与所有旧adapter完整保留。

## 3. 实际执行流程

原始S1同主机评测 → 原始S1做chosen-SFT29次更新并重载 → SFT评测 → 原始S1做DPO29次更新并重载 → DPO评测 → 配对统计与语义审核。

每组24个development任务、seed42/43，共48条；整个矩阵144条。没有新增教师API、训练题采集、RL或sealed测试。

## 4. 唯一变量与控制

训练目标是主要变量：chosen目标token平均CE与完整轨迹DPO。固定同29题、chosen曝光、任务顺序、29次更新、原始S1、学习率5e−6、seed42和同主机。DPO beta=0.1，reference始终是冻结原始S1。

这是同数据/同更新数对照，不是同计算量对照。SFT一次输入389709tokens；DPO的reference一次846778、policy打分与反向重算1693556，另有checkpoint内部重算和重载验证。成本要真实记录。

## 5. 原始结果

144有效/0infra-invalid。S1/SFT29/DPO29整体35/34/33（分母48），非空30/29/29（分母40），空reference5/5/4（分母8）。DPO−SFT非空0pp，95%任务聚类区间[−7.5,+7.5]pp；整体−2.083pp，[−8.333,+4.167]pp。

两组各29次真实更新，504LoRA张量改变，reloadlogits差0。SFT平均update4.003s，DPO11.239s，DPOreference另74.769s；全部5脚本共0.743011GPUh，RMB时价未知。

## 6. Representative success/failure

已完成的具体对照：task18/seed42要求修改Nov30时间最晚的事件。返回列表按时间倒序，第一行15:30、最后一行09:30。原S1选择15:30的event253并成功改名；chosen-SFT选择09:30的event200并错误宣称完成。两者ID都来自观察，差别是时间排序与目标选择，不是ID幻觉。

baseline与chosen-SFT的8条空reference各已重新审核：官方5/8成功，有充分依据完成不修改4/8，整条干净2/8。task122把周一Nov27称为周二；有时碰巧不画图但reward1，不代表条件判断正确。DPO在task18/42选择正确，但在task1/43又把“末页09:00”当成“最晚15:00”。它恢复一道题却丢掉另一道题，非空总分与SFT相同。

DPO空reference官方4/8、有证据且完整结束3/8、整条干净0/8；task12/43重复空查询到轮数上限，reward1只是状态未变。另有task684分页漏查和错误负责人过滤；task952/42输出截断，包含未来到期任务的拟操作，严格gate执行0次修改。

## 7. 路线结论

本轮没有建立DPO相对同chosen-SFT的额外收益。也不能证明DPO普遍无效；这是一个训练seed、29对不均衡数据、小且多次曝光的dev。

建议停止自动堆DPO数据/步数，保留负结果，下一阶段先准备独立泛化评测协议。项目已完成真实SFT和偏好优化能力链，尚不能宣称最终泛化。

## 8. 未被支持的推测

29对覆盖五域，不等于充足或均衡。20对chosen比rejected短，长度与行为质量仍可能相关；没有按长短造标签，但也没有证明消除了长度影响。1069/956的reference相同，不是完全独立证据。固定dev已经多次曝光，不能把这次结果称作最终泛化结论。

## 9. 四个代码入口

- `scripts/run_preference29.py → main`：输入冻结29pairs与原S1，输出每步loss/梯度/adapter/重载结果。每个task完整反向后只step一次。
- `veriagent/dpo.py → pair_backward`：输入两个完整分支及冻结参考分数，输出DPO梯度与重算一致性；不执行optimizer.step。
- `scripts/evaluate_preference29.py → main`：输入固定dev24与某个明确adapter，执行真实工具、保存状态和verifier；输出48条轨迹。评测时requires_grad=False。
- `scripts/compare_preference29.py → main`：输入三组同task/seed记录与训练证据，输出配对差值、按任务聚类置信区间；不挑checkpoint。

核心循环可这样理解：

```python
# SFT：把同一任务chosen各回合的梯度累加。
optimizer.zero_grad(set_to_none=True)
for turn in pair['chosen']['encoded_turns']:
    loss = -turn_logp(model, turn) / pair['chosen']['target_tokens']
    loss.backward()
clip_grad_norm_(trainable_parameters, 1.0)
optimizer.step()  # 一道任务一次更新

# DPO：参考分数来自更新前的原始S1，整轮固定。
optimizer.zero_grad(set_to_none=True)
pair_backward(model, pair, frozen_S1_reference[pair['pair_id']], beta=0.1)
clip_grad_norm_(trainable_parameters, 1.0)
optimizer.step()
```

同一task的chosen/rejected各有自己的历史observations。观察只作context，loss只落在assistant生成的tool call和最终响应上。

## 10. 今晚三个知识点

1. 为什么DPO需要chosen-only SFT对照，而不能只和原模型比较。
2. 为什么离线DPO虽然属于偏好优化，却不是current-policy online RL。
3. 为什么把同一任务两个seed当两道独立题会夸大统计把握。

## 11. 五个面试追问（不给答案）

1. 本实验为什么同时保持原始S1作为policy起点和reference？
2. 每任务一次更新与每assistant回合一次更新有何不同？
3. 同chosen、同29次更新还缺少哪些等预算条件？
4. 空reference获得reward1，为什么仍需要语义审核？
5. 若DPO总体提升但只来自四个空reference任务，你会怎样表述结论？

## 12. 下一次路线分叉

本矩阵完成后停止新增实验，依据实际结果决定：继续研究数据选择/偏好目标，还是收敛当前结论并转向独立泛化评测设计。不要自动增加epochs/seeds、加入同奖励pair或进入RL。

## 13. 追溯

执行commit：033a53f2c49d7ce134c1f24cf5dc4efa60a02907。
配置：configs/preference29_plan.json。
训练：PREF29-CHOSEN-SFT-20261016-001、PREF29-DPO-20261016-001。
评测：PREF29-EVAL-S1/CHOSEN_SFT/DPO-20261016-001。
证据：evidence/preference29-20261016；报告：reports/preference29-20261016。
远端状态：logs/pref29-20261016/status.json。实例保持开机。


最终审核范围：24条空reference+28条非空轨迹，共52条新读；不是144条全部语义标注。62原始成员SHA已核验；两次慢速SFTP中断属于回收操作，部分文件保留，正式模型run没有重跑。


交接完成：两个adapter六文件已核验，计算与SSH连接均结束；实例仍开机，后续分配费用持续。完整报告`docs/PREFERENCE29_COMPARISON_20261016.md`；最终回执`evidence/preference29-20261016/completion.json`。
