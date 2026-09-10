# 单卡训练可行性：事实、估算与缺失证据

2026-09-10 远端准备已完成：实际 Torch2.8.0+cu128/Transformers4.56.2/PEFT0.17.1/Accelerate1.10.1 导入成功，固定权重/辅助文件已校验；`run_sft_probe.py` 与8步配置已部署。当前无卡，没有模型加载、GPU forward/backward、训练显存或重载证据。详见 SFT_NO_CARD_HANDOFF.md；金额门槛已被用户覆盖，单卡与数据/完整性门槛保持。

2026-09-10 工程进展：逐轮真实输入/生成 IDs 的 CPU 编码审计已通过 200/200，固定 prefill 不作为 policy target；训练准入阻止 dev/错误来源/未审查数据。仅解决编码准备层，真实 Transformers trainer CE/LoRA update/reload 仍待 probe。下一轮先采集固定 20 条 training-pool rollout，详见 SFT_PREPARATION_REPORT.md。

2026-09-10：新增 [第一次 LoRA SFT 学习课](learning/05-first-lora-sft.md)，包含未执行的 PEFT、batch、update 和 save/reload 示例。它用于理解下列训练门槛，不表示 trainer 已实现、版本组合已验证或 cost probe 已获批。

更新：Day 3 已加载模型做纯推理，实测单张 4090 的 Torch allocated 峰值约 17.17 GiB、nvidia-smi 采样 used 峰值约 19.80 GiB。以下训练显存/速度仍是估算，尚无参数更新；不能由推理显存推出训练显存。

优先链路：官方 Workplace 工具/状态/verifier → 可审计轨迹 → Transformers/PEFT，按需要使用 TRL。rollout serving 可以独立，避免把 Gym/BFCL/训练的依赖装进同一个环境。暂不引入 NeMo RL/verl/分布式训练作为主线。

| 方法 | 1×A800 80GB 工程判断 | 必要条件 |
|---|---|---|
| BF16 LoRA SFT | 可行性高；估计约 25–50GB | 4K–8K、microbatch 1、梯度累积、checkpointing |
| QLoRA SFT | 显存更低；估计约 15–35GB | 先验证量化/硬件兼容，不因有 QLoRA 就默认更快 |
| LoRA DPO | 有条件可行；估计约 35–70GB | chosen/rejected 长度控制、冻结 reference、可预计算 reference log-prob |
| Online GRPO | 未资格化，不承诺显存/吞吐 | SFT/DPO 完成；reward 可靠；非全零；小组 reward 有差异；cost probe 获批 |

这些区间不是实测。8B BF16 权重本身约十几 GB，不等于训练总显存；activation、logits、adapter gradients、optimizer states、reference 与推理 KV cache 都会占用空间。

## 可以在不下载权重时计算的东西

固定 Qwen config：hidden_size=4096、intermediate_size=12288、36 layers、32 attention heads、8 KV heads、head_dim=128。若只对每层 q/k/v/o/gate/up/down 七个线性层加 rank-16 LoRA，理论新增参数为：

```text
每层 = r × [(4096+4096)+(4096+1024)+(4096+1024)+(4096+4096)
          +(4096+12288)+(4096+12288)+(12288+4096)]
总数 = 16 × 75,776 × 36 = 43,646,976
```

这是假设模型结构与模块选择相符时的解析期望值，不是实际 trainable_parameter_count。bias、embedding、lm_head、额外可训练模块或实现差异都会改变结果。正式 PEFT 加载后必须逐模块核对。

## 真实训练 gate，尚未执行

1. 实际 trainer 的 messages → template → input_ids 与 CPU 检查对齐；assistant targets、EOS、padding 和截断规则明确。
2. 用真正模型 logits 做 shifted CE，确认非目标 token 不贡献直接 loss；inspect 非零 LoRA gradient 与权重差异。
3. 核对 trainable parameter count，保存 adapter，重新加载后在固定输入上验证输出/logits 一致性（需记录 dtype/容差）。
4. S1/S2 对齐 processed/supervised token 预算、步数、adapter、seed 和 eval；保留不同选择策略的采集费用。
5. DPO reference 是指定的冻结 checkpoint；两支 observation 仅作 context；不以长度或基础设施失败决定 rejected。
6. 实测 SFT/DPO step time、VRAM/utilization、GPU-hours，更新预算后才批准正式训练。

7. Day 3 已发现 canonical role-mask 与实际生成输出相差四个强制 non-thinking prefill tokens。还需核对每轮真实输入与生成输出的 conditioning、消息重序列化以及强制前缀。详见 evidence/day3/serialization_alignment_note.json；仅通过 assistant-role mask 检查不代表真实 trainer 对齐已通过。

## Optional online RL 的下一层 gate

只允许先做 10–20 tasks×2–4 rollouts×1–3 updates 的获批 probe。必须有 policy v0 身份、在线 rollout、reward/advantage、update、policy v1 身份和新的 rollout 证据；记录 all-same-reward group ratio、无效轨迹、tokens、wall time、update time、VRAM、GPU-hours 和 RMB。

固定离线轨迹多跑几个 optimizer steps 不是 online RL。CPU toy CE/DPO 数字也不是训练结果。
