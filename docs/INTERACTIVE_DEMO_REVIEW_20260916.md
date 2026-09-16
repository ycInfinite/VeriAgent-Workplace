# 第一条 Token Plan 交互示范审核

## 结果

用户在官方Qwen Code界面发起的training707任务已真实完成：查询Kerry Moore → 使用查询返回的ID更新status → 查询复核。三次业务工具调用无错误，数据库只改变该客户的status，官方reward=1。CPU重新执行同一动作序列后，观察与最终状态哈希均一致。没有新参数更新。

这证明套餐的官方交互式路线能完成本项目的一个真实工具任务；不证明批量脚本适用，也不构成普遍成功率或模型提升结论。该题是已知可完成的接入示例，不是随机盲测。

## 为什么没有直接放进SFT

本次为用户发起后的事后审核，ID为`INTERACTIVE-DEMO-20260916-001`，不能伪装成预登记B1。真实客户端没有执行预期的8K/non-thinking配置：

| 证据 | 实测 |
|---|---|
| 客户端记录的context window | 1,000,000 |
| 六个主线回复的最大input tokens | 9,805；其中5次超过8,192 |
| 主线input/output tokens | 48,280 / 796 |
| thinking tokens | 255；不能再加到output上冒充额外总量 |
| 主线缓存tokens / API耗时 | 38,445 / 22.984秒 |
| 业务工具 / 含开始结束的MCP工具 | 3 / 5 |
| 客户端总用量记录 | 7次请求，58,620 input、798 output、24.467秒 |

主线逐响应记录只有6次。聚合记录多出的1次、10,340 input、2 output、1.483秒，与默认后续建议机制相符；没有额外响应ID，严格归因仍是推断。两种口径均保留，不挑较低数字当总费用。套餐Credits与实际账单未读取，不套普通按量单价。

完整wire request、动态系统上下文和独立模型revision不在当前日志中。客户端的get_task/finish_task协议也不同于已有SFT准入格式。因此`training_eligible=false`，不计入正式B1指标、不增加合格SFT数据条数。这是配置和记录门槛问题，不能标成模型任务失败。原reward=1和动作日志不改写。

## 已修复与验证边界

根因从固定Qwen Code0.23.4源码确认：`--bare`使用`createMinimalSettings()`，跳过配置文件。之前只检查JSON存在和MCP连通，没有验证最终解析值，这是接入检查遗漏。

- 启动器移除`--bare`并清除继承的`QWEN_CODE_SIMPLE`；仍保留明确工具拒绝列表、独立工作目录和配置目录。
- 新配置显式关闭hooks、自动记忆、follow-up建议和speculation，使用专用上下文文件名。
- 使用新`interactive-client-v2`目录保留旧会话、配置和证据。
- 对实际官方配置解析器做无网络测试：旧设置解析为1M/未指定thinking，新设置解析为8192/enable_thinking=false/单次output256/重试0。
- MCP返回改为等价紧凑JSON，没有截断或删除工具字段。旧任务返回文本的学生token数5306→3371，仅是返回文本的测量，不能当作新模型完整请求长度。
- `INTERACTIVE-MCP-CPU-20260916-004`的18项真实CPU工具/状态/验证控制通过。

尚未进行修复后的真实模型试跑，不能提前宣称所有请求均在8K内或数据已合格。后续首次交互仍需用户在官方客户端发起；先核验实际wire/context/usage，再考虑训练准入。不扩大context、不自动采样20题、不训练。

## 证据

- 原始归档：`evidence/interactive-client/INTERACTIVE-DEMO-20260916-001-evidence.tar.gz`，SHA256 `e40576625c1a0bc524716f09a32b808a5a4945465815ba93eb265403a2dc3888`。
- 22个归档成员逐一SHA核验；路径较长的成员通过可追溯映射保存到实验raw目录，未修改内容。
- `experiments/INTERACTIVE-DEMO-20260916-001/result.json`及`raw_manifest.json`。
- `evidence/interactive-client/effective_config_audit_20260916.json`。
- 原执行源码commit：`318e23376f5f8358e52fa3dead81227021597fb1`；模型请求名qwen3.8-max，独立权重revision未知。

下一步路线：停止追加教师采样，先决定是否继续资格测试此交互来源，或回到已有15条合格完整轨迹的下一轮SFT设计。二者均没有自动开始。
