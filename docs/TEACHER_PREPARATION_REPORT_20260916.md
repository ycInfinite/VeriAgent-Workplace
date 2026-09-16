# 完整教师轨迹准备：已完成 CPU 审计，尚未调用 API

核验日期：2026-09-16。用户选定百炼 `qwen3.8-max`，目前提供的访问方式是 Token Plan。学生仍是固定 revision 的 Qwen3-8B。此次工作旨在补齐完整高质量示范，尚未进入参数训练。

## 实际证据

实验 `TEACHER-PREP-20260916-001`，代码 commit `b1f67b34b5fc18dd8e607ade68524332d58c4193`。

| 检查 | 原始结果 | 可以说明什么 |
|---|---:|---|
| 固定 training20 的初始 messages/tools 哈希 | 20/20 匹配 | 保留原 B1 与任务，不给教师参考答案 |
| 既有未批准轨迹的可见 assistant 轮次编码 | 69/69，丢弃0轮 | 已有样本可按学生模板完整编码 |
| processed / supervised tokens | 309957 / 3310 | 上下文保留但不作为监督目标 |
| 最大单轮序列 | 5316 | 这批格式样本可容纳于8192；不保证新教师轨迹也可以 |
| canonical targets 与原采样 IDs 不同 | 1轮 | 重新序列化不等于恢复实际采样token |
| 负向检查 | 5/5 | 拒绝oracle字段、改prompt、dev、非assistant目标、模板边界注入 |
| 教师调用 / 新rollout / 新批准 / 参数更新 | 0 / 0 / 0 / 0 | 未取得教师质量或训练效果证据 |
| CPU时间 / GPU-h / 本次付费实验费用 | 2.0213秒 / 0 / 0元 | 只做本地准备 |

全部结果在 `experiments/TEACHER-PREP-20260916-001/`，登记在 `experiments/registry.jsonl`。没有 infrastructure-invalid run。旧20条仍是未经批准的数据，不能因格式检查通过就进入训练；原3条 reward=1 和质量拒绝都保留。

新增实现为 `veriagent/teacher_data.py`、`scripts/prepare_teacher_data.py` 和 `configs/teacher_preparation_audit.json`。现有GPU采集器/SFT准入没有被改成接收未知教师数据；API采集器与教师数据准入尚未完成端到端实现。

## 官方来源与渠道结论

网页是可变官方文档，没有可固定的公开commit；下表记录URL和核验日期，不把它们当API实测。

| 项目 | 判定 | 官方来源 |
|---|---|---|
| qwen3.8-max支持Function Calling与关闭thinking | Verified Fact：官方示例使用该模型、tools与enable_thinking=False | [Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling) |
| Token Plan个人版用于自定义批量脚本 | 不适用：官方排除该用途 | [个人版FAQ](https://help.aliyun.com/zh/model-studio/token-plan-personal-faq) |
| 团队版可否替代个人版来跑本采集器 | 同样不适用；个人/团队/Coding Plan均排除自定义自动化脚本 | [更多工具](https://help.aliyun.com/zh/model-studio/more-tools) |
| 普通按量API路线 | 官方提供独立接入；需与套餐Key/端点区分 | [更多工具](https://help.aliyun.com/zh/model-studio/more-tools) |
| 北京普通模型单价 | 输入12元/百万tokens，输出36元/百万tokens；不按Prime价估算 | [模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) |
| 版本固定 | 官方列出qwen3.8-max-0902；当前用户指定alias。真正请求名、返回model与可用快照待接入记录，API不能提供等同开放权重的commit证明 | [模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) |
| 用户账户权限、适用Key、端点、实际usage与可用快照 | Requires Test；没有读取凭据、未发请求 | 无API实测 |

下一步需落实普通按量API，而非把Token Plan Key放入批量脚本或隐式改成余额扣费。Key只在远端进程环境中输入，不进入聊天、文件或日志。API生成阶段只需CPU执行环境和网络，不需要开启PRO6000 GPU。

## 待执行的有界采集方案（未登记为已执行）

- **Research Question**：同一固定20题/B1下，所选教师能否产出至少两条完整、可模仿的真实成功轨迹，供首次LoRA完整性probe？
- **Hypothesis**：更强教师可减少错误ID、非法参数和无依据范围收窄，但仍需逐条验证，不能预设成功。
- **Independent Variable**：轨迹生成策略改为百炼qwen3.8-max。跨模型tokenizer/API工具序列化的差异显式记录；这不是严格单变量的模型能力对比。
- **Controlled Variables**：固定training20、原B1/messages/tools、世界初始状态/时钟、官方工具/reward、学生模型revision；不接触dev/final，不给oracle，不换题。
- **Metrics**：官方success、可执行工具率、完整轨迹质量批准数、错误分类、APIusage、学生格式tokens、延迟、无效请求、费用。
- **Evidence Gate**：真实工具与状态；online/replay一致；完成assistant终止；全轨迹无不可监督决策；至少2个独立任务获显式批准；学生8192内、不删轮不截关键上下文。过门槛才进入原8更新probe的准备核验。
- **Cost Bound**：20题各1条，并发1，每题最多6轮，每次输出最多768、累计最多2048供应商completion tokens；无自动重试/额外采样，计划最大120次请求及1800秒采集进程。学生8192预算另查，不假装已知教师tokenizer。按100万输入/40960输出规划约13.47元，不是硬费用上限；接入后以真实usage核算。
- **Failure Branch**：渠道不适用先解决接入；API/超时等独立记无效并计费用；没有足够完整示范则停在审核，不自动改mask、扩大模型/上下文或启动SFT。

需要后续实现：普通API请求与错误记录；真实tool-result轮回；供应商usage与学生tokens分别记录；完整教师provenance准入。不能直接把新文本伪装成旧Qwen3-8B实际采样IDs。

## 粗颗粒学习

教师负责产生更好的行为示范，学生负责学习这些示范。它们可以使用不同tokenizer：把教师完整的可见动作和回答转成学生格式，再计算学生的CE；用户/工具观察仍是上下文，labels=-100。此处只保证格式与来源隔离，尚未证明示范质量、梯度更新或Agent效果。闭源教师质量和SFT收益都仍是假设。

下一步分叉只有访问渠道：落实普通按量API，或暂缓教师采集。无需为这一步租更大的GPU。
