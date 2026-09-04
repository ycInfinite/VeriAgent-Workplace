# Failure taxonomy：尚无模型分布

以下是待实证的标签定义，不是 Base failure 结论。当前所有轨迹为脚本，不能用于估计模型各类失败占比。

| 标签 | 判定证据 | 排除/注意事项 |
|---|---|---|
| wrong_tool | 未注册工具，或观察/任务证据表明选择错误 | 不因与 reference 顺序不同判错 |
| wrong_argument | JSON/schema 不合法，或状态证明参数语义错误 | HTTP 200 仍可能包含工具错误 |
| identifier_hallucination | ID 不存在且无来源依据 | 与存在但未 grounding 的 ID 区分 |
| ungrounded_identifier | 用户与前序 observation 中无可追溯来源 | 正确猜中 ID 也不自动算 grounded |
| missing_prerequisite | 尚未获取做出该决策需要的状态/实体信息 | 不机械要求某个唯一查询工具 |
| redundant_action | 无新增信息/必要状态效果，也无合理恢复目的 | 状态改变后的重复查询可能合理 |
| retry_loop | 相同参数/相同结果/无状态推进的连续重复，初稿阈值 3 次 | 正常纠错不是循环 |
| premature_termination | policy 主动停止，必需任务仍未完成 | 达到 token/round cap 单列 |
| failure_after_partial_progress | 已完成部分目标，后续动作使最终目标失败 | partial progress 不折算正式成功 |
| unsupported_completion_claim | 自然语言宣称完成但观察不支持 | 官方 reward 不直接检测它 |
| infrastructure_invalid | 模型 API/环境进程/工具适配等非 policy 原因失效 | 保留原始记录，不计能力指标，计费用 |
| attribution_pending | 尚不能区分模型错误、数据歧义和环境问题 | 不强行塞入模型 failure 标签 |

每条标注记录 task_uid、trajectory_id、最早因果错误步骤、支持的 observation/state diff、主要标签、次要标签、置信度和复核说明。优先报告 earliest causal failure，而非把每个后续症状都算一次主因。

CPU 发现的 noop blindness、未评分的自然语言、plot-path simulation 属于环境/评分覆盖发现，不是 Qwen 失败。
