# Compute budget

更新：Day 3 已完成。按用户确认的 1.98 元/小时，受控会话从 SSH 创建到发出关机命令约 0.872 GPU-hours，估算 RMB 1.73；其中三次模型运行含加载共 0.158 GPU-hours，约 RMB 0.31（已包含在 1.73 中，不能相加）。未访问实际账单，未包括更早的开机时间、独立存储费用及本地电费。没有付费模型 API 调用。

CPU 阶段官方源文件 33.14MB、tokenizer/config 11.43MB；Day 3 在远端新增约 16.38GB 权重，本地仍未下载权重，BFCL cases 始终未下载。CPU 依赖留在本地项目 .venv；远端另建独立 .venv 并复用镜像 PyTorch，没有更改全局已安装包。

规划价格 p=RMB 10/GPU-hour 只是占位，不是平台报价。租用前重新核价。单次预计超过 RMB 30 必须明确批准；无自动续费/多卡/扩大模型/context/seed。

| 档位 | S1/S2 各自 processed tokens | DPO pairs | 数据采集 output tokens | GPU-h 预算额度 | p=10 加余量 |
|---|---:|---:|---:|---:|---:|
| 低预算 | 2M | 150 | 0.5–1M | 45 | 约 550 元 |
| 正常 | 5M | 300 | 1–2M | 90 | 约 1100 元 |
| 扩展 | 8M | 500 | 2–3M | 140 | 约 1700 元 |

这些是额度，不是测出的耗时。额度包括 rollout、训练和评测，最终根据 probe 重算。扩展版最多预留约 10h 给获批 RL；p=15 时该档超过 2000，必须缩减/取消 RL。

SFT 的 processed token 与 supervised token 分开记；已测的单条学习 fixture 4536/89 不能当作整个训练集平均比例。DPO 按 chosen/rejected 两支分别计 token，reference forward 的时间也计入。rollout 的多轮累计输入会重复包含前缀，不能与一次 SFT 序列 token 混算。

此前 Q0 的 RMB 80/2–5 GPU-h 是粗规划。用户后续授权既有实例上的 Day 3，实际远低于该估算；没有把 RMB 80 当作超 30 元实验的默认授权。已关机，下一阶段另行规划。

AutoDL 补充（2026-09-04）：实际 1×4090 24GB、并发 1 已完成测试，报价为用户确认的 1.98 元/小时。本次接入时已是 GPU 模式，准备/下载时间计入上述 1.73 元估算。无卡模式官方说明为 0.1 元/小时（0.5 核/2GB RAM），可作为后续准备优化，不能把这次准备时间虚记成无卡费用。此前 2–5 GPU-h 是粗估，不替代实测。

| 必测项 | 当前值 |
|---|---|
| peak VRAM / utilization | 本轮 allocated 最大 17.17 GiB；nvidia-smi sampled used 最大 19.80 GiB；B0/B1 sample mean utilization 60.7%/63.3% |
| policy generated tokens / trajectory length / rollout wall time | 75 条共 11,186 output tokens；B0 324.66 秒、B1 214.07 秒（各含加载）；详见 DAY3_REPORT |
| SFT / DPO step time | 未测 |
| GRPO rollout / update time | 未测 |
| adapter load/save consistency | 未测 |
| cost per verified LLM success | B0 约 0.0162 元，B1 约 0.0147 元，仅含各 run wall time；不包含准备费用，以官方 state reward=1 为分母 |

正式 GPU probe 必须记录设备型号、驱动/CUDA/框架版本、prefill/output tokens、冷启动、并发、显存峰值、总 wall time、账单小时及 RMB。
