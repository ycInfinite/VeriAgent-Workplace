# 已购 Token Plan 的项目使用方案

实施更新：固定Qwen Code0.23.4和隔离MCP1.30.0已在本地安装，scripts/serve_workplace_interactive.py 已实现三项交互工具；CPU003通过18项，001/002失败原始记录保留。当前904无卡部署进行中。以下“未实现/未安装”表格保留为较早准备快照，不代表最新进度；仍未发起模型任务或批准新SFT数据。

核验日期：2026-09-16。性质：官方来源核验和客户端配置准备，不是模型实验或新 rollout。

## 先修正前面的表述

当前自动采集脚本不能直接使用个人版 Token Plan，不等于套餐不能用于这个项目。官方个人版说明明确允许编程/智能体工具中的交互式使用及工具扩展。我们应当把已购额度用于实际交互开发、代码理解、已有训练数据审核和单任务调试。不能让另一个脚本通过 headless 客户端循环采集，再把它称作交互。

## 官方事实与尚未完成的验证

| 项目 | 状态 | 来源 |
|---|---|---|
| 个人版支持 Qwen Code 等编程/智能体工具，允许工具内交互式使用扩展 | 官方事实 | https://help.aliyun.com/zh/model-studio/token-plan-personal-overview 的订阅前须知 |
| 个人版排除自动化脚本、应用后端、非交互批量调用 | 官方事实 | 同上；https://help.aliyun.com/zh/model-studio/token-plan-personal-faq |
| 个人版目前不支持退订 | 官方事实；不能套用团队版未消耗席位规则 | 个人版概述的订阅管理 |
| qwen3.8-max 在个人版模型列表内 | 官方事实；实际账户额度/认证仍未测试 | 个人版概述的支持模型 |
| Qwen Code 可使用自定义模型提供方、环境变量 Key 和 MCP 工具 | 官方接口能力 | https://help.aliyun.com/zh/model-studio/qwen-code 及 https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/ |
| 用户账户订阅档位、剩余额度、自动续费状态、特殊退款资格 | 未核验 | 需控制台/客服，不由 Key 前缀猜测 |
| 本项目的 Qwen Code 接入、Workplace MCP 集成、新轨迹导出和训练准入 | 未执行/未实现相应适配 | 不把配置文件可解析当端到端成功 |

Qwen Code 是通用客户端；其文档介绍的技术能力不能自动扩大具体套餐的使用许可。只使用个人版明确支持的交互方式。若客服另有书面许可，保留适用账户、用途、限额和有效期后再评估。

## 已准备的配置

`configs/qwen_code_token_plan.example.json` 只包含北京套餐端点、qwen3.8-max、non-thinking 请求设置和环境变量名称。没有 Key、普通按量后备或自动运行参数。这是示例，不会自动覆盖用户的客户端设置。

参考官方安装说明安装 Qwen Code 后，先记录 `qwen --version`。在远端个人 CPU 工作环境中合并示例的 `modelProviders`、`security.auth`、`model` 到客户端设置，保留已有设置；确认其他配置层没有覆盖模型和端点。当前机器是否安装、客户端版本及设置合并均未验证。本轮未安装软件或开启 AutoDL。

凭据继续遵守项目约定：只进入远端进程环境。不要使用把 Key 写入 settings.json、.env、shell 启动文件或命令行参数的示例。Linux Bash 的人工终端可使用：

```bash
read -r -s -p 'Token Plan key: ' BAILIAN_TOKEN_PLAN_API_KEY
printf '\n'
export BAILIAN_TOKEN_PLAN_API_KEY
qwen
unset BAILIAN_TOKEN_PLAN_API_KEY
```

这里 `qwen` 启动真实交互界面，由用户亲自输入任务；没有 `-p`、管道提示词、任务循环或后台作业。不要把 Key 粘进模型聊天。终端和客户端不能开启凭据调试输出。已在聊天公开的 Key 建议先重置；本轮未使用它。

## 马上能用在项目上的交互任务

在 Qwen Code 中由用户发送以下提示。它只做代码/已有证据学习，不产生新实验结果：

```text
这是我的公开个人 VeriAgent-Workplace 项目。先阅读 AGENTS.md、
docs/PROJECT_CONTRACT.md 和 docs/PROJECT_STATE.md。
本次只解释已有 SFT 实现与证据，不启动 API 采集器、GPU、训练或子代理。
只读 veriagent/token_mask.py、veriagent/sft_data.py、
veriagent/teacher_data.py、scripts/run_sft_probe.py 和
docs/SFT_FIRST_PROBE_REPORT_20260916.md。
不要读取环境变量、凭据文件、公司资料、dev/final 任务或 BFCL case。
逐段解释 assistant-only labels 如何形成，CE 如何计算，
LoRA 参数如何更新，adapter reload 如何检查。
区分代码行为、已有实测和未被证据支持的推测。
最后给我三个关于这些真实代码的追问，等我回答后再评价。
```

同样可以在交互会话里审查已批准的 training 轨迹是否有遗漏前置查询、无依据 ID 或错误完成声明。这个审核是 AI 复核，不能标成独立人工审核，也不能修改历史原始记录。

## 与用户想要的 rollout 怎样衔接

候选路线：用户在客户端发起一个开发/调试任务 → 客户端模型选择 Workplace 工具 → 官方环境真实执行并返回 observation → 后续决策 → 单次结束后 verifier 检查与记录。

Qwen Code 的 MCP 扩展能力与项目现有 `WorkplaceEnv.reset/step/verify` 可用于实现这条路线，但本轮没有实现桥接器，也没有运行或导出新轨迹。不能把上述代码讲解当 rollout，不能把“客户端已支持 MCP”当“本项目已接通”。

开始前仍需一个单任务协议：限定 training pool、初始状态、实际客户端版本/提示词/可见工具和终止边界；保存完整会话与真实工具事件。客户端可能附加 system prompt、压缩上下文或调用非 Workplace 工具，因此不能宣称与旧 B1 相同条件。不可控的模型 revision、seed、tokens 记为不可用，不能编造。

如果有人工修正或读过 reference，记录为辅助示范；不能当独立盲测能力。新来源先保持 training_eligible=false，完成完整轨迹、grounding、学生 8192 编码与来源审核后，才考虑新的准入适配。原 API/本地模型导出门槛不放宽。正式大批量采集仍需服务允许的渠道。

## 可提交给客服的具体问题（未发送）

```text
我购买了 Token Plan 个人版，用于个人开源 Agent 后训练学习项目。
请确认两种场景各自是否允许：
1. 本人在 Qwen Code 的交互会话中发起单个开发调试任务，
   模型经自定义 MCP 操作公开的本地模拟工作环境，保存实际工具日志；
   人工审核后拟把完整示范用于个人开放权重模型的 LoRA SFT。
2. 自定义 Python 脚本连续运行多个任务，自动调用模型并收集训练数据。
如果第 2 种不在个人版范围内，是否有适用该用途的套餐或书面授权？
如果本次购买与实际用途不匹配，可否人工审核退订、退款或权益转换？
请按我的具体订阅和订单说明，不要只确认 API 技术上能够请求成功。
```

普通规则写明个人版不支持退订，因此特殊处理不能保证。订单号仅在官方客服界面补充，不附 API Key。本轮没有替用户提交工单、取消自动续费或更改订单。

## 本轮结果

完成来源核验、无凭据配置样例及交互任务说明；配置仅通过静态检查。新增 API 请求、rollout、参数更新和 GPU 使用均为 0。没有承诺套餐已可批量生成 SFT 数据，也没有启动按量 API。已有 15 条审核通过的完整教师轨迹保留，可供后续登记训练使用；本轮未启动新训练。
