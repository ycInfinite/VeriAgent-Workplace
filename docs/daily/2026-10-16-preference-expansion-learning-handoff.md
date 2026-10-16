# 2026-10-16 学习交接：偏好数据从6对扩到29对

## 1. 今天回答的核心问题

在不新增教师API、不把开发集拿去训练的情况下，能否扩大当前S1偏好数据的覆盖？可以：新增23对奖励差偏好，累计29对，覆盖从2个域扩到5个域。另新增3对同奖励语义偏好，累计4对单独存放。

## 2. 开始前状态

六对数据的对照已完成：S1/SFT/DPO总体35/36/34条成功，DPO没有显示整体优势。本次没有继续加训练步数，而是补数据覆盖。已有教师池中，排除原S1训练50题与前25题采集，还剩91个历史已审候选。

## 3. 实际执行

冻结91任务 → 原S1各采一次 → 保存完整轨迹 → 全182分支机械回放 → 完整审核36条S1与28条教师 → 编码准入 → 保存新增与累计偏好池。

没有新教师调用、没有模型参数更新、没有重采失败任务、没有打开final/BFCL。

## 4. 变量与控制

新增的是training任务覆盖。原S1权重、B1、seed42、8192context、六轮、单次768输出、累计2048输出均不变。用户换了新PRO6000克隆，驱动由595.71.05变为595.58.03；这个差异已记录，不能把新旧采集分数差看成能力变化。

## 5. 原始结果

| 项目 | 结果 |
|---|---:|
| 新rollouts | 91有效、0infra-invalid |
| 官方成功 | 65/91 |
| 非空 / 空reference成功 | 55/67、10/24 |
| 新奖励差pairs | 23 |
| 新同奖励语义pairs | 3，分开保存 |
| 累计奖励差 / 同奖励pairs | 29 / 4 |
| 语义暂缓 | 2题 |
| 截断/不完整暂缓 | 4题 |
| 本轮GPU脚本时间 | 19.2分钟 |
| 参数更新 / 教师API | 0 / 0 |

91题不等于91个偏好对。55条非空reward1只机械筛查，没有当成新质量合格数据。4条有依据正确不操作的S1没有硬造偏好。全部182分支回放一致，导出后11项CPU控制通过。

## 6. 代表性成功和失败

- **1006：ID正确，收件人错误。** S1找到正确邮件，却凭空写sofia@atlas.com；教师查目录得到sofia.santos@atlas.com。工具返回成功仍可能业务失败。
- **973：漏约束。** 要移动Lead，S1把Qualified/Won/Lost也移动。调用可执行、ID真实，仍然越界。
- **176：会算但不遵守。** S1知道−60%不满足“增长超过5%”，却继续画图。
- **666：观察已有，排序错。** 最早未完成任务是Nov28，S1却选Nov29。
- **811/329：失败被奖励掩盖。** 没有In Progress任务，模型却想改全部任务；输出截断后严格门禁没有执行。状态未变带来reward1，却不是正确克制。

## 7. 路线级结论

累计29对奖励差数据中：analytics15、calendar7、CRM2、email3、项目管理2；包含14个空reference与15个非空reference任务。覆盖扩大了，但analytics仍占一半以上。

1069/956虽然是两题，却要求删除同一场会议；已经记录重复操作目标。不同task_id不等于独立能力模式，22种chosen调用序列也不是22种新技能。

本阶段只证明“有了更丰富且通过审核的偏好数据”。没有训练新的29对数据池，因此没有能力提升结论。

## 8. 尚未支持的推测

更多pairs一定修好之前DPO的过度操作、五个业务域均衡、同reward语义pair一定有收益，都还未证明。教师此前已审，也不能免除本轮复核：1135的比较条件不清，50的教师比较增长率解释不够可靠，均被暂缓。

最长canonical序列达到8073，接近8192。CPU能编码不代表这一批数据已通过真实GPU训练显存检查。

## 9. 今晚需要理解的5处代码

| 文件 → 函数 | 输入 | 输出 | 作用 |
|---|---|---|---|
| `prepare_preference_expansion.py` → `main` | 已审教师清单、S1训练ID、旧25ID | 固定91任务和哈希 | 采集前决定样本，防止按成绩换题 |
| `collect_s1_preference_expansion.py` → `main` | 原S1、91任务、固定预算 | 完整真实rollouts | 当前策略负责决定工具调用 |
| `replay_preference_expansion.py` → `main` | 教师/S1共182分支 | 观察/状态/reward一致性记录 | 排除数据损坏和不可复现工具状态 |
| `export_preference_expansion.py` → `main` | 原始记录、回放、人工judgments | 新增与累计29/4数据文件 | 语义、完整性和编码都过才准入 |
| `check_preference_expansion.py` → `main` | 导出的两类数据池 | 11项控制 | 泄漏、mask、重复、旧数据保护和标签门槛 |

固定候选集合的核心逻辑：

```python
eligible = [x for x in approvals
            if x['task_uid'] not in s1 | seen]
# s1：原S1的50个训练任务
# seen：前一批25个已经采集的任务
# 全取剩余91题；排序只用业务域、reference类型和固定SHA。
```

回放不能只对一下reward：

```python
actual = env.step(event['tool_call'])
for key in ['observation', 'exception',
            'state_before_sha256', 'state_after_sha256', 'state_changes']:
    require(content_sha256(actual[key]) == content_sha256(event[key]),
            'Event replay differs')
```

数据准入还要单独检查完整性：

```python
require(j['teacher_full_review'] and j['S1_full_review']
        and item['complete_candidate'], 'Wholepair review/termination gate')
a, b = branch(t, encoder), branch(s, encoder)
# 保留两条轨迹各自的历史和观察，不互换观察，不裁掉错误前缀。
```

## 10. 今晚三个知识点

1. **采集数、成功数、准入pair数是三件事。** 91次rollout、65个官方成功、23个新奖励差pair，各自回答不同问题。
2. **偏好标签不等于reward大小排序。** reward0可能含歧义或截断；reward1可能含错日期或错误回答。最终监督需要可解释的优劣关系。
3. **数据覆盖有多个层次。** 数量、业务域、工具序列、条件类型、失败机制、重复任务家族都要看，不能只增加样本数。

## 11. 面试追问（不给答案）

1. 为什么811/329得到reward1，却不适合当正确“不操作”示范？
2. 为什么91个任务只能产生23个新奖励差pair，而不是26个失败全部使用？
3. 为什么既有教师的reward1和历史审核不能代替重新检查chosen？
4. 同动作目标的1069/956，以及所有空reference的`[]`，分别该如何理解重复性？
5. 为什么最长8073能通过CPU编码，却仍要做GPU训练预检？

## 12. 下一步需要确认的路线

建议先对累计29个reward-gap做整批真实HF模板/mask和显存预检，再登记同数据chosen-only SFT与DPO对照。当前未登记训练步数，不自动训练。4个同奖励pair仍单独保留，不改旧loader绕过标签限制。

新主机按你的要求保持开机，采集进程已结束、SSH已关闭。GPU时价未知，实例继续占用的费用不包含在19分钟纯采集时间里。

## 13. ID、配置、日志、代码版本

- 执行：`S1-EXPAND-ACQUIRE-20261016-001`，commit `ebd0880da7cd983f51c8059d5abc35a281c39f7b`。
- 回放：`S1-EXPAND-REPLAY-20261016-001`；准入：`S1-EXPAND-REVIEW-20261016-001`。
- 采集配置：`configs/s1_preference_expansion.json`；审核协议：`configs/s1_preference_expansion_review.json`。
- 下一阶段数据入口：`configs/preference_expanded_data.json`，GPU_training_authorized=false。
- 原始日志/29成员归档/资源：`evidence/preference-expansion-20261016/`。
- 逐条判断与覆盖：`reports/preference-expansion-20261016/`。
- 完整报告：`docs/PREFERENCE_EXPANSION_20261016.md`。

两次GitHub404与一次本地统计片段语法错误均保留；没有删除后重跑模型。修复临时链接缓存后才启动唯一一次91题采集。
