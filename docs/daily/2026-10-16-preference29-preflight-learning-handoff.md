# 2026-10-16 学习交接：29对数据进入训练前的最后检查

## 1. 核心问题

审核过的trajectory能否完整、正确地变成训练张量，并在当前单卡上计算梯度？这与“DPO能否提升Agent”是两个需要分别用证据回答的问题。

## 2. 开始前状态

原始S1、旧12对及当前6对偏好对照均已有结果。新采91题后累计29个奖励差pair、4个同奖励语义pair。新数据已经过回放、语义审核和本地编码，但还缺实际HF全分支验证与长序列反向显存检查。

## 3. 实际执行

固定29对 → 全179个assistant回合用实际HF重建input_ids/labels → 小模型梯度等价控制 → 原始S1加载 → 最长task358的chosen完整分支CE反向 → 固定S1参考分数 → chosen/rejected完整分支DPO反向 → 比较原权重。

没有optimizer.step，没有新adapter，没有新Agent rollout。后台进程结束后保留主机开机。

## 4. 唯一变量与控制

比较两种反向目标：chosen-only CE与DPO。数据、原S1、随机种子、dtype、attention、checkpointing、context和主机固定。最长pair按序列长度选出，不依据训练成绩。后续29对正式实验方案只是准备，未执行。

## 5. 原始结果

179/179实际HF回合、7/7梯度控制通过。task358的SFT反向5.156秒，reference3.595秒，DPO反向15.723秒；DPO初始margin0、loss=ln2、重算差0。504个LoRA张量完全不变。全脚本51.072秒，设备峰值28.417GiB；12成员原始归档SHA验证通过。没有参数更新，当前29对尚未训练。实例保持开机，SSH关闭。

## 6. Representative trajectory

task358同时包含最长chosen6365和最长rejected8073token。这里选择它用于显存边界，不把它当作本轮新生成的成功/失败案例。语义审核与原始messages仍保存在 `experiments/S1-EXPAND-REVIEW-20261016-001/cumulative_reward_gap_pairs.jsonl.gz`；本轮只有离线重算已有轨迹，没有新增任务表现。

## 7. 路线级结论

通过检查后，下一步才是原始S1出发的29步chosen-SFT与29步DPO，并做同主机固定dev评测。数据量增加不会自动带来提升，必须比较相同chosen数据的SFT基线。

## 8. 尚未支持的推测

本轮不能证明DPO更强、29对足够、80GB一定能跑、或训练后泛化更好。最长pair无optimizer反向也不替代全29对更新、保存重载与Agent评测。

## 9. 今晚理解的四个代码入口

1. `scripts/preflight_preference29.py → main`：输入固定配置/29pairs/原S1，输出HF、梯度、显存和权重不变证据。作用是训练准入。
2. `scripts/run_current_s1_preference.py → actual_tokenizer_check`：输入messages/tools和预编码turns，输出179回合逐一一致检查。context的labels全−100，assistant完整目标不裁剪。
3. `veriagent/dpo.py → turn_logp / branch_score`：输入某一分支各assistant回合，输出该分支所有目标token的log-probability之和。工具观察参与预测条件，不作为预测目标。
4. `veriagent/dpo.py → pair_backward`：输入chosen/rejected和冻结参考分数，输出DPO loss与梯度。先无梯度算系数，再逐回合重算反向；函数本身不更新参数。

关键代码的粗颗粒含义：

```python
# chosen-only SFT：一次任务更新使用该任务全部chosen目标。
for turn in pair['chosen']['encoded_turns']:
    loss = -turn_logp(model, turn) / pair['chosen']['target_tokens']
    loss.backward()

# DPO：相对于冻结S1，更偏好chosen而不是rejected。
margin = (policy_chosen - policy_rejected) - (reference_chosen - reference_rejected)
loss = -logsigmoid(beta * margin)

# 本轮到梯度为止。正式训练才会在完整任务反向后调用：
# optimizer.step()
```

`backward()`把梯度累加到参数的`.grad`；`step()`才用梯度改变参数。不能看到梯度非零就说完成了训练。

## 10. 今晚三个知识点

- 条件上下文与监督目标：不监督tool observations，不代表模型看不到它们。
- 冻结参考策略：DPO比较当前policy相对于初始S1的偏好变化，不是只比较两个原始概率。
- 匹配对照：同任务、chosen曝光、更新数不意味着等计算量，DPO还有rejected与reference开销。

## 11. 五个面试追问（不给答案）

1. 为什么29个pair会产生179个assistant训练回合？
2. 为什么工具观察不能简单拼进去全部计算CE？
3. 为什么DPO初始margin应接近0、loss接近ln2？
4. 两次前向重算为什么要求关闭dropout？
5. 只验证最长序列还遗漏了哪些正式训练风险？

## 12. 下一次路线分叉

执行已准备的29对chosen-only SFT／DPO对照，或者先调整研究问题；不自动追加教师采样、same-reward训练、RL或sealed评测。推荐按固定29对完成一次对照再判断。

## 13. 证据入口

- experiment_id：`PREF29-PREFLIGHT-20261016-001`
- execution commit：`a0a5e5edba40aea97f7058c4b151bfc8d8ae0310`
- config：`configs/preference29_preflight.json`
- proposal：`configs/preference29_comparison_proposal.json`
- evidence：`evidence/preference29-preflight-20261016/`
- 远端日志：`logs/pref29-preflight-20261016/process.log`
