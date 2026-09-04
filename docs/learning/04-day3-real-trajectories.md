# 第四课：从真实模型轨迹看 Post-Training 要解决什么

今天已经运行 Qwen3-8B：3 条 smoke、48 条 B0、24 条 B1，共 75 条真实模型轨迹。它们与前几课的脚本演示不同。但今天仍然没有参数更新，因此项目还没有完成 SFT/DPO。

建议先用 30–45 分钟读这一课，再读 DAY3_REPORT 的指标表。不会要求你立即读完全部原始 JSON。

## 1. 工具调用能执行，为什么任务还失败？

B0 的结构可执行调用率为 87/91，约 95.6%；任务成功却只有 11/48，约 22.9%。

真实例子：模型调用 `email_reply_email(email_id="last_email_id", ...)`。JSON 正确、工具名存在、参数是字符串，函数确实执行了；但数据库里没有这个 ID，返回 `Email not found.`，模型随后停止。

所以至少要分开：格式是否可解析、函数能否执行、参数是否正确、任务最终是否完成。只看第一项，会漏掉大多数 Agent 错误。

## 2. B1 到底改善了什么？

同 seed 的 B0 是 5/24，B1 是 8/24。三个新增成功都来自恢复。例如 task 0：

```text
B0：猜 last_email_id → Email not found → 结束，reward=0
B1：猜 12345678 → Email not found → 搜索邮件
    → 看到真实 ID 00000057 → 回复 → reward=1
```

B1 并没有消除最初的猜测，它让模型在错误后继续寻找信息。因此不能把“成功率提高”解释为“grounding 已学会”。这里没有新权重，变化来自通用 system 指令。

这也解释了成本：平均工具步数从 1.79 增到 2.92，平均耗时从 6.27 秒增到 8.45 秒。更愿意继续尝试，既可能成功恢复，也可能多做错误动作。

## 3. 看过一个字符串，不代表知道它是哪种标识符

用户说删除 Quinn Taylor。模型把 `Quinn Taylor` 填进 customer_id。它确实在用户文本中看过这个字符串，但那是姓名，不是数据库 ID。

另一种错误正好相反：模型从查询结果中取到了真实 customer_id，却忽略“属于 Sofia”的条件，删除了别人的客户。此时 ID 有来源，但目标选错了。

检查顺序可以是：参数需要哪种东西？这个值是什么类型？从哪里获得？在当前状态是否存在？是否对应用户要求的对象？

## 4. 为什么 reward=1 仍要审计？

task 12 的实际状态不需要修改。模型却用虚构的 `leila@example.com` 查询，得到空列表，再停止。最终状态没有变化，因此 reward=1。

这不是一条值得直接模仿的高质量成功轨迹。随机从 reward=1 里取 SFT 数据，可能把虚构参数也教给模型。以后 S1/S2 必须共用清楚的质量门槛，不能只看 reward。

本轮 B0 与 B1 都没有调用 company_directory；邮箱槽位错误仍未解决。这是后续数据覆盖要回答的问题，而不是再追加一条口号就自动解决的问题。

## 5. 一个真实 preference pair，以及它的限制

打开 `evidence/day3/real_preference_learning_pair.json`。这是同一个 task 18、相同初始 system/user/tools/state：

- seed 43：先查错新名称，随后扩大查询、找到事件并改名，reward=1。
- seed 42：没有找到正确事件便结束，reward=0。

前者是成功恢复，不是无错误的专家演示。它是否适合监督全部错误前缀，需要正式数据设计决定。另外两条都来自 **dev**，所以本文件明确标记 training_eligible=false，只用于学习。

不能把 B0/B1 的对比记录未经说明就当作同 prompt DPO pair，因为 B1 多了一段 system 指令。若未来做 prompt distillation，必须明确保存生成上下文与统一训练上下文，并重新审计。

## 6. 进阶：今天发现了四个 token 的对齐问题

真实 pair 的 chosen/rejected 分别生成 275/161 tokens；完整 messages 经过目前的 role-mask 后，监督 token 数却是 279/165。

差异来自四个空 non-thinking prefill tokens。实际生成时它们已由模板放进输入；完整 conversation 渲染时，最后一个 assistant 的这些标记又被算进 target。我们逐 token 核对过：在这两个样例中去掉这段固定 prefill 后，target IDs 才与实际输出 IDs 一致。

这说明：只检查“user/tool 的 label=-100”还不够，还要问“这些 target 真的是 policy 生成的吗？”未来做 DPO 时，还需核对逐轮实际 conditioning，不能只把完整对话拼成一串就宣称与 rollout 概率完全相同。

目前没有开始训练，正适合先发现并解决这些问题。

## 现在你只需读五处函数

| 文件 → 函数 | 输入 → 输出 | 作用 |
|---|---|---|
| scripts/run_day3.py → inference_trajectory | task/policy/seed → 完整真实轨迹 | 主循环与预算 |
| veriagent/policy_protocol.py → parse_tool_calls | 模型文本 → calls/errors | 把生成文本变成可执行请求 |
| veriagent/environment.py → WorkplaceEnv.step | action → observation/diff | 真实工具执行 |
| vendor/Gym/resources_servers/workplace_assistant/utils.py → is_correct | 预测/参考 actions → bool | 官方 reward |
| veriagent/token_mask.py → TokenMaskInspector.inspect | messages/tools → ids/labels | 训练 target 边界 |

## Day 3 考核：请用自己的话回答，不附答案

1. 本轮模型确实运行了，为什么仍不能说已经完成 Post-Training？用两个证据回答。
2. 为什么 95.6% 的结构可执行调用率，可以与 22.9% 的任务成功率同时成立？举一个真实例子。
3. B1 新增三个成功说明了什么，又不能说明什么？为什么还要看绝对错误数与分母？
4. `Quinn Taylor` 被填进 customer_id，与“使用真实 ID 删除错误客户”有什么区别？
5. 那四个 prefill tokens 为什么会影响你对 SFT/DPO 数据完整性的判断？如果暂时不理解，可先指出生成和训练各自的输入/输出边界。

提交这五题后，Codex 会逐题评分与追问；然后再做代码定位和实验设计题。当前没有提前判定你通过。
