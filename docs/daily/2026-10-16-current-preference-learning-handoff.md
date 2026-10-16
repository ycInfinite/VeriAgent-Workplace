# 2026-10-16 学习交接：六对当前策略负例的 SFT / DPO 对照

今天已结束本阶段的新实验。下面供离开电脑后粗颗粒复习；学习和答题不是继续实验的审批门槛。

## 1. 今天回答的核心问题

用当前S1真实失败形成的六对数据，DPO是否比只学习相同正确轨迹更好？本次DPO修好一条非空任务seed，但损失三条空任务seed，总体没有优于chosen-only SFT。不能由此判断DPO普遍无效。

## 2. 开始前状态

原S1已经完成SFT。今天先固定采集25题，审核得到6个成功/失败偏好对，另一个同奖励语义pair702单独保留。此前旧12对DPO没有证明额外收益，因此这次检查更贴近当前S1错误的数据是否能提供帮助。

## 3. 实际执行

```text
原S1 ───────────────────→ 同机baseline评估48条
  ├─ 同6题chosen，SFT6步 → 新adapter → 评估48条
  └─ 同6题chosen/rejected，DPO6步 → 新adapter → 评估48条
```

两个训练臂各自重新加载原S1。DPO的reference也是原S1，训练过程中固定。不是先SFT6步再接着DPO6步，也不是在线GRPO。

## 4. 唯一主要变量与控制

主要变量是优化目标：chosen-only交叉熵 vs DPO。相同六题、chosen轨迹、任务顺序、原S1、学习率5e-6、seed42、各6次更新、8192context、同机、dev24×42/43。DPO beta固定0.1，不挑checkpoint、不调参。

匹配了任务和chosen暴露，**没有匹配总tokens、前向次数或GPU时间**；DPO多看了rejected和reference。也不能和旧12对直接当“负例来源”单变量比较，因为任务、数量都变了。

## 5. 原始结果

| 条件 | 非空任务 | 空任务 | 总体 |
|---|---:|---:|---:|
| 原S1 | 30/40 | 5/8 | 35/48 |
| chosen-only SFT | 30/40 | 6/8 | 36/48 |
| DPO | 31/40 | 3/8 | 34/48 |

144条均为有效环境运行、0infra-invalid。SFT有一条六轮耗尽，仍计有效模型失败。一次CPU启动导入错误发生在模型运行前，单独永久保留，修复后所有正式ID只执行一次。

DPO相对SFT非空+2.5pp，task bootstrap95%CI[0,7.5]pp；总体−4.17pp，CI[−12.5,4.17]pp。空任务只有4个任务簇，不能把8条rollout当8道独立题。单训练seed和已暴露dev限制了结论。

两臂各504个LoRA张量改变，保存重载logit差0，39轮真实HF模板和mask一致，Torch梯度对照差0。五个脚本合计约31.8分钟GPU时间，实例部署/闲置/备份另计；本机单价未知，不编造人民币费用。

## 6. 代表性成功与失败

**真的修好执行：684/seed42。** 原S1和SFT找到四名客户，却停在“给你列出来”；DPO找到Akira邮箱，再把四条记录真正重新分配。这是执行闭环改善，另一seed仍失败。

**奖励上升却没修好推理：122/seed43。** SFT和DPO这次没画图，官方成功，但都把周一Nov27当星期二。正确状态结果不代表正确判断过程。

**不该操作却操作：12/seed42。** DPO查到In Progress为空，仍把In Review任务移到Backlog。ID有观察依据，错误在把条件换掉，不是ID幻觉。

**错误删除：709/seed43。** DPO把相对Nov30已经过去的Nov14会议说成未来并删除。

**相同失败奖励、不同过程：414/seed42。** SFT逐日重复查询已完成任务，耗尽6轮；DPO直接把Completed任务当最紧急任务转交。两者都reward0，但失败机制不同。

## 7. 路线级结论

六对数据足以验证完整训练与评估链路，也能改变一些行为；不足以证明稳定的DPO优势。新负例里虽然有正确不操作示范，DPO在开发集的正确克制行为仍变差。

全部24条空任务重新审核：有依据完成不修改，S1/SFT/DPO分别4/8、4/8、2/8；整条无已发现语义错误分别2/8、2/8、1/8。今天总共读了37/144条完整轨迹，包括全部空任务、全部DPO非空官方失败和关键变化案例，不声称144条全部语义审核。

项目现在已完成：真实轨迹、数据审核、SFT参数更新、DPO参数更新、同数据chosen-only对照、闭环Agent评估、成本记录。未完成的主要研究证据仍包括更充分的数据覆盖和sealed泛化；Online RL仍是可选项。

## 8. 尚未支持的推测

“只要扩数据就一定提高”“DPO本身有害”“当前策略负例比旧Base更有效”“SFT已经饱和”“原S1适用于外部benchmark”都没有被这次实验证明。

当前只有六对、两个训练业务域、1774个chosen目标tokens。低样本、覆盖偏窄、目标尺度、更新量和训练seed都可能影响结果；我们没有做区分这些因素的消融。

## 9. 今晚最该理解的5处代码

| 文件 → 函数 | 输入 | 输出 | pipeline作用 |
|---|---|---|---|
| `scripts/run_current_s1_preference_pipeline.py` → `main` | 固定计划、尚未用过的runIDs | 五个顺序实验、状态日志 | 某正式阶段失败就停止；不关机器 |
| `scripts/run_current_s1_preference.py` → `main` | 原S1、6对、训练条件 | 6次更新、新adapter、重载证据 | 比较两种目标，保持起点相同 |
| `veriagent/dpo.py` → `turn_logp` | 模型、一轮input_ids/labels | 本轮assistant目标token的log概率和 | 工具观察不作为预测目标 |
| `veriagent/dpo.py` → `pair_backward` | 两分支、固定reference、beta | loss/margin/梯度 | 分轮重算，保持完整DPO目标并节省显存 |
| `scripts/compare_current_s1_preferences.py` → `main` | 三组48条真实评估 | 配对差值和task-cluster区间 | 避免把两个seed当独立任务 |

先看chosen-only SFT的真实训练核心：

```python
target_count = p['chosen']['target_tokens']
for ex in p['chosen']['encoded_turns']:
    nll = -turn_logp(model, ex) / target_count
    nll.backward()
# 该任务所有assistant轮次完成后才optimizer.step()
```

这让模型提高正确轨迹的概率。除以本任务目标token数后，该任务优化的是平均交叉熵；没有读取rejected。

再看DPO的核心数学，对应`scalar_loss_and_coefficient`：

```python
z = beta * ((pc - pr) - (rc - rr))
loss = max(0., -z) + math.log1p(math.exp(-abs(z)))
```

`pc/pr`是当前policy对chosen/rejected完整assistant目标的log概率和，`rc/rr`是冻结原S1的对应值。希望当前policy相对reference更偏向chosen。首步policy等于reference，所以margin=0、loss=ln2。

log概率只收集label不为−100的位置：

```python
labels = torch.tensor([example['labels']], device=device)[:, 1:]
mask = labels != -100
logits = output.logits[:, :-1, :][mask].float()
return -F.cross_entropy(logits, labels[mask], reduction='sum')
```

shift使当前位置预测下一个token。用户和工具观察保留为可见context，只是不直接计目标loss；不是把它们从attention中删掉。DPO每个分支保留自己的工具观察，不能混用。

## 10. 今晚三个知识点

1. **参数更新成功 vs 能力提升**：权重变化、梯度正常、重载一致是训练完整性；只有执行新策略的Agent评估才能谈任务表现。
2. **同数据对照的重要性**：DPO之后涨分可能来自新增正确示范，所以需要chosen-only SFT。即使有此对照，本次仍不等总算力。
3. **任务成功与条件遵守**：做对该做的操作、避免不该做的操作都重要；总reward、空/非空分层、语义审核需要一起看。

## 11. 面试追问（不给答案）

1. 为什么DPO非空31/40高于SFT30/40，仍不能说它整体更好？
2. 六个DPO loss点能否证明训练loss在持续下降？为什么？
3. 如果DPO reference误用裸Base、关闭S1 adapter，会改变什么？
4. 为什么工具观察labels=−100，模型仍然能够利用观察作决策？
5. 下一轮要区分“数据太少”和“优化目标有问题”，应该固定哪些变量、改变哪个变量？

## 12. 下一次需要确认的路线分叉

建议优先冻结一批新的training任务，扩大当前策略偏好数据的行为覆盖，再做有界对照；不直接在六对上反复加epoch/调beta。另一条路线是先整理未见工具组合与最终held-out的评估资格，完成项目的泛化环节。今天两者都没启动，也没有进入RL。

你要求保留GPU资源，因此机器仍开机；当前训练和采集进程均已结束，SSH已关闭，后续实例继续计费。

## 13. experiment_id、log、commit、config

- 执行commit：`6b7898e9c9ca4d82f95e00bf40b1ec0ecbf528f7`。
- 配置：`configs/current_s1_preference_plan.json`。
- 训练：`CURPREF-CHOSEN-SFT-20261016-001`、`CURPREF-DPO-20261016-001`。
- 评估：`CURPREF-EVAL-S1-20261016-001`、`CURPREF-EVAL-CHOSEN_SFT-20261016-001`、`CURPREF-EVAL-DPO-20261016-001`。
- CPU故障：`experiments/CURPREF-BOOT-20261016-001/`，正式运行前的common导入失败，没有隐藏。
- 日志/65成员归档/6adapter文件校验/资源记录：`evidence/current-preference-execution-20261016/`。
- 配对结果与逐案审核：`reports/current-preference-20261016/`。
- 完整报告：`docs/CURRENT_S1_PREFERENCE_20261016.md`。
