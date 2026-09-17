# 首轮 SFT 开训前准备

状态：**数据、CPU 准入、两组训练配置、训练入口、开发集评估入口和 GitHub 部署清单已准备完成。没有开机、调用新模型 API 或更新参数。**

本轮准备的是小规模 S1/S2 开发对照。已完成的 8 步 probe 和 adapter 保留；两组未来均从同一份原始 Qwen3-8B 新建 LoRA，不接着那个 probe adapter 训练。

## 数据为什么没有直接用 629 条

629 是机械筛查未报警的数量，不是整条语义质量合格数。本轮先固定审核池：575 条“机械未报警且非空 reference”的轨迹中，各业务域按固定哈希顺序选 30 条，共 150 条。名单在逐条判断前固定，没有根据审核通过率补选。

这 150 条的所有可见 assistant 决策、工具参数、observations 和最终回答已逐条查看，必要的数值计算另行复算。结果为 **137 条通过、13 条暂缓**，审核者为 Codex，尚无独立人工复核。

| 业务域 | 完整审核 | 通过 |
|---|---:|---:|
| Analytics | 30 | 27 |
| Calendar | 30 | 28 |
| CRM | 30 | 30 |
| Email | 30 | 23 |
| Project management | 30 | 29 |

暂缓包括：6 条未充分验证最新邮件的分页范围；3 条数值汇总不准确；1 条相对日期边界未解决；1 条跨域 ID 误用；1 条多余的越界分页；1 条宣称将进行、却未执行的额外核验计划。其中后三类属于保守的整条质量控制，不篡改原官方 reward。

例子：task263 用 task_id 查询日历工具；task83 把真实流量总数 246/46/48/109 算成了 248/48/49/104。两条原 reward 都是 1，仍不进入 SFT。没有删除错误轮次、重写答案或只监督正确片段。

全部新增 723 条均有准入状态：137 条批准，586 条本阶段暂不准入。后者包括 13 条本次语义暂缓，以及机械失败、空 reference 专项未完成和未纳入本轮逐条审核的轨迹。**不能把未审样本写成已经判错，也不能说全部 629 条已完成语义审核。** 原 20 题和此前 Max 数据继续保留，本对照不混用它们。

## 已冻结的对照

| 控制项 | S1：分层随机 SFT | S2：Failure-targeted SFT |
|---|---:|---:|
| 任务 | 50，各业务域 10 | 50，各业务域 10 |
| 完整 assistant 轮次 / epoch | 155 | 155 |
| Epoch | 2 | 2 |
| Optimizer updates | 310 | 310 |
| 总 processed tokens | 1,425,440 | 1,415,914 |
| 总 supervised tokens | 28,546 | 29,114 |
| 微批量 / 梯度累积 | 1 / 1 | 1 / 1 |

两组重合 16 个任务，共 84 个不同任务。S1 是在已批准池中按域随机抽样，不是从全部 743 题无条件抽样。S2 使用已观察到的 Day 3 failure 作为依据，优先覆盖目录查邮箱、实体查询后操作、多目标处理、过滤条件组合和时间范围。

S2 的评分是公开冻结的启发式，不是学出来的因果权重：目录 grounding 4 分、实体查询 2 分、多目标 3 分、组合过滤 2 分、时间范围 2 分。使用固定约束选择整条轨迹，评分从 S1 的 258 提高到 S2 的 339。评分更高只证明选择确实偏向这些行为，**不证明训练后模型更好**。

Processed tokens 相差 -0.67%，supervised tokens 相差 +1.99%。本轮是近似匹配预算，不能在报告里改写成“训练 token 完全相同”。更新次数、域配额、模型、LoRA 和 seed 相同。它是第一轮可控开发实验，不是最终严格泛化结论。

固定参数：Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`，BF16，LoRA rank16 / alpha32 / dropout0，7 个已验证投影模块，43,646,976 个可训练参数，AdamW，lr=5e-5，weight decay=0，clip=1，seed42，常数学习率、不 packing、不截断。两组最长实际序列 7,208，小于 8,192。

## 训练完整性

采用逐 assistant 轮次训练：一个完整轨迹拆成多个样本，但每个样本都保留该决策之前的完整上下文，整条轨迹的每个 assistant 轮次都会被监督。它不是之前被否决的“只挑正确片段”。

```python
input_ids = prefix_ids + target_ids
labels = [-100] * len(prefix_ids) + target_ids
# prefix 包含 system、user、历史assistant和真实tool observations。
# target 是本轮完整assistant响应/tool calls，含EOS；不包含模板分隔换行。
```

DeepSeek 输出按固定学生模板重新编码，不冒充 DeepSeek 采样 token IDs。未来真实 forward 的第一步还会核对 shifted CE：`logits[:, :-1]` 对 `labels[:, 1:]`，只对非 -100 标签计分。每步检查有限非零梯度；最终检查 LoRA 变化、冻结参数抽样不变和 adapter 保存重载后的 logits/greedy IDs 一致。

本地 20 项 CPU 检查已通过：两组原始轨迹到模板/IDs/labels 的重建、整条完整性、source/pool/review 防错、禁止监督 context、禁止局部删除 target、解析式 CE mask 检查、旧 Bailian 两轨迹 8 轮 / 582 target tokens 回归检查。CPU 检查未加载模型，不能声称这次 310 步训练或新数据的 GPU 显存已实测。

## 评估已经准备到什么程度

复用原来的固定 development24，不换题。未来分别对 BASE_B1、S1、S2 运行 seed42/43，各 48 条真实 rollout。所有条件均保持 B1、non-thinking、8,192 context、6 轮、768 每次输出、2,048 累计输出。会重新跑同设备的 BASE_B1，不把历史 B0 或不同 seed 的旧结果混成配对基线。

所有训练只保存并使用固定最终 checkpoint，不根据这 24 题挑中间 checkpoint。比较入口检查 cohort/seed/代码/软件/GPU 一致，保留 paired task-cluster 不确定性；语义错误率必须重新标注，不能复用旧模型的标注。

Checkpoint validation93、官方 validation540、composition reserve181 和 BFCL 继续封存。本阶段不依赖它们选参数。严格 Tool-Combination Generalization 仍未资格通过；官方 reference 只含最终动作，不足以证明包含 lookup 的完整工具组合是未见的。共享初始数据库还可能带来 ID 记忆，因此即使 dev success 上升，也必须看 observation-grounding，不能直接宣称泛化或规划能力已解决。

## 文件与实际入口

- 审核、数据和选择：`experiments/SFT-READY-20260917-001/`。`quality_approvals.json` 包含完整通过/暂缓状态；两个 `.jsonl.gz` 是冻结的训练样本。
- 固定配置：`configs/sft_comparison_plan.json`，含八个实验字段、输入哈希、权重/模板哈希及计算上限。
- 准入：`veriagent/sft_stage.py`；旧 provider 默认准入不变，新 DeepSeek 路径需要明确的整条审核批准。
- 训练：`scripts/run_sft_comparison.py`；评估：`scripts/evaluate_sft_comparison.py`；比较：`scripts/compare_sft_evaluations.py`。
- 部署：`scripts/github_file_sync.py --include-sft-stage`，精确增加 14 个文件，预期共 54 个受控执行文件（包括实际主机 CPU 预检入口）。所有新增文件小于 2 MB。现有 904 数据盘已有原始教师 run；运行时必须匹配其哈希。

以下默认仅执行 CPU 检查，不加载模型：

```bash
.venv/bin/python scripts/run_sft_comparison.py --arm S1
.venv/bin/python scripts/run_sft_comparison.py --arm S2
.venv/bin/python scripts/evaluate_sft_comparison.py --condition BASE_B1
```

**未来得到开训指示后**，才在既有单 GPU 实例部署同一个已发布 commit，并显式增加 `--execute`。该参数是执行开关，不是用户授权的替代品。例：

```bash
.venv/bin/python scripts/run_sft_comparison.py --arm S1 --execute --run-id SFT-S1-20260917-001
# 完成并保全后，另一组仍从fresh base开始：
.venv/bin/python scripts/run_sft_comparison.py --arm S2 --execute --run-id SFT-S2-20260917-001
.venv/bin/python scripts/evaluate_sft_comparison.py --condition BASE_B1 --execute --run-id SFT-EVAL-BASE-20260917-001
.venv/bin/python scripts/evaluate_sft_comparison.py --condition S1 --training-run SFT-S1-20260917-001 --execute --run-id SFT-EVAL-S1-20260917-001
.venv/bin/python scripts/evaluate_sft_comparison.py --condition S2 --training-run SFT-S2-20260917-001 --execute --run-id SFT-EVAL-S2-20260917-001
```

Run ID 若已使用，程序拒绝覆盖。实际单价已知时加 `--hourly-rmb`；未知费用记 null。正式运行前会重查 5 个权重分片和 4 个模型/tokenizer文件、固定软件版本和单卡显存；现有 904 PRO6000 已跑过旧 probe，新的最长样本显存和 step time 仍须在开训时实测。

本轮实际费用：新增模型 API=0、GPU-hours=0、参数更新=0。未来两组训练加三组 dev 推理暂按 0.75–1.5 GPU-hours 规划，属于工程估计，包含加载/检查余量，非已测承诺；单个训练进程 60 分钟上限、单个 eval 30 分钟上限。发生 OOM、CE/gradient/reload/数据错误即停，不自动改卡数、context、监督目标或重采样。

**当前停止点：首轮 SFT 可执行准备完成，服务器未启动，训练和新 Agent evaluation 都未运行。**


补充：最后将通过既有904无卡模式部署并执行真实安装包/权重/tokenizer检查，再关机。此操作仍不构造8B模型或初始化GPU；实际结果以随后SFT-REMOTE-PREP-20260917-001回执为准。
