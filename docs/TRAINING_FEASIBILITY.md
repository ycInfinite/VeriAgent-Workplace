# 单卡训练可行性：事实、估算与缺失证据

当前从未加载模型权重，所有显存/速度/参数更新判断都是计划或估算。CPU 检查不能代替真实训练 gate。

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

## Optional online RL 的下一层 gate

只允许先做 10–20 tasks×2–4 rollouts×1–3 updates 的获批 probe。必须有 policy v0 身份、在线 rollout、reward/advantage、update、policy v1 身份和新的 rollout 证据；记录 all-same-reward group ratio、无效轨迹、tokens、wall time、update time、VRAM、GPU-hours 和 RMB。

固定离线轨迹多跑几个 optimizer steps 不是 online RL。CPU toy CE/DPO 数字也不是训练结果。
