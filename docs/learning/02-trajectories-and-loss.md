# 第二课：模型究竟学习哪些 token

一条 trajectory 是整个交互过程：初始任务、每次 assistant 决策、真实工具 observation、错误、状态变化、结束原因与 verifier。它不是只保留最终答案的一条文本。

进入 SFT 前，通常需要把 trajectory 整理成 messages，再通过模型的 chat template 转成文本和 token IDs。

```text
messages → chat template → input_ids → labels / loss mask → CE loss → 参数更新
```

今天实际验证到 input_ids/labels 和一个 toy loss 计算。真正的模型 forward、反向传播、LoRA 更新、保存和 reload 还没有发生。

## Context 与 target

| 内容 | policy 是否需要看见 | 默认是否参与监督 |
|---|---|---|
| system / user | 是 | 否，labels=-100 |
| 工具 schema | 是 | 否 |
| tool observation / environment feedback | 是 | 否 |
| assistant 的 tool call | 是 | 是 |
| assistant 的回复 | 是 | 是 |

`-100` 是交给损失函数的忽略标记，不是一个需要模型输出的词。一个 observation token 的 label=-100，不表示把它从 input_ids 删除。它仍能影响后面动作的预测；只是我们不要求模型去模仿环境生成那段 observation。

例如，搜索返回某个 email_id。后面的 assistant tool call 应该学会使用这个 ID。观察里的 ID 是上下文；调用参数里的 ID 是 policy 生成目标。相同字符串出现在不同角色时，训练作用可以不同。

## 今天的数字意味着什么

真实工具学习 fixture 共 4536 tokens，其中 89 个 assistant target，4447 个 context。长 schema 占去很多输入，但模型实际受监督的决策 token 很少。这只是一个例子，不能拿其比例代替整个训练集。

Qwen 模板会把工具输出包在 user 样式的 `<tool_response>` 块里。只看渲染后的“user”标题可能困惑：原 messages 的 role 仍是 tool，模板为它选择了特定格式。

我们使用固定 Qwen 模板与 tokenizer，依据 assistant 内容边界生成 labels，并拒绝正文中的 ChatML 分隔符注入。这不是适用于所有模型的万能 collator。正式训练时，必须再次比较实际 Transformers/TRL 的渲染与标签，不能仅凭今天的检查跳过。

## CE loss 的最低限度理解

模型在每个位置预测下一个 token。若某个正确 target 被赋予的概率很小，负对数概率就大；训练希望让正确 target 更可能出现。

```text
CE = - average(log p(正确的 assistant token | 前面的上下文))
```

只对未被 mask 的 target 求平均。实现时还要对齐 logits 与下一个 token 的 labels，不能错一位。今天用人造 log-prob=-2 得到 toy CE=2，这只是数学检查，不是 Qwen 的 loss。

LoRA 将部分大矩阵的更新写成低秩矩阵乘积，训练新增的小矩阵。它确实会改变 policy 参数；只改 prompt 或记录轨迹不会。理解 LoRA 不要求现在先学分布式训练。

## DPO 为什么必须保留两条分支

chosen/rejected 必须来自同一任务和相同初始条件。但它们可能调用不同工具，于是各自 observation 不同。不要把 chosen 的 observation 塞给 rejected，假装二者之后仍拥有同一个完整上下文。

每条轨迹的 policy 分数，是 assistant 生成 token 的条件 log-prob 之和。环境的 token 不参与这个分数。DPO 比较当前 policy 对两支的偏好变化，并与一个冻结 reference policy 比较。

```text
偏好改变量 = (当前 chosen 分数 - 当前 rejected 分数)
           - (reference chosen 分数 - reference rejected 分数)
DPO loss = -log sigmoid(beta × 偏好改变量)
```

长度会影响序列分数，需要审计，但“短/长”本身不是好坏标签。今天的学习 pair 中，正确轨迹更长，失败的 `Done.` 更短。这个 pair 来自 dev、由脚本产生，因此明确禁止作为正式训练数据。

## 你应能复述

解释为什么 observations 要保留在输入却不做监督目标；为什么更低 training loss 不能证明 Agent 更会完成任务；为什么 DPO 的 reference 必须是选定的冻结 checkpoint，而不是随手关闭 adapter 得到的另一个模型。
