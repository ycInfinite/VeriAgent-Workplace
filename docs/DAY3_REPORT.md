# Day 3：真实 Qwen3-8B Agent 资格实验

2026-09-04。Day 3 已完成，未做参数更新。使用个人 AutoDL 单张 RTX 4090 24GB，完成 3 条 smoke、48 条 B0、24 条 B1，共 75 条真实模型轨迹。所有轨迹有效，在线状态与重放状态一致。结果已取回校验，已执行关机命令并观察到远端关闭 SSH。

结论：硬件和真实工具链资格通过；B0 单独未达到预登记 operating-regime 门槛。B1 单 seed 在需要动作的任务上达到最低成功/失败混合数量，成为有条件候选，但尚不足以宣布整个 Q0 或正式训练资格通过。

## 1. 实际执行和版本

- 模型：`Qwen/Qwen3-8B`，revision `b968826d9c46dd6066d109eabc6255188de91218`；这里 B0 指本项目未微调的基线，不是另一个 `Qwen3-8B-Base` checkpoint。
- 工具/verifier：NVIDIA Gym `83b3980b9c04379d72bbf59592d7846630f706bf` 的未改动核心。
- GPU 实际运行代码：`cb4067c3e0dd21723d5664e7ccd27cdd3120c51e`；完整上传文件哈希在各 identity.json 的 bundle_manifest 中。
- 环境：Python 3.12.3、PyTorch 2.8.0+cu128、Transformers 4.56.2、Accelerate 1.10.1、tokenizers 0.22.2、pandas 3.0.3、NumPy 2.3.2、jsonschema 4.25.0；驱动 580.105.08。
- 使用 Transformers/SDPA 直接单卡推理，复用现成 PyTorch；未安装 vLLM/Ray/训练框架。
- 24 个任务固定来自 SPLIT-003 的 dev 清单：20 个需要动作、4 个空 reference。B0 seed 42/43，B1 seed 42；non-thinking，8K context，6 个模型轮次，单轨迹最多 2048 output tokens，单次 generation 最多 768。
- 同轮生成的多条合法工具调用依次执行；六轮不等于六次 tool call。Native Transformers 没有执行 API 层的 parallel_tool_calls 开关，此行为已预登记在运行配置。

5 个权重分片在运行前通过独立 SHA256 校验；4 个 tokenizer/config 文件运行后通过固定哈希校验。24 个 B0 初始 prompt 与 CPU 模板的完整文本哈希一致。B1 逐任务核验只有已预登记 system 指令追加，用户请求与 tools 不变。

模型实际加载 8,190,735,360 个参数，trainable parameter count=0。三次运行的参数采样指纹相同，每次运行前后指纹不变；没有 optimizer 或反向传播。

## 2. 原始成功结果

| 指标 | B0 seed 42 | B0 seed 43 | B0 合计 | B1 seed 42 |
|---|---:|---:|---:|---:|
| 有效 rollout | 24/24 | 24/24 | 48/48 | 24/24 |
| 官方 Task Success | 5/24，20.8% | 6/24，25.0% | 11/48，22.9% | 8/24，33.3% |
| 需要动作的任务 | 2/20，10.0% | 3/20，15.0% | 5/40，12.5% | 5/20，25.0% |
| 空 reference 任务 | 3/4 | 3/4 | 6/8 | 3/4 |

主要对照是 B1 vs B0 seed 42：相同 24 题净增 3 个成功，增加 12.5 个百分点；改善 task 0、1、18，没有退化任务。三条改善都包含先犯错再恢复，并不是第一步错误被消除。

这是小规模、选定 development cohort 的结果，不能声称普遍或显著提升。探索性的配对精确检验 p=0.25；B0 的 task-cluster bootstrap 区间也很宽。未评测 BFCL、final 或组合 held-out。

## 3. 行为与成本：分母不能省略

以下主要按同一 seed 的 24 题比较。语义错误/冗余/提前结束来自 Codex 逐条复核，尚未独立人工复核；全部原始候选计数仍保留。标签可重叠，不可相加成总错误率。

| 指标 | B0 seed 42 | B1 seed 42 |
|---|---:|---:|
| 结构可执行调用 | 41/43，95.3% | 68/70，97.1% |
| Wrong Tool（本次严格功能口径） | 0/43 | 0/70 |
| Wrong Argument（语义复核） | 25/43，58.1% | 34/70，48.6% |
| Record-ID grounding error | 3/12，25.0% | 2/30，6.7% |
| 邮箱槽位 grounding error | 9/9 | 9/9 |
| 合并 identifier/email 错误 | 12/18，66.7% | 11/37，29.7% |
| 含 grounding 错误的轨迹 | 10/24 | 8/24 |
| Redundant Action | 2/43，4.7% | 7/70，10.0% |
| Retry Loop（连续三次相同调用/状态） | 0/24 | 0/24 |
| 确认的提前停止 | 11/24，45.8% | 6/24，25.0% |
| 平均工具调用数 | 1.79 | 2.92 |
| 累计 input tokens | 239,685 | 368,264 |
| 累计 output tokens | 3,193 | 4,184 |
| 平均轨迹耗时 | 6.27 秒 | 8.45 秒 |

口径：结构可执行要求 JSON/name/schema 合法且工具函数不抛异常，不保证业务操作成功。Wrong Tool 指未知或功能上不符合任务的工具；过早使用一个最终相关工具，归入缺前置查询等标签，不据此宣称规划正确。Wrong Argument 包括错误实体、字段值、时间范围和目标对象；宽查询不因与 reference 不同自动判错。Record-ID 还检查真实类型/当前状态，不能只看字符串是否出现。邮箱槽位包括把人名错误填进必须使用邮箱的参数。重复调用只计无新增事实的重试/重复读取；三次循环与两次重复分开。

“提前停止”经过复核，限定为可继续完成任务却在错误/失败查询后放弃，或无必要的能力否认；达到预算上限、已经执行错误修改后的结束另外报告。原始 failed-finalization 候选是 B0 33/48、B1 12/24，不能直接等同于最终提前停止标签。

合并 grounding 比例大幅下降时，绝对错误调用仅从 12 降到 11，分母从 18 增到 37；不能把分母增长写成彻底解决 grounding。两组均没有调用 company_directory 工具，所有本次邮箱槽位仍存在类型/来源问题。这不意味着必须使用唯一 lookup workflow，而是当前成功数据覆盖不了这一弱项。

## 4. 代表性成功/失败与真实原因

- **Task 0，B1 成功恢复**：先猜 `12345678` 作为 email_id → `Email not found` → 实际搜索 → 从 observation 取 `00000057` → 回复成功。改善的是恢复，首次 hallucination 仍在。
- **Task 1，B1 成功恢复**：先用准备改成的新名称搜索旧事件，空结果后改为按日期检索，取真实 ID，再改名。
- **Task 184**：`Quinn Taylor` 在用户文本出现过，但它是姓名，不能当 customer_id。字符串出现不等于 typed grounding。
- **Task 12，reward=1 的质量陷阱**：用虚构的 `leila@example.com` 查询，恰好得到与 no-op reference 一致的最终状态。两组都应单独标注，不自动作为高质量成功样本。
- **Task 1063**：IDs 都来自 observation，却删除了不属于 Sofia 的客户。Grounded ID 仍可能是错误目标。
- **Task 314/1219，B1 部分进展后失败**：先做了部分正确更新/删除，再操作其他人的任务或过去的会议；继续执行不等于正确完成。
- **Task 669/952，context limit**：B0 的下一次输入分别达到 8206、17890 tokens；B1 为 8268、17952。保存完整 observation 后停止，没有偷偷裁剪或扩大 8192。前者还存在错误 metric 参数，后者是过宽查询导致观察膨胀。

这些标签来自实际轨迹。B0 的 24 个 task 中，21 个在两次 seed 下得到完全相同的调用/观察序列，错误有较强可重复性。

## 5. 显存与费用

| 运行 | GPU wall time，含加载 | GPU-hours | 按 1.98 元/小时估算 | 每次官方 verified success |
|---|---:|---:|---:|---:|
| Smoke，3 条 | 29.23 秒 | 0.00812 | 0.016 元 | 不作稳定性能估计 |
| B0，48 条 | 324.66 秒 | 0.09018 | 0.179 元 | 0.0162 元 |
| B1，24 条 | 214.07 秒 | 0.05946 | 0.118 元 | 0.0147 元 |

纯运行合计约 9.47 分钟、0.158 GPU-hours、0.31 元。受控 SSH 会话从 04:33:21 UTC 到 05:25:40 UTC 发出关机命令，约 52.3 分钟，包含准备/下载/检查，费用估算约 **1.73 元**。未访问平台账单，不包含你更早的开机时间和独立存储费；关机请求到实际停机可能相差数秒。

B0/B1 Torch allocated 峰值分别为 17.16/17.17 GiB，nvidia-smi 采样 used 峰值为 18.96/19.80 GiB。整段运行的一秒采样 GPU utilization 均值约 60.7%/63.3%，包含加载和 CPU/工具间隙，不是连续利用率的精确积分。

24GB 已实测满足本轮配置，不能据此推断 SFT/DPO 也只需 24GB。费用优势主要来自任务规模小；后续仍需真实训练 cost probe。

## 6. 无效记录、元数据和训练完整性

没有 infrastructure-invalid 模型轨迹。准备阶段一次权重校验因文件列表缺少 LFS 字段失败；改用固定分片 HEAD 的独立哈希后全部通过，失败日志永久保留。未覆盖任何模型 run。

元数据说明见 `evidence/day3/metadata_notes.json`：运行 config 保留了一个陈旧的本地 weights-present 规划标记，不能据它否认实际权重加载；SMOKE 的 trajectory.condition=B0 表示提示条件，不等于纳入 B0 正式分母；Native Transformers 的多调用处理也已单列。原始文件不改写。

**新增训练前门槛**：真实同 prompt preference 演示中，chosen/rejected 的 generated tokens 为 275/161，而完整 conversation 的 role-mask targets 为 279/165。差出的四个 token 是模板插入的空 non-thinking prefill，在实际 generation 中属于输入。未来 SFT 必须声明格式目标；DPO 的 policy likelihood 必须核对逐轮保存的输入和输出，不能把 conversation 拼接后就当成精确 rollout-policy likelihood。尚未进行 trainer forward/CE、LoRA update、adapter save/reload。

## 7. Hypothesis 与路线分叉

- 硬件/执行链假设：支持。真实模型、真实工具、完整日志、哈希/状态一致性均有证据。
- B0 operating regime：未通过成功任务数量门槛。总体 22.9% 被 no-op 成功抬高，动作任务只有 12.5%。
- B1 通用提示改善：在当前配对 cohort 上支持净增 3 个成功；未证明显著或一般化收益。改善主要来自恢复，输入 tokens 增约 53.6%、输出约 31.0%，仍有冗余与目标约束问题。
- B1 作为下一步候选：有条件。动作任务 5 成功/15 失败，但只测一个 seed；CRM/Project Management 动作任务仍全失败。不得把低质量 no-op 成功直接加入训练。
- 严格 tool-combination held-out、BFCL 泛化、S1/S2、DPO、GRPO：均未完成/未测试。没有自动进入参数更新。

下次需要决定：是否冻结 B1 为后续共同 baseline；如何取得覆盖姓名→邮箱/目标约束/查询粒度的高质量 training-pool 数据；如何补足组合泛化设计。先完成学习与数据/训练完整性审阅，再批准小规模训练 probe。

## 8. 文件与证据入口

- 原始运行：`experiments/Q0-SMOKE-20260904-001/`、`Q0-B0-20260904-001/`、`Q0-B1-20260904-001/`，含 config/identity/trajectories/gpu_samples/result。
- 主配对表：`reports/day3-paired-initial/summary.json`、`task_outcomes.csv`。
- 当前语义复核：`reports/day3-reviewed-v2/metrics.json`、`annotations.json`、`domain_and_repeatability.json`。v1 保留，仅作为已被替代的分析版本。
- 权重、输入、费用证据：`evidence/day3/remote/model_integrity.json`、`model_aux_integrity.json`、`control_and_integrity_checks.json`、`lifecycle_and_cost.json`。
- 真实 preference 学习演示：`evidence/day3/real_preference_learning_pair.json`；来自 dev，training_eligible=false。
- 学习：`docs/learning/04-day3-real-trajectories.md`。

交付状态补充：新增报告、原始产物和学习材料已提交，交付 commit 为 5a5dec8aa8c4980a8ef218e78828918c27183167。此前两次提交尝试因自动权限审核超时而未创建进程，该临时阻碍已解除，历史记录保留在 evidence/day3/final_commit_status.json。实验运行所用代码仍为 cb4067c，不把交付提交当作新的实验。
