# Compute budget

实际新增 GPU-hours=0；付费模型 API=0；GPU/API 支出 RMB 0。本地 CPU/电费没有计量，不能宣称一切资源成本为零。

官方源文件 33.14MB、tokenizer/config 11.43MB；无模型权重、无 BFCL cases。CPU 依赖留在项目 .venv，复用系统 pandas/numpy 等只读包；没有更改全局已安装包。

规划价格 p=RMB 10/GPU-hour 只是占位，不是平台报价。租用前重新核价。单次预计超过 RMB 30 必须明确批准；无自动续费/多卡/扩大模型/context/seed。

| 档位 | S1/S2 各自 processed tokens | DPO pairs | 数据采集 output tokens | GPU-h 预算额度 | p=10 加余量 |
|---|---:|---:|---:|---:|---:|
| 低预算 | 2M | 150 | 0.5–1M | 45 | 约 550 元 |
| 正常 | 5M | 300 | 1–2M | 90 | 约 1100 元 |
| 扩展 | 8M | 500 | 2–3M | 140 | 约 1700 元 |

这些是额度，不是测出的耗时。额度包括 rollout、训练和评测，最终根据 probe 重算。扩展版最多预留约 10h 给获批 RL；p=15 时该档超过 2000，必须缩减/取消 RL。

SFT 的 processed token 与 supervised token 分开记；已测的单条学习 fixture 4536/89 不能当作整个训练集平均比例。DPO 按 chosen/rejected 两支分别计 token，reference forward 的时间也计入。rollout 的多轮累计输入会重复包含前缀，不能与一次 SFT 序列 token 混算。

Q0 模型阶段候选上限 RMB 80，预估 2–5 GPU-h 加启动余量，未授权。实际需逐 run 批准。

| 必测项 | 当前值 |
|---|---|
| peak VRAM / utilization | 未测 |
| policy generated tokens / trajectory length / rollout wall time | 未测 |
| SFT / DPO step time | 未测 |
| GRPO rollout / update time | 未测 |
| adapter load/save consistency | 未测 |
| cost per verified LLM success | undefined：无 LLM run |

正式 GPU probe 必须记录设备型号、驱动/CUDA/框架版本、prefill/output tokens、冷启动、并发、显存峰值、总 wall time、账单小时及 RMB。
