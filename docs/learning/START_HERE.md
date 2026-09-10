# 从这里开始：先理解证据，再学训练

**当前入口（2026-09-10）：[第五课：第一次 LoRA SFT](05-first-lora-sft.md)。** 用户说明 Day 3 前内容基本掌握，直接进入 SFT 模块。新课内嵌 LoRA、PEFT、batch、forward/backward/step、参数变化与重载代码，适合手机交给 GPT 学习。旧材料按需要查阅，不要求先补完旧考核再学 SFT。

**2026-09-08 复习入口：[三天后重新接上项目：学习合订本](2026-09-08-return-to-project.md)。** 这份文件整合下面四课、Day 3 证据、代码导读和考核；可以独立阅读。按文内四段计划恢复基础、阅读源码、连接训练机制，再提交 A1–A5；收到回答后才评分。

**手机代码详解版已补齐：** 合订本第 11 章直接贴出 21 段项目/官方源码，逐段说明变量、输入输出和状态变化，并嵌入 task 0、task 18 与真实 token 表。晚上只把这一份文件交给 GPT 即可；第 11.15 节提供逐段教学请求，第 12 节考核无需打开仓库或运行命令。代码可分两晚阅读。

当前已完成 75 条真实模型轨迹，尚未做参数更新。下文为保留的 9 月 4 日学习安排，其中 CPU 阶段的“今天”不是当前状态。

你现在不需要先学 Ray、分布式训练或 GRPO 的全部推导。先能解释一条任务如何改变状态、reward 检查了什么、训练究竟监督哪些 token。建议分两晚完成，共约 90–120 分钟；这个时间只是学习安排，不是要求。

**更新：Day 3 真实模型运行已完成。** 先看 [第四课：真实轨迹与训练问题](04-day3-real-trajectories.md) 和 [Day 3 报告](../DAY3_REPORT.md)。下文“今天没有模型”的表述记录的是此前 CPU 阶段，不代表最新状态；本次已有 75 条真实模型轨迹，但仍没有参数更新。

## 先记住今天的边界

今天运行了 Python 工具和 verifier，以及真实 Qwen tokenizer。没有运行 Qwen 模型，没有 LoRA，没有训练成绩。看到 reward=1 时，必须先问“谁产生了轨迹、这个 reward 验证了什么”。

今天的一个真实学习案例：找 Carlos 的指定邮件 → 从工具返回中拿到 email_id → 回复 → 数据库变化 → verifier=1。动作由我们写的脚本产生，工具返回来自真实执行。它能教你理解管线，但不能证明模型已经会做。

## 学习顺序

1. [第一课：Task、Tool、State、Reward](01-state-tools-reward.md)，约 25 分钟。目标：能不看术语解释 stateful。
2. [第二课：Trajectory、Token、Loss Mask、DPO](02-trajectories-and-loss.md)，约 30 分钟。目标：能指出哪些内容是模型决策，哪些只是上下文。
3. [第三课：数据切分与实验结论](03-data-and-evidence.md)，约 25 分钟。目标：能判断一项结果是否支持研究假设。
4. [考核](ASSESSMENT.md)，约 30 分钟。允许查项目文件，但用自己的话回答。提交后由 Codex 按证据评分、追问与补课；当前未考核。

在项目根目录运行以下只读命令，不会启动实验、租 GPU 或联网：

```powershell
.venv\Scripts\python.exe scripts/learning_lab.py --view trace
.venv\Scripts\python.exe scripts/learning_lab.py --view mask
.venv\Scripts\python.exe scripts/learning_lab.py --view rewards
```

如果命令暂时不熟，可以先直接读三节课。终端只是查看相同证据的一种方式，不是学习目标本身。

## 五处最应该读的代码

| 文件 → 函数 | 输入 → 输出 | 在管线中的作用 |
|---|---|---|
| `veriagent/environment.py` → `WorkplaceEnv.step` | name/arguments → observation/error/state diff | 把一个动作变成真实执行证据 |
| `vendor/Gym/resources_servers/workplace_assistant/workplace_assistant_tools/email.py` → `search_emails`、`reply_email` | 查询/ID/正文 → 邮件信息/更新状态 | 一个只读工具与一个写工具 |
| `vendor/Gym/resources_servers/workplace_assistant/utils.py` → `is_correct` | predicted/ground_truth actions → bool | 决定官方 reward 的语义 |
| `veriagent/token_mask.py` → `TokenMaskInspector.inspect` | messages/tools → input_ids/labels | 区分 context 与 policy target |
| `scripts/audit_dataset.py` → `run` | 固定数据与 seed → 统计/候选清单 | 约束哪些任务能进入哪个阶段 |

不用一次读懂所有 import、类型标注和配置。每次先回答四个问题：输入是什么？修改了什么？输出是什么？下一步谁消费它？

## 完成学习后的提交方式

先提交考核 A1–A5 的回答。随后进行 B 部分证据追踪和 C 部分实验设计。不会仅凭选择题得分判定你掌握了项目，也不会在考核后自动租 GPU。
