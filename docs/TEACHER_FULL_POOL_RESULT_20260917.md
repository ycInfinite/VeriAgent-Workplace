# 全 training 教师采集结果

**采集已完成，原始证据已完整备份，实例已关机。整条轨迹的语义质量审核尚未完成，没有开始新一轮 SFT。**

## 实际执行

实验 `DEEPSEEK-SFTDATA-20260917-001` 使用普通 DeepSeek Flash API，对固定 training pool 剩余 723 题各采集一次。早上的原 20 题保持原样，没有重复采样；项目 743 个 training 任务至此都有一次 DeepSeek 采集记录。Dev、checkpoint validation、final、官方 validation 和 BFCL 没有进入采集。

执行版本 `2ca291cde64b5c96baec2c9ebeb91e853665ae0a`。新任务按冻结的跨域交错顺序执行。保持 B1、non-thinking、最多六轮、学生上下文 8,192、单次输出上限 768、累计输出上限 2,048；没有重试、扩上下文、换题、训练或 GPU 使用。

实际开始：北京时间 **12:00:00**；实际结束：**12:50:28**；耗时 **3,028.69 秒**。不是仅创建了定时配置，而是已经完成真实模型请求、工具执行、状态变化和 verifier 检查。

## 原始结果与分母

| 指标 | 本次新增 723 题 |
|---|---:|
| 完成 trajectory | 723/723 |
| Infrastructure-invalid trajectory | 0/723 |
| 官方 reward=1 | 664/723，91.84% |
| 官方 reward=0 | 59/723 |
| Executable tool calls | 2,411/2,438，98.89% |
| API 请求 / 已保存响应 | 2,443 / 2,443 |
| Provider input tokens | 11,374,350 |
| Provider output tokens | 283,925 |
| Cache-hit input tokens | 10,601,856 |
| Cache-miss input tokens | 772,494 |
| Unknown-usage requests | 0 |
| 新增 SFT 质量批准 / 参数更新 | 0 / 0 |

这是 **teacher 在 training pool 的采集成功率**，不是学生模型提升、正式 held-out 成绩或 SFT 数据通过率。没有给 partial success 计分：表中成功采用官方 reward=1；完整质量审核仍会检查最终回答、grounding、范围和分页等。

83 题的 reference 为空，其中 80 题 reward=1；其余 640 个非空 reference 任务成功 584 题。空 reference 中保持数据库不变可能符合 state verifier，却不能证明查询答案正确或完整。必须分别审查，不能只因 reward=1 入库训练。

终止类型：702 条正常 assistant final，15 条学生上下文上限，3 条六轮上限，1 条生成不完整，2 条学生编码拒绝。模型正常调用过程中的这些边界失败保留为原始行为结果，没有被删除或自动改成基础设施失败。

## 费用

按已核验的官方午间价和返回 usage 估算，模型费 **2.12023112 元**。本次无卡实例包括准备、等待、采集和证据回收，约 **0.28 元**；合计约 **2.40 元**。CPU 起止采用操作记录估计，均非账单，未包含存储费。

模型费除以官方成功数约 0.00319 元/次。每条“质量合格 SFT 轨迹”的成本目前不可计算，因为整条语义审核还未完成。早上原 20 题资格测试费用另有记录，不混入本表。

## 证据与收尾

原始归档：`evidence/deepseek/DEEPSEEK-SFTDATA-20260917-001-evidence.tar.gz`，4,909,385 bytes；SHA256：`2b8062044fc1f555cf20feef03482f6bc42367378ff17f9adb30ca8c2e69f782`。

归档含 11 个原始文件、合计 81,993,639 bytes。归档和逐文件哈希已比对远端回执后安全提取到本地。完整 JSONL 留在本地和远端，GitHub 保存包含相同原始字节的压缩归档，避免再重复提交约 81 MB 的展开文件。逐文件哈希见 `evidence/deepseek/window_archive_receipt.json`。

原 worker 已退出。904 在证据备份后关机，另两台实例也处于关机状态。当天采集 heartbeat 已暂停，旧 GPU heartbeat 继续暂停；14:00 兜底关机在提前关机后已取消。没有遗留自动重采或训练任务。

Windows 本地完整性检查首次因新脚本漏写 UTF-8、默认 GBK 解码失败，已在操作记录中保留并修正。这是离线审核工具失败，没有产生新 API 请求，也不把已完成的模型轨迹改记为失败。

## 假设与下一步

支持的结论：该 provider 在本次固定范围和时间窗内完成全部 723 题采集，成本约两元级，产生了大量官方 verifier 成功轨迹。是否足够覆盖高质量整条 SFT 数据、是否改善学生 Agent、能否组合泛化仍未得到证明。

接下来先审查轨迹语义质量及学生编码，特别处理空 reference、分页、条件判断和提前结束。质量批准后再冻结正式 SFT 数据选择、训练 token 预算和评估协议。没有把本次采集授权延伸成 GPU 训练授权。

配置的八个预登记字段在 `configs/deepseek_window_acquisition.json`；原始结果在 `experiments/DEEPSEEK-SFTDATA-20260917-001/result.json`；生命周期与费用在同目录 `lifecycle_and_cost.json`。后续机械审核是派生证据，不能覆盖这些原始结果。


## 本地完整性审核已完成

723/723 的初始任务身份、工具 observation、逐步状态哈希、最终状态和 verifier 重放通过；2,443 对请求/响应及 non-thinking 配置与原始记录一致；费用重算一致。所有已记录的学生 prefix token 数复算一致。2,441 个 assistant 轮次可编码，其余两个完整目标编码被拒绝。

机械检查未标记的候选629条，标记94条。标记原因可重叠：59条reward不是1、21条非正常assistant final、26条包含不可执行调用、2条整条目标编码失败。未标记候选包含54条空reference轨迹，仍必须检查语义；候选累计学生processed tokens9,850,846、监督目标tokens195,473。不能把它们当成最终训练规模。

工具名称未知0/2,438；schema参数错误27/2,438；未在上下文观察到的ID候选0/1,181；同状态重复调用2/2,438。这些分别是词表/schema/启发式诊断，不能直接替代wrong tool selection、语义参数错误、ID hallucination或冗余行动的人工判定。Provider没有返回显式reasoning token用量字段；可见reasoning_content为空，但内部reasoning usage保持unavailable。

业务域官方成功数：Analytics122/132，Calendar152/169，CRM111/115，Email150/153，Project management129/154。统计仅用于描述采集和安排审核，不用于held-out checkpoint选择。

派生证据：`integrity_summary.json`、`mechanical_screen.json`。原始`result.json`及全部模型轨迹未改写。完整语义批准数仍为0。
