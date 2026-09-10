# SFT 准备实验：2026-09-10

当前阶段：**SFT 数据准备**。用户要求实验优先、粗颗粒教学。已经完成实际 CPU 编码审计与固定训练采集任务；尚未采集新模型轨迹或执行参数更新。

## 1. 实际执行与结果

实验 ID：`SFT-PREP-20260910-001`。运行代码 commit：`23fa06f`（完整值见 identity.json）。配置包含八个实验字段，原始输入哈希和逐轮结果保留。

| 检查 | 结果 |
|---|---:|
| 已有真实轨迹审计 | 75 条 |
| 实际模型生成轮次 | 200 次 |
| 重建输入 prompt 哈希匹配 | 200/200 |
| target IDs 与实际生成完全一致 | 200/200 |
| 固定 non-thinking prefill 留在输入、未计为 target | 200/200 |
| dev 轨迹拒绝进入训练 | 75/75 |
| 篡改输入、输出、来源等负向检查 | 7/7 拒绝 |
| 逐轮 processed / supervised tokens | 912,164 / 11,186 |
| 单轮最大 processed tokens | 8,176，未超过 8,192 |
| 本轮参数更新 / GPU-hours / 付费 GPU/API 费用 | 0 / 0 / RMB 0 |

假设在本次 CPU 检查范围内得到支持。没有 preparation-invalid run。结果不等于真实 trainer 的 forward、CE、LoRA 更新或重载已经通过。

编码现在直接保留每轮 rollout 的真实输入，并仅监督该轮真实生成 IDs。它明确采用“一轮模型生成一个训练样本”的目标；多轮会重复处理历史 context，后续 S1/S2 必须使用同一种编码并同时报告 processed/supervised tokens。没有静默改写旧 role-mask 审计结果，没有导出 dev 训练语料。

## 2. 下一轮固定训练采集任务

从 `SPLIT-003` 的 training_candidate 选择 **20 题，五个业务域各 4 题**。固定 seed=20260910 的 task_uid 哈希排序；参考动作数限定 1–4；没有按新模型成绩选题或换题。

初始 B1 prompt 为 4177–4204 tokens，覆盖率 20/20，全部能放入当前 8192 context。此覆盖仅是初始输入，不保证工具返回后不触发长度上限。

采集采用原 B1 通用提示作为 **probe 候选条件**，seed42，一题一次，最多 20 rollout；保持六轮、累计输出 2048、单次 768 等既有边界。没有宣称 B1 已成为充分验证的正式 baseline，也没有声称严格组合泛化已合格。

采集之后必须逐条审核：verifier 成功、有效执行、ID/邮箱依据、目标范围、监督各轮的合理性。初次 probe 要求至少两个不同 training 任务拥有明确批准的轨迹；成功不自动等于高质量，不足时报告分叉，不自动加 seed、改 prompt 或换任务。

## 3. 已准备代码与采集包

| 文件 | 作用 |
|---|---|
| `veriagent/sft_data.py` | 固定 tokenizer 哈希、逐轮编码、严格训练准入和导出接口 |
| `scripts/prepare_sft_probe.py` | 实际执行的 CPU 审计与固定选题 |
| `scripts/collect_training_probe.py` | 有价格和硬进程时限的真实训练轨迹采集入口，GPU 尚未执行 |
| `scripts/run_day3.py` | 复用真实工具主循环；新增显式 source_pool，默认保持 development |
| `scripts/build_sft_acquisition_bundle.py` | 白名单打包，排除 dev/final/BFCL/权重/凭据 |

采集入口/包代码 commit：`537b1876`（完整值见打包回执）。包：`dist/sft-acquisition-537b1876.tar.gz`，81,809 bytes。SHA256：`d6a58ad1ecc34d67bf22e4b4e48b209ba7b56bd5a30ca7aad06e998a3df8ac38`。31 个归档成员，其中 30 个载荷逐项核验哈希，另外一个是清单；20 个任务全部属于 training_candidate。采集输入验证另拒绝了错误 pool、修改任务和重复任务三种情况。

无卡模式可上传这个包并准备依赖。新主机仍需检查 Python/CUDA/PyTorch 与固定推理依赖组合。包是采集入口，不含已合格的 SFT trainer；后者在得到批准的 training 轨迹后接通并验证。

## 4. 资源与路线分叉

建议单张 A800 80GB；A100 80GB 可按实际报价选择。80GB 是为下一步 BF16 LoRA probe 留余量，不是已经实测的训练显存需求。用户尚未提供新实例型号、单价和可用入口。

下一轮采集进程上限 1800 秒，最大进程费用估算为 `0.5 × 实际元/小时`；入口拒绝预计超过 RMB 30 的自动执行。进程截止会退出并释放 GPU，但不会代替 AutoDL 实例关机，准备、空闲和存储仍需单独核算。没有使用历史 4090 的 1.98 元报价替代新实例报价。

当前待外部条件：用户提供准备好的实例及价格。随后按“主机核验 → 固定 20 题采集 → 质量审查 → 合格数据导出 → 小规模 LoRA 完整性/cost probe”推进。S1/S2 正式对照、DPO、RL 和最终泛化评测未启动。

## 5. 证据入口与粗颗粒教学

- [实验配置](../experiments/SFT-PREP-20260910-001/config.json)
- [原始逐轮检查](../experiments/SFT-PREP-20260910-001/turn_audit.jsonl)
- [结果](../experiments/SFT-PREP-20260910-001/result.json)
- [固定采集清单](../experiments/SFT-PREP-20260910-001/acquisition_manifest.json)
- [下一轮采集实验卡](../configs/sft_acquisition_plan.json)
- [打包验证](../evidence/sft-preparation/bundle_validation.json)

本阶段只需理解三点：dev 成功不能移到训练集；实际输入/输出边界要与训练目标一致；先拿到可信训练数据，再验证真正的参数更新。细节学习可用第五课，不作为工程推进门槛。
