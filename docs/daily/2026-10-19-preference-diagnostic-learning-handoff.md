# 2026-10-19 学习交接：DPO学到了偏好，还是学会了执行？

## 1. 核心问题

上一轮DPO没有超过同chosen的SFT。今天不换算法，先诊断现有权重在训练数据上的拟合，以及重新执行训练任务的表现。

## 2. 开始前状态

29对完整偏好数据、S1/SFT29/DPO29权重已冻结。旧dev整体35/34/33，不足以判定DPO普遍无效。chosen全部来自历史DeepSeekAPI成功轨迹，rejected来自原S1真实失败；由Codex单审核者筛选，并未独立人工复核。

## 3. 实际执行流程

固定两题复算S1分数验证旧cache → 两个最终adapter分别给同29对完整轨迹打分 → 两模型各执行同29任务、seed42一次 → 新读输出与观察 → 联合解释。没有参数更新，没有新teacherAPI，没有重跑dev，没有打开final/BFCL。

## 4. 变量与控制

只更换已冻结策略；29题与顺序、真实环境、B1、8192、六轮、768单次/2048累计输出不变。S1历史失败是数据入选条件，不能把训练题的成功率提升写成泛化进步。新58条rollout不自动加入训练数据。

## 5. 原始结果

已完成的打分部分：原S1两题缓存复算差0。SFT和DPO均29/29相对margin改善、chosen logp提高、rejected logp下降。平均DPO目标loss分别0.252519和0.164948，参考为0.693147。

平均Δchosen：SFT+9.4998、DPO+8.6805；平均Δrejected：SFT−4.1458、DPO−10.8751。这些是sum-logp单位，不是成功率或百分比。DPO更大的margin主要来自更强rejected抑制，不等于比SFT更会生成成功行为。58条rollout仍待完整结果。

## 6. Representative success / failure

待新读本轮轨迹后回填，不复用旧标签冒充新审核。

## 7. 路线级结论

待结果。今天区分：偏好分数未学会；偏好分数学会但执行失败；训练题执行改善但泛化仍未证明。训练诊断不能单独证明长程credit assignment就是失败原因。

## 8. 尚未支持的推测

不把较低DPO loss直接解释为真实任务完成；不把teacher生成的正确轨迹等同于当前policy自己能生成；不把训练任务表现当独立测试。单seed、29任务不均衡和单审核者限制仍保留。

## 9. 四个代码入口

- `veriagent/preference_diagnostic.py → load_inputs`：输入固定config/pairs/tasks/reference，检查29题、初始messages/tools和缓存身份；输出四个固定对象。
- `veriagent/preference_diagnostic.py → score_change`：输入当前与参考的两分支logp，输出Δchosen、Δrejected、margin和DPO loss。
- `scripts/run_preference_diagnostic.py → main`：输入mode/condition，完成reference校准、完整轨迹重打分或真实rollout，输出不可覆盖的实验文件。requires_grad=False，不创建optimizer。
- `scripts/analyze_preference_diagnostic.py → main`：按task_uid将打分与执行结果连接，区分margin改善但执行仍失败的案例。

核心计算：

```python
delta_chosen = logp_current_chosen - logp_S1_chosen
delta_rejected = logp_current_rejected - logp_S1_rejected
margin = delta_chosen - delta_rejected
loss = -logsigmoid(beta * margin)
```

例如chosen概率没变、rejected的logp下降4，margin也会增加4。它说明相对偏好改善，不能单凭它说模型已经更会生成chosen。每token归一化结果只帮助诊断长度因素，不替换原始训练loss。

## 10. 今晚三个知识点

1. teacher forcing打分与自由生成闭环执行的差别。
2. DPO相对概率改善和chosen绝对概率改善的差别。
3. 选取模型失败任务之后，为什么原S1的0%不能当无偏baseline。

## 11. 五个考核追问（不给答案）

1. 为什么首步margin=0，却不能说明训练后的29题margin也都为0？
2. chosen概率没提高，DPO loss能下降吗？
3. 为什么给一条已知正确轨迹高概率，不保证rollout成功？
4. 若29道训练题执行改善，仍不能证明什么？
5. 如何区分优化不足、数据覆盖不足和整轨迹监督过粗？需要哪些额外证据？

## 12. 下阶段分叉

本轮完成后停止，由诊断结果决定是否研究拟合强度、数据/决策监督，或准备独立泛化协议。不自动加epochs、换算法、调用新teacher或执行sealed测试。

## 13. 证据入口

配置：configs/preference29_diagnostic.json。
执行commit：de49b932d927a35edf11a534da7990eefeb7469d。
新runID：PREF29-DIAG-REF/SCORE-CHOSEN_SFT/SCORE-DPO/ROLLOUT-CHOSEN_SFT/ROLLOUT-DPO-20261019-001。
原始日志：logs/pref29-diagnostic-20261019。
证据：evidence/preference-diagnostic-20261019；分析：reports/preference-diagnostic-20261019。

CPUprep001的本地S1缓存假设错误已保留；002通过17控制，三套远端adapter文件哈希均匹配。实例按用户要求保持开机。
