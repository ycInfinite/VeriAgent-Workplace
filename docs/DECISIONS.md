# Decisions

| ID / 日期 | 决策与理由 | 状态 |
|---|---|---|
| D001 / 2026-09-04 | 固定 Gym/NVIDIA 数据集，不使用浮动 latest 或新 Nexusflow prepare 入口 | 已执行 |
| D002 | 直接调用官方工具/verifier，采用小型本地适配层采集状态；不安装完整 Ray/训练框架 | CPU 路径已验证；不声称原生 NeMo launcher 验证 |
| D003 | BFCL 只读取协议与版本文档，cases 未下载 | 保持 sealed |
| D004 | 相似候选和模板亲缘保守隔离，原始数据及原清单保留 | SPLIT-002 生效 |
| D005 | 按写操作任务与 no-op 任务分开评价；不再用总体 20% 门槛单独放行 | 写入模型资格计划 |
| D006 | CPU 原始 24-task 样本用于环境检查；未来模型 pilot 重新按最终清单固定 20+4 分层 | 无模型结果参与选题；保留前版 |
| D007 | 学习 fixture 永不进入 SFT/DPO 数据：它来自 dev 且由脚本生成 | 已写 eligibility=false |
| D008 | strict composition held-out 不成立为已验证事实；181 条只是预留 | 需用户路线决定 |
| D009 | 无 GPU、无模型权重、无训练；接下来先学习、考核 | 当前停点 |

待用户选择：A. 保留 Workplace 做 grounded lookup→state mutation 的数据选择研究，收窄泛化主张；B. 后续独立设计少量受控 composition 任务并审计其语义；C. 若严格组合泛化不可让步，比较其他环境。未自动选择 B/C 或开始生成任务。
