# 项目约定

用户目标：真正掌握 trajectory → eval/failure analysis → post-training data → SFT/LoRA → DPO → 可选 online RL → generalization/cost 的完整机制。核心对照为相同训练预算的 random verified SFT 与 failure-targeted SFT。RL 不是项目成立条件。

## 当前授权

2026-09-04：完成租 GPU 前全部可做工作；结束后提供适合学习一个月的新手的学习材料，并考核。允许小型官方源码、任务数据、CPU 依赖和 tokenizer 准备；不租 GPU、不下载大模型、不使用付费模型 API、不做训练、不自动进入后续阶段。

## 固定边界

- 单卡上限 1×A800 80GB；候选约 8B，LoRA/QLoRA，有限 context。
- 总预算约 RMB 1000–2000；单次预计超过 RMB 30 必须明确获批。
- 保留旧 tau2 项目为 Hard-environment Base Qualification Audit，不操作旧目录。
- 只使用公开个人项目资料。公司数据、源码、技能、Prompt、API、测试及内部结论禁止混入。
- API key 只允许远端进程环境，不写文件/Git/日志/聊天。
- BFCL final cases 不用于任何训练、prompt 调试、taxonomy、pair、RL 或 checkpoint selection。
- 所有模型行为结论必须来自真实模型 rollout。脚本回放只证明工具/verifier 性质。
- 在线 RL 必须证明当前权重 rollout → reward → update → 新权重 rollout；离线轨迹不冒充 online。

## 训练与评价

- SFT 的 system/user/tool/environment 内容默认 labels=-100；assistant tool calls/response 是监督目标。
- DPO pair 共享任务与初始条件，各自工具 observation 仅作为 context；检查 policy-token log-prob mask 和冻结 reference 身份。
- S1/S2 控制模型、token、step、adapter、eval 和 seed；分别报告 processed/context/supervised tokens 和采集成本。
- 不能把 reward=1 等同高质量/grounded，也不能把 loss 下降等同 task success。
- 保留成功、失败、无效 run 原始证据；无效 run 不计能力指标，但计费用。

## 长期产物

维护 PROJECT_STATE、ENVIRONMENT_AUDIT、EXPERIMENT_PROTOCOL、FAILURE_TAXONOMY、DECISIONS、HYPOTHESES、COMPUTE_BUDGET、experiments/registry.jsonl 和 docs/daily/YYYY-MM-DD-learning-handoff.md。

每日结束停止新实验，handoff 应包含核心问题、前后状态、执行、变量、结果、代表轨迹、结论/推测、3–5 个代码函数导读、学习点、5 个无答案面试题、路线分叉及证据身份。

