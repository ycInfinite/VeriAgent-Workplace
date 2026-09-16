# Hypotheses

2026-09-16 实时价格检查仅建立候选卡的价格比，不建立跨卡速度或训练效果结论。PRO相对普通A800的成本盈亏点约1.249倍吞吐，H800相对PRO约1.430倍；实际是否达到未测。研究假设与SFT资格不因查价而升级。

2026-09-10 GitHub同步：20个固定ref执行文件哈希验证通过，仅支持代码传输与部署身份一致性；没有新模型或训练证据，不改变SFT/DPO/RL效果假设。

2026-09-10 无卡远端证据：支持固定模型文件、真实 Transformers tokenizer 与工具 CPU 执行准备可用；20/20 prompt/IDs 一致、脚本 task565 状态变化/reset 通过、PEFT等导入通过。仍没有 SFT CE/梯度/参数更新或重载实测，不升级 H5/H6/H7，也不把脚本 smoke 算模型成功。

2026-09-10 新实验 SFT-PREP-20260910-001 支持“逐轮编码能重建本批已保存输入与实际 target，且阻止 dev 进入训练”：200/200 次生成通过，75/75 dev 拒绝，7/7 负向检查通过。尚未执行真实 trainer CE、更新或重载，H5/H6/H7 仍未获得训练效果证据。

2026-09-10：按用户更正直接进入 SFT/LoRA 学习，已给出未执行的教学代码。无新训练或评测结果；学习者自述基础基本掌握，正式评分仍为空，研究假设不因材料发布而升级。

2026-09-08：仅整理学习合订本，无新增模型/训练证据，既有假设结论不升级。下表 H3 的历史措辞同步为已保存的 Day 3 结果。

同日代码详解补充只引用已有源码与轨迹；CE/DPO 数学算例明确为教学示意，不计入 H5/H6 的训练证据。

同日赛事检索：赛事主办方、赛程与人数不构成本项目能力或学习成效证据，H0–H6状态不因赛事推荐改变。Skills/Prompt竞赛也不能自动支持参数后训练能力结论。

ARC后续澄清仅更新求职目标与赛事偏好；未读取用户ARC方案，不能推断其已做参数训练，现有研究假设仍不变。

| ID | 假设 | 当前证据结论 |
|---|---|---|
| H0 | 环境工具核心能在低成本 CPU 上执行真实状态变化 | 已抽查支持：138 scripted trajectories，reset/isolation/重放通过 |
| H1 | official reward 能充分代表高质量 grounded task completion | 不支持充分性：CPU no-op 检查及真实 task 12 的虚构邮箱查询仍 reward=1；最终文本未评分；不意味着状态 reward 无用 |
| H2 | reference tool sequence 可直接构造组合 held-out | 不支持：train 170 空 reference，其余每条只有一种 reference 工具 |
| H3 | 初始工具 schema 会让 8K context 不可用 | 初始输入不支持此担忧：955 条均 4112–4153；Day 3 已测多轮，task 669/952 的部分轨迹触发 context cap，初始可容纳不保证整条可容纳 |
| H4 | Qwen3-8B 在正向写任务上具有非退化成功/失败分布 | B0 写任务 5/40、仅 3 个有成功的任务，未达门槛；B1 单 seed 5/20 为有条件候选，仍需稳定性/弱域数据方案 |
| H5 | 相同训练 token 下 failure-targeted SFT 优于 random verified SFT | 未测；核心正式研究问题 |
| H6 | Verified trajectory DPO 可利用失败中的相对信息 | 未训练；新增真实同 prompt dev pair 演示，并发现 forced-prefill / per-turn likelihood 对齐门槛 |
| H7 | 单卡 online GRPO 在预算内提供额外收益 | 未测；必须先完成 SFT/DPO 和 online cost probe |
| H8 | 一版通用 B1 提示能减少失败 | 当前 paired cohort 从 5/24 到 8/24，三条都是恢复；不构成一般或显著收益证明，冗余和 tokens 增加 |

Day 3 不涉及 H5/H6/H7 的参数更新。初始 prompt 都能放进 8K，不代表完整 rollout 能放进；两任务的部分轨迹触发 context cap。官网/API 支持能力不替代真实实验结果。
