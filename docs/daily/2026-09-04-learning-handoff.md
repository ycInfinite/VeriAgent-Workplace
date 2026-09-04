# 2026-09-04 Learning Handoff：CPU 审计与 Day 3

今天的模型实验已结束。75 条真实轨迹已取回，关机命令成功且 SSH 由远端关闭；接下来只做学习、考核和路线讨论，不自动训练。此前 CPU/preparation handoff 保存在 2026-09-04-cpu-handoff-history.md。

1. **核心问题**：Qwen3-8B 是否能在单张 4090 上完成真实工具循环？B0/B1 的失败是什么？通用提示的收益来自哪里？这些轨迹能否直接用于训练？

2. **开始前状态**：CPU 工具/verifier/split/tokenizer 已审计，没有实际模型运行。用户随后提供个人 AutoDL 实例并要求完成 Day 3，确认 1.98 元/小时。既定 24 题、两个 B0 seeds、一次条件 B1，不做参数更新。

3. **实际执行与文件**：远端复用 torch 2.8+cu128，安装 Transformers 4.56.2 等轻量所需依赖；下载并验证固定模型；上传白名单源码/24 条 dev；运行 smoke/B0/B1；取回校验、语义复核、关机。主要代码为 scripts/run_day3.py、build_day3_bundle.py、verify_model_integrity.py、veriagent/policy_protocol.py、review_day3_metrics.py；主报告是 docs/DAY3_REPORT.md。

4. **变量/控制**：B0 为固定 policy 的 seed 42/43；B1 只增加此前登记的通用 system 指令，使用 seed 42。同模型 revision、工具、世界状态、用户任务、8K context、6 个模型轮次、累计 2048 output tokens。B1 24 条初始消息逐一核对，其他输入未改变。

5. **原始结果**：smoke 1/3；B0 11/48，动作任务 5/40；B1 8/24，动作任务 5/20。主要配对为 B0 seed42 5/24 → B1 8/24，改善 task 0/1/18，无退化。75/75 轨迹有效且 online/replay 一致。Torch allocated 峰值 17.17 GiB，采样 GPU used 峰值 19.80 GiB。会话约 52.3 分钟、1.73 元估算；模型运行部分 9.47 分钟、0.31 元，已包含在会话费用中。

6. **代表轨迹**：task 0 的 B1 先猜 ID 再查到真实 ID 后成功；task 18 的 B0 seed43 是成功恢复，seed42 是失败；task 12 在虚构邮箱查询后仍 reward=1；task 1063 使用真实但不符合用户条件的客户 ID；task 669/952 的输入超过 context。源文件均为三个模型实验目录中的 trajectories.jsonl。真实 preference 学习 pair 在 evidence/day3/real_preference_learning_pair.json，明确 training_eligible=false。

7. **路线结论**：硬件/真实交互链通过。B0 单独未通过成功任务数量门槛。B1 是有条件候选，收益主要是恢复；CRM/PM 动作任务仍全失败，B1 仅单 seed。不能直接开始大规模数据生成或把本批 dev 数据投入 SFT。严格组合泛化仍未合格。

8. **尚未支持**：没有 SFT/DPO/GRPO 参数更新；没有证明 B1 的一般性或显著收益；没有证明全局无泄漏；没有 BFCL/final 泛化成绩。语义标签由 Codex 逐条复核，没有独立人工标注。没有访问真实账单，费用未计入更早的实例开机和独立存储。

9. **最应该读的五处函数**：

| 文件 → 函数 | 输入 → 输出 | pipeline 作用 |
|---|---|---|
| scripts/run_day3.py → inference_trajectory | policy/task/seed → 完整轨迹 | 模型决策、上下文和预算循环 |
| veriagent/policy_protocol.py → parse_tool_calls | 模型文本 → calls/errors | 结构化可执行请求 |
| veriagent/environment.py → WorkplaceEnv.step | action → observation/error/diff | 执行真实官方工具 |
| vendor/Gym/resources_servers/workplace_assistant/utils.py → is_correct | 预测/参考动作 → bool | executable reward |
| veriagent/token_mask.py → TokenMaskInspector.inspect | messages/tools → ids/labels | 训练 target 边界检查 |

10. **今晚三个知识点**：typed grounding 与目标约束的区别；reward、恢复和高质量轨迹的区别；逐轮 policy 输入/输出与 SFT/DPO target 的对齐。新发现：真实 pair 的生成 token 为 275/161，而 canonical targets 为 279/165，四个强制 non-thinking prefill tokens 在实际生成时属于输入。这是训练前必须处理的门槛。

11. **五个面试追问，不附答案**：

- 为什么结构可执行调用率 95.6%，任务成功率却只有 22.9%？
- 如何从原始日志证明 B1 改善的是恢复，而不是第一次决策？
- 一个 ID 来自 observation，为什么仍可能操作错误对象？
- 为什么 grounding 错误比例下降时，还必须报告绝对错误数和分母？
- 为什么四个模板插入的 token 会影响对 SFT/DPO 数据完整性的判断？

12. **下次路线分叉**：是否将 B1 冻结为共同 baseline；如何为姓名→邮箱、目标约束、查询粒度取得合格的 training-pool 轨迹；如何补足 composition split；训练 cost probe 前怎样解决逐轮模板/mask 对齐。不自动增加 B1 seed、换大模型或开启训练。

13. **证据身份**：模型运行代码 commit cb4067c3e0dd21723d5664e7ccd27cdd3120c51e；模型 revision b968826d9c46dd6066d109eabc6255188de91218；Gym commit 83b3980b9c04379d72bbf59592d7846630f706bf。实验 ID：Q0-SMOKE-20260904-001、Q0-B0-20260904-001、Q0-B1-20260904-001。各目录含 config.json、identity.json、trajectories.jsonl、gpu_samples.jsonl、result.json。完整账本 experiments/registry.jsonl；当前复核 reports/day3-reviewed-v2；费用/完整性 evidence/day3。准备阶段一次 Hub 元数据校验失败保留在 setup_attempts.jsonl 和原始日志中，没有模型 invalid run。

学习入口：docs/learning/04-day3-real-trajectories.md。考核状态仍是未开始、未评分；提交该页五题后再逐题评分与追问。先前 CPU 记录保留，不能把脚本轨迹和真实模型轨迹混算。

交付补充：最终本地 Git 提交的自动权限审核两次超时，命令未执行。文件均已保存，但新增产物尚未提交；实验运行前的代码 commit 已固定。这个版本保存阻碍不计入模型 invalid run，也没有产生新的 GPU 费用。
