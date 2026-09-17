# 全 training 教师采集：排队回执

状态：**已排队，尚未开始采集**。核验时间为北京时间 2026-09-17 10:30:55。

## 本次范围

项目内部 training pool 有 743 题。今天早上的资格测试已尝试其中 20 题；保留这些成功和失败，不重复采样。本次采集剩余 **723 题**，每题一次。

| 业务域 | 新任务数 |
|---|---:|
| Analytics | 132 |
| Calendar | 169 |
| CRM | 115 |
| Email | 153 |
| Project management | 154 |

固定顺序在各域内使用 seed=20260917 的哈希排序，再跨域交错执行。这里的 seed 是选题顺序，不是 DeepSeek 未承诺支持的推理 seed。没有根据新模型成绩换题。Dev、checkpoint validation、final/composition reserve、官方 validation 与 BFCL 不进入本次数据。

83 题的官方 reference 为空，全部保留并单独标记。这类任务可能属于查询或条件不触发；官方 state verifier 的 reward=1 不能独自证明自然语言答案完整、事实正确或适合 SFT。

## 已经完成的工程检查

- 723 个输入全部通过学生 tokenizer 初始检查，最长 4,215 tokens；没有截断任务或扩大 8,192 上限。
- 工具 schema 去重存储后逐题还原，和原始输入完全一致。
- 四个时间边界及四个范围变更拒绝检查通过；这些是 CPU 检查，不是模型成绩。
- 40 个执行文件通过 GitHub 固定提交部署和哈希校验。
- 远端预检通过；进程在原 SSH 断开后仍存活，未发现 GPU 设备。
- 核验时 API 请求数为 0，远端状态为 `ARMED_WAITING`。

## 执行边界

仅今天北京时间 **12:00–14:00**。普通 DeepSeek Flash API，non-thinking，原 B1，最多六轮、768 output tokens/call、2,048 output tokens/trajectory，学生上下文仍为 8,192。最多 723 条、4,338 次模型请求；顺序执行，无自动重试。

远端一次性进程持有临时 Key，等待到 12:00。Key 不写入文件、Git、日志或自动化配置。逐条保存完整请求、响应、实际工具执行、状态和 verifier。全部完成即结束；基础设施故障停止并留证；14:00 截止时不继续调用模型。AutoDL 平台也已设置今天 14:00 关机。

本地电脑关闭不影响已排队的远端进程。Codex 的自动检查和结果回收仍依赖本地应用可用；若未在关机前回收，结果留在远端数据盘，不声称已经备份。本次不运行 SFT，不自动批准训练数据，也不进入 DPO/RL。

## 费用与不确定性

按早上 20 题的实测速度推算，723 题约 53 分钟。这只是外推；本次覆盖更复杂任务，可能遇到速率限制或上下文问题。

按同等 token 用量和缓存比例，午间 API 费用约 2.10 元；同等 token 用量但完全没有缓存约 11.88 元。不是费用上限或账单。无卡模式 0.10 元/小时，包含等待和部署时间；到 14:00 的本次 CPU 开机窗口约 0.38 元。模型/API 最终费用、有效和无效轨迹、未完成清单均待采集后报告。

## 运行身份与交接

- 采集 ID：`DEEPSEEK-SFTDATA-20260917-001`
- 固定执行提交：`2ca291cde64b5c96baec2c9ebeb91e853665ae0a`
- 远端：既有 904 无卡实例；PID 1398，start ticks `1926709082`。复查时必须核对身份，不能只凭 PID 判断。
- 配置：`configs/deepseek_window_acquisition.json`
- 名单准备：`experiments/DEEPSEEK-POOL-PREP-20260917-001/`
- 排队/部署证据：`evidence/deepseek/window_schedule_receipt.json`、`window_github_sync.json`、`window_queue/`
- 保留的操作故障：`evidence/deepseek/window_operations.jsonl`
- 当天到期的监控：`veriagent-9-17`；旧 GPU 监控继续暂停。

等待或运行中不要再次部署执行文件，否则固定哈希检查会停止任务。不要重复 arm，不自动补采未完成任务，不放宽质量门槛。

本轮回答的是“如何按时采集全部可训练任务的教师证据”。是否能全部完成、多少能作为整条 SFT 数据、是否能提升学生 Agent，目前仍未得到本轮实验结果。
