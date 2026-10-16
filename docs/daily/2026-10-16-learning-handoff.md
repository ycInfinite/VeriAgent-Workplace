# 2026-10-16 学习交接：用当前S1找真实失败，构建下一批偏好数据

## 1. 今天回答的问题

经过SFT的当前S1还有什么错误？这些错误能否和现有教师成功轨迹配成可靠DPO数据？答案是能，但本次只有6对明确成功/失败偏好，另1对回答准确性偏好单独保留。尚未训练这些数据。

## 2. 开始前状态

S1/S2、S100/MIX100、12对chosen-only SFT与DPO对照已完成。旧12对DPO没有证明额外收益。25题当前S1采集此前因缺卡停留在准备；你提供新克隆并要求保持开机，今天恢复执行。

## 3. 实际执行

固定25题一次采集 → 保存完整轨迹 → 逐条读50个教师/S1分支 → 回放工具与状态 → 记录全部25题审核结论 → 导出6+1对 → 检查编码/mask。没有新教师API、参数更新或后续评测。

## 4. 变量与控制

新增的是当前S1在冻结training任务上的一次输出；模型权重没有更新。原S1、B1、seed42、工具、初始状态、8192context、6轮、2048累计输出不变。任务排除原S1训练50题，但不是所有其他独立实验都没见过这些题。

## 5. 原始结果

- 25有效，0infra-invalid；官方成功18/25，非空15/20、空3/5。
- 工具87/90可执行；3次错误参数都在1179。
- 输入408,835 / 输出8,634 tokens；总89模型轮、90工具步。
- 推理脚本329.248秒，0.09146 GPU小时；另有部署和闲置占用。
- 六对奖励差偏好：1076、1000、473、349、1194、51。
- 一对同奖励偏好：702；两条轨迹都不改状态，但S1的总结数字错误。
- 1179因6轮截断暂缓；746因7天边界解释暂缓；其余16题不强行建pair。
- 50分支回放一致，12CPU控制通过；训练侧实际HF/梯度/重载仍待下阶段。

## 6. 代表性轨迹

成功：1146查出Olga的12条Backlog任务，只有Nov27到期的258/294过期，只移动这两条。说明模型能完成“查人 → 查任务 → 判断日期 → 批量更新”。

失败：349观察到Dec5/6/18/19，仍把18日当“下一次”改名。ID是真实观察到的，因此应归为时间排序/目标选择错误，不是identifier hallucination。

条件失败：51查到最近见过Anaya，仍新建会议。1000把“低于2”擅自解释成“低于2小时”。正确不操作需要判断谓词，不能只靠少调用工具。

奖励盲点：702真实分布Completed6/Backlog12/InReview4/InProgress0；S1不改状态拿到reward1，但声称11/10/3。可执行verifier不必然检查回答里的所有事实。

## 7. 路线级结论

流程是：现有S1 → training池rollout → 失败归因 → 优质教师配对 → 审核与编码 → 将来chosen-only SFT/DPO对照 → dev评测 → 最后sealed泛化。今天完成中间的数据环节。

样本量要分别数：采集25题、官方失败7题、可用奖励差6对、同奖励语义1对。增加总采集数不保证同比增加独立有效信号。六对集中在两个业务域，适合小范围机制检查，不能声称大样本泛化。

## 8. 尚未支持的推测

当前S1负例更适合DPO、增加数据能稳定提高成功率、SFT已经饱和、DPO普遍无效，都还没有证据。本轮仅seed42，不证明每个失败可重复。教师与S1的风格/长度混杂也没有消失。

## 9. 今晚最该理解的5处代码

| 文件 → 函数 | 输入 | 输出 | pipeline作用 |
|---|---|---|---|
| `scripts/collect_s1_failures.py` → `main` | 冻结config、S1adapter、25任务 | 原始trajectories与资源result | 只跑当前策略，不训练 |
| `scripts/run_day3.py` → `inference_trajectory` | model、tokenizer、task、seed、限制 | 每轮messages/tool/observation/state/reward | 把一次Agent任务展开成真实多步轨迹 |
| `veriagent/environment.py` → `WorkplaceEnv.step` | name和arguments | observation、exception、状态前后哈希和diff | 真实执行工具、捕获状态变化 |
| `scripts/review_current_s1_pairs.py` → `main` | 两个来源的完整轨迹及审核决定 | 分开的6对/1对、全部处置、回放记录 | 数据准入；reward只是一个检查条件 |
| `veriagent/teacher_data.py` → `CanonicalTeacherEncoder.encode` | 历史messages、tools、当前assistant | input_ids、labels、mask、token计数 | context不算CE，仅assistant作为目标 |

最关键的原代码片段：

```python
# collect_s1_failures.py：模型只生成，参数不更新
model.eval()
model.requires_grad_(False)
# 没有optimizer和backward；一条新的rollout不是一次训练。
```

```python
# environment.py：工具不是手工写好的固定回答
result = self.tools['functions'][action['name']](**args)
after = snapshot(self.tools)
# 前后state_diff和真实result一起进入轨迹。
```

```python
# teacher_data.py：把上下文与目标拼接
'input_ids': prefix_ids + target_ids,
'labels': [-100] * len(prefix_ids) + target_ids,
# prefix包含用户任务、工具观察以及之前交互。
# -100使这些位置不参与本轮交叉熵。
```

```python
# review_current_s1_pairs.py：不能只有reward高低就直接训练
require(c['termination'] == s['termination'] == 'assistant_final',
        'Censored/corrupt pair')
a, b = branch(c, encoder), branch(s, encoder)
# 每条分支保留自己的工具观察；不能把chosen观察塞到rejected里。
```

## 10. 今晚三个知识点

1. SFT学“这类上下文下应输出什么”；DPO学“同一个任务哪条完整决策轨迹更值得提高相对概率”。DPO不等于重新在线探索。
2. 工具可执行、最终状态正确、回答事实正确，是不同层次。349工具完全可执行却操作错目标；702状态正确但总结不对。
3. 截断是一种有效policy-budget失败，但本次数据协议不把它当完整rejected。暂缓不等于删除，也不等于基础设施出错。

## 11. 面试追问（先不看答案）

1. 为什么18/25不能拿来与此前35/48直接算提升或退步？
2. 为什么349用了真实ID，却仍然失败？指标应怎么命名？
3. 为什么同样reward1的702仍能构成偏好对？它优化的到底是什么？
4. 为什么1179不是infra-invalid，却被本轮DPO导出排除？
5. 六对数据做完DPO后分数升高，为什么仍需要同数据chosen-only SFT对照？

## 12. 下一次需要你决定的路线

建议先用6个reward-gap做有界chosen-only SFT对照DPO，起点仍是原S1，702保留作独立后续项；这只是小样本机制检查。另一条路线是先冻结新的training任务批次、扩大当前策略失败覆盖。两条都需要新登记，不因机器开着就默认训练。今天不启动下一实验。

实例按你的要求保持开机，已无采集计算进程；SSH已关闭。GPU资源仍占用并持续计费，真实单价未知，不能把脚本约5.5分钟当成整机账单时长。

## 13. ID、log、commit、config

- 运行：`S1-FAILURE-ACQUIRE-20261012-001`，实际Oct16，execution commit `4efbf07e3410cad64b20989498247405e2026a0d`。
- 审核：`S1-PAIR-REVIEW-20261016-001`；12个检查位于其`cpu_controls.json`。
- 配置：`configs/s1_failure_acquisition.json`、`configs/s1_failure_pair_review_protocol.json`、`experiments/S1-FAILURE-RESUME-20261016-001/config.json`。
- 原始messages：`experiments/S1-FAILURE-ACQUIRE-20261012-001/trajectories.jsonl`。
- log与15成员SHA归档：`evidence/s1-failure-execution-20261016/raw.tar.gz`；资源汇总`resource_summary.json`。
- 完整报告：`docs/S1_FAILURE_COLLECTION_RESULT_20261016.md`。
