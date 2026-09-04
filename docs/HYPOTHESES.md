# Hypotheses

| ID | 假设 | 当前证据结论 |
|---|---|---|
| H0 | 环境工具核心能在低成本 CPU 上执行真实状态变化 | 已抽查支持：138 scripted trajectories，reset/isolation/重放通过 |
| H1 | official reward 能充分代表高质量 grounded task completion | 不支持充分性：no-op 猜中得分、最终文本未评分；不意味着状态 reward 无用 |
| H2 | reference tool sequence 可直接构造组合 held-out | 不支持：train 170 空 reference，其余每条只有一种 reference 工具 |
| H3 | 初始工具 schema 会让 8K context 不可用 | 当前初始输入不支持此担忧：955 条均 4112–4153；长 rollout 仍未测 |
| H4 | Qwen3-8B 在正向写任务上具有非退化成功/失败分布 | 未测 |
| H5 | 相同训练 token 下 failure-targeted SFT 优于 random verified SFT | 未测；核心正式研究问题 |
| H6 | Verified trajectory DPO 可利用失败中的相对信息 | 未测；CPU 仅验证表示与 toy arithmetic |
| H7 | 单卡 online GRPO 在预算内提供额外收益 | 未测；必须先完成 SFT/DPO 和 online cost probe |

CPU qualification 只能回答 H0/H1/H2/H3 的一部分，不能推出 H4–H7。
