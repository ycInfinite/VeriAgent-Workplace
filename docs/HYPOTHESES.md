# Hypotheses

| ID | 假设 | 当前证据结论 |
|---|---|---|
| H0 | 环境工具核心能在低成本 CPU 上执行真实状态变化 | 已抽查支持：138 scripted trajectories，reset/isolation/重放通过 |
| H1 | official reward 能充分代表高质量 grounded task completion | 不支持充分性：CPU no-op 检查及真实 task 12 的虚构邮箱查询仍 reward=1；最终文本未评分；不意味着状态 reward 无用 |
| H2 | reference tool sequence 可直接构造组合 held-out | 不支持：train 170 空 reference，其余每条只有一种 reference 工具 |
| H3 | 初始工具 schema 会让 8K context 不可用 | 当前初始输入不支持此担忧：955 条均 4112–4153；长 rollout 仍未测 |
| H4 | Qwen3-8B 在正向写任务上具有非退化成功/失败分布 | B0 写任务 5/40、仅 3 个有成功的任务，未达门槛；B1 单 seed 5/20 为有条件候选，仍需稳定性/弱域数据方案 |
| H5 | 相同训练 token 下 failure-targeted SFT 优于 random verified SFT | 未测；核心正式研究问题 |
| H6 | Verified trajectory DPO 可利用失败中的相对信息 | 未训练；新增真实同 prompt dev pair 演示，并发现 forced-prefill / per-turn likelihood 对齐门槛 |
| H7 | 单卡 online GRPO 在预算内提供额外收益 | 未测；必须先完成 SFT/DPO 和 online cost probe |
| H8 | 一版通用 B1 提示能减少失败 | 当前 paired cohort 从 5/24 到 8/24，三条都是恢复；不构成一般或显著收益证明，冗余和 tokens 增加 |

Day 3 不涉及 H5/H6/H7 的参数更新。初始 prompt 都能放进 8K，不代表完整 rollout 能放进；两任务的部分轨迹触发 context cap。官网/API 支持能力不替代真实实验结果。
