# Q0 CPU 环境审计（2026-09-04）

结论：官方工具核心可在本地 CPU 运行；数据、状态和 tokenizer 准备已完成。严格 tool-combination held-out 尚未获得资格，GPU 阶段不放行。没有运行 LLM，也没有更新参数。

## 版本与来源

| 对象 | 固定身份 |
|---|---|
| Gym | `83b3980b9c04379d72bbf59592d7846630f706bf` |
| NVIDIA dataset | `c86a908379e0a361a573c395e175d3c1aa128e6c` |
| Qwen3-8B tokenizer/config | `b968826d9c46dd6066d109eabc6255188de91218`；无权重 |
| BFCL main 审计快照 | `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`；仅文档 |
| BFCL V4 榜单复现快照 | `f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`；页面标 2026-04-12，包 `2025.12.17` |

逐文件 URL、Git blob 和 SHA256 在 `evidence/sources/manifest.json`；tokenizer 身份在 `configs/tokenizer.json`。下载的 193 个源码/数据/文档文件总计 33,135,564 bytes，包含完整 Workplace 任务文件；tokenizer/config 11,433,353 bytes。未下载其他数据集、BFCL cases 或模型权重。

官方来源：[Gym](https://github.com/NVIDIA-NeMo/Gym/tree/83b3980b9c04379d72bbf59592d7846630f706bf)、[NVIDIA dataset](https://huggingface.co/datasets/nvidia/Nemotron-RL-agent-workplace_assistant/tree/c86a908379e0a361a573c395e175d3c1aa128e6c)、[BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html)。

## 已验证事实

- 实际读取 train 1255、validation 545 行；各自 ID 和规范化问题均唯一，跨官方 split 未发现规范化完全相同的问题。两边的数字 ID 会重复，因此项目 task_uid 包含 revision/split/row index。
- 每个 split 在五个业务类别中等量：train 每类 251、validation 每类 109。
- 每条数据暴露 27 个 schema。五个可变业务状态库，加一个只读 Directory；实现是 Python/pandas 内存状态，不要求外部数据库服务。
- train 中 170 条 reference 为空，其余 1085 条每条只使用一种 reference 工具；validation 对应 71 与 474。reference 不含完整 prerequisite lookup。
- 官方旧 README 的 690/1260 不是当前文件计数；新 prepare 入口引用不同数据源且生成嵌套 verifier_metadata，与当前顶层 TaskData 不符。CPU Pydantic 验证证实该形状需要适配。
- 默认 max_steps=6 计算模型轮次。一个轮次可能有多个调用，不能把它当成严格六次工具调用。
- 官方 verifier 重放 predicted 和 ground_truth，再比较五个最终状态表，输出 0/1；不评分最终自然语言或 identifier 来源。
- 工具抛异常可以作为错误文本返回，HTTP 200 不意味着业务操作成功。unknown-call 后恢复成功可以得到 reward=1，不能因此把所有 recovery 当坏数据。
- analytics_create_plot 增加路径记录，但不实际生成 PNG。这是模拟业务效果，不应宣传为真实绘图系统。

## 实测证据

| 实验 | 原始结果 | 可支持的结论 |
|---|---|---|
| Q0-DATA-20260904-001 | 完整结构统计、原始 split manifest | 数据身份与结构；不能证明语义无近重复 |
| Q0-ENV-20260904-001 | 24 个 dev task，138 条脚本轨迹；reference/repeat 均 24/24 reward=1；必要动作遗漏 18/18 reward=0；无关写入 24/24 reward=0 | 已抽查的执行、reset、隔离与重放性质成立 |
| 同上 | 138/138 online/replay 状态一致；0 个无效记录 | 当前脚本样本一致，不代表所有参数空间已穷尽 |
| 同上 | 6/24 空动作也得分；unknown-prefix+reference 24/24 得分 | reward 不保证前置观察或无错误过程 |
| Q0-TOKENS-20260904-001 | 955 个 training/dev 初始输入 4112–4153 tokens；学习轨迹 4536 tokens，其中 89 supervised、4447 context；9 个检查通过 | 这些输入及学习轨迹适合 8K；不是所有模型轨迹的长度保证 |
| Q0-CONTRACT-20260904-001 | 8 个接口/字段检查通过；208 个跨 split 高词面相似候选，涉及 148 个 train rows | 本地适配器契约可用；相似性需要保守处理，不等同泄漏证明 |
| Q0-SPLIT-20260904-003 | 保守隔离后剩余 flagged training edges=0；pilot reference 最多 4 次调用 | 已发现的风险边被排除；仍不能证明不存在其他语义近重复或额外前置步骤 |

原始结果在同名 `experiments/<ID>/` 下，均含 config、identity、result。所有轨迹显式标记 SCRIPTED，不计任何 LLM task success。

## reward 的边界

DEV task 709 要求删除未来的某类会议。真实 calendar_search_events 返回 `No events found.`；查询后结束和直接结束都得 reward=1。这不证明 reference 标错：不修改状态可能正是正确结果。它证明奖励无法区分“查证后决定不做”与“碰巧猜对”。

reference 与自己重放得到 1 也不是语义真值证明：同一个错误 reference 可以自洽。我们另测了遗漏、无关状态变化、lookup 和 reset，但未穷尽所有任务的语义标注。

## 数据清单最终状态

以 `experiments/Q0-SPLIT-20260904-003/split_manifest.json` 为当前候选清单：

| Pool | 数量 | 状态 |
|---|---:|---|
| training_candidate | 743 | 无训练授权 |
| development | 85 | 可用于开发与学习 |
| checkpoint_validation | 93 | 仅未来 checkpoint selection |
| composition_reserve_UNQUALIFIED | 181 | 不能报为已验证的组合泛化测试集 |
| train 侧保守隔离 | 153 | 包括相似候选及模板亲缘任务，原数据保留 |
| official_validation_SEALED | 540 | 项目过滤子集，不是完整官方 545 条成绩 |
| 已暴露 dev 的官方验证亲缘任务隔离 | 5 | 保留暴露历史与原任务 |

原始清单未改写。SPLIT-001 因 no-op 抽样过度偏向 Analytics 被 SPLIT-002 取代；交付审查又发现其中有 7 次 reference 调用的任务，SPLIT-003 在模型运行前将 reference 调用上限设为 4，为查询/结束预留轮次。这些是计划修订，不是模型失败或无效基础设施 run。最终 pilot=20 个非空 reference+4 个空 reference，类别分布 Analytics 6、Calendar 5、CRM 4、Email 4、Project 5。该筛选仍不保证所有任务的额外 prerequisite 均能在六轮内完成，必须单独归因预算限制。

## 组合泛化结论：未通过资格门槛

schema 中看过工具，不等于训练时执行/监督过该工具。参考动作序列也不等于可观察 planning 轨迹。实际 task 0 的检索→回复证明任务可能需要多工具，但不能据此证明能分出“每个工具都训练过、特定组合没训练过”的足量独立任务族。

不能通过打乱可交换动作的顺序制造组合泛化结论。当前 181 条仅预留，未自动生成新任务或修改语义。路线选择须在学习后确认：收窄主张、单独补充受控组合任务，或重选环境。

## 官方训练/BFCL 与未验证项

NVIDIA 的 Workplace GRPO 示例是 Nemotron Nano v2 9B，1 node×8 GPUs，64 prompts×16 generations；不是单卡方案。官方 offline SFT/DPO 教程是 experimental 的数据处理示例。官方教程建议训练前后测 BFCL v3，但本轮没有确立可独立归因于 Workplace 的数值增益证据。

原始链接：[RL 配置](https://github.com/NVIDIA-NeMo/RL/blob/4601ba2c646ec40e5928c780fc0051a842328eba/examples/nemo_gym/grpo_workplace_assistant_nemotron_nano_v2_9b.yaml)、[BFCL 建议](https://github.com/NVIDIA-NeMo/Gym/blob/83b3980b9c04379d72bbf59592d7846630f706bf/fern/versions/latest/pages/training-tutorials/nemo-rl-grpo/multi-node-training.mdx)。

CPU path 是 `veriagent` 薄适配器直接调用未改动的官方工具/verifier。本地 HTTP 只测了进程内 ASGI，未部署公网，也未安装/运行完整 NeMo HTTP/Ray launcher。Windows CPU 通过不代表 Linux GPU serving/训练栈兼容。

Qwen 性能、GPU utilization/VRAM、SFT/DPO step time、真实 CE/LoRA update、adapter save/reload、GRPO 全部未测。BFCL cases 保持未下载/未评测。数据许可按 NVIDIA 数据卡 CC BY 4.0 记录，同时保留 Gym 的 Apache 2.0 元数据冲突；不重发布成统一 Apache 数据。
