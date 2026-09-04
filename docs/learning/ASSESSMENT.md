# 学习后考核（无答案版）

当前状态：尚未开始，未评分。允许查本项目文件；请用自己的话说明机制和证据路径。先提交 A1–A5，Codex 再追问 B/C。需要思考的地方可以明确写“不确定”，不要求装作已经懂。

## A：机制理解，30 分

每题 6 分：准确概念 2、能关联本项目 2、指出证据边界 2。

1. `reference:reward=1` 有 24 条。能否据此说 Qwen3-8B 成功率 100%？请说明谁产生了这些动作，以及目前实际验证到了哪一层。
2. `search_emails` 没有改变邮件表，它为什么仍可能是必要步骤？state 与 observation 有什么区别？
3. 为什么一个 no-op 任务中“查过再结束”和“直接结束”都能 reward=1？这能证明任务标错吗？
4. tool observation 的 labels=-100 是否意味着模型看不到它？同一个 email_id 在 observation 和 assistant 参数中出现时有什么不同？
5. DPO 中两条轨迹为什么只需要共享初始任务，而不应强行共享后续所有 observations？

## B：证据追踪，40 分

1. 20 分：沿 `grounded_fixture_DEV_ONLY.json` 找到查询返回的 ID、之后使用该 ID 的动作、状态变化和 verifier；为每一步标明对应代码文件/函数。再说明这条 fixture 为什么不能进入训练集。
2. 20 分：在 `token_labels_DEV_ONLY.csv` 中各找一个 context token 和 target token，给出位置、label、角色及原因。解释 processed/supervised token 数量分别代表什么，并指出真实训练前还缺哪三个检查。

## C：实验设计，30 分

选题：比较“随机成功轨迹 SFT”与“failure-targeted SFT”。按项目八字段写一张实验卡。必须写清训练 token 口径、checkpoint selection 使用哪个 pool、无效 run 怎样处理、支持/反驳假设的证据，以及什么情况下应停止。

评分：问题/变量清楚 6；控制变量合理 6；指标/分母 6；泄漏和归因 6；成本/停止分叉 6。

## 通过标准与补课

总分至少 80，并通过三项关键检查：不混淆脚本与模型能力；不把 final cases 用于训练/调参；不把工具 observation 当作默认 policy target。关键项未过时，先讲解对应实际轨迹，再用不同例子复测。

评分必须在收到你的答案后进行。考核通过只意味着可以进入下一轮项目讨论，不自动授权租 GPU 或训练。
