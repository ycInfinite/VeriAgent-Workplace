# 项目约定

用户目标：真正掌握 trajectory → eval/failure analysis → post-training data → SFT/LoRA → DPO → 可选 online RL → generalization/cost 的完整机制。核心对照为相同训练预算的 random verified SFT 与 failure-targeted SFT。RL 不是项目成立条件。

## 当前授权

2026-09-16 API补充：用户指定百炼 qwen3.8-max，现有渠道为 Token Plan。已核验官方个人版/团队版规则均排除自定义自动化脚本；固定20题采集需要适用的普通按量API，不能暗中改扣费渠道。平台/模型已知，适用凭据和远端进程接入尚未落实。CPU准备已完成；没有付费API请求、新rollout或参数更新。下条“平台/模型待提供”仅描述较早状态。

2026-09-16 继续指示：用户随后要求“进行下一步”，并确认有个人公网API。恢复完整高质量轨迹的数据来源准备，保留整条监督门槛和固定20题/B1；不采用之前未获同意的正确片段方案。具体API平台和模型ID仍待用户提供，Key不得进入聊天/文件/Git。当前只做CPU请求隔离与学生格式审计，不据此开机、调用未确认API或更新参数。

2026-09-16 当前停点：固定20条采集后，整条轨迹质量门槛未通过。用户明确“保持原方案，先停在数据审核”，未采纳正确片段监督提案。停止在此，不自动追加采样、放宽审核、改变mask或执行更新；新旧实例均已关机，数据保留。此前条件probe授权不覆盖停止后的自动重启。

2026-09-16 迁移与开机：用户明确要求通过AutoDL“更多→跨实例拷贝”将旧A800项目迁至新PRO6000实例；拷贝完成后又明确回复“允许开启并继续”，授权开启新单卡并执行固定20条采集→质量审核→通过后8步LoRA probe。此为明确开机授权，不是自动租新实例或扩大实验；旧A800数据保留，旧机保持关机。新机开机确认框显示6.98元/小时。

2026-09-10 文件传输：在明确说明待发布代码、学习文档与公开环境实验准备记录的范围后，用户回复“记得用github传文件”。据此使用指定 ycInfinite/VeriAgent-Workplace 私有仓库推送并在远端拉取固定 commit 文件；不再对同一已说明范围重复确认。密码、模型权重和缓存不入 Git；训练主机只下载执行白名单，保持 dev/final 隔离。私有仓库匿名 clone 不可用时，用现有本地 Git 登录向 GitHub 取得临时只读文件链接，远端直接从 GitHub 下载并校验；不传账号凭据，不保存临时链接，不自动修改仓库可见性。

2026-09-10 最新预算覆盖：用户提供新的个人 AutoDL SSH 无卡实例并要求继续，随后明确“无需顾虑预算，继续使用”。当前 SFT 推进不再以 RMB30 或未知报价作为等待确认的门槛；保留单卡/固定模型/上下文/rollout/阶段范围，实际资源仍记录，未知单价与费用写 null/不可用而非 0。无卡模式下完成上传、依赖、固定权重下载和检查，不在无卡模式加载 8B 或擅自调用未核实的实例切换接口。下方较早金额条款在本轮被此授权覆盖。

2026-09-10 最新指示：用户要求直接推进实验进度，教学保持粗颗粒。开始 SFT 的数据、编码与训练入口准备，将首次小规模训练 probe 做到可执行、可审查；不再以旧学习题/考核阻挡工程。GPU 尚未准备，用户询问选型；建议单张 A800/A100 80GB，先无卡准备。执行前仍需实际实例、报价、合格 training 数据、完整性检查和登记配置；不自动租卡/开机，不自动扩大为正式 S1/S2、DPO 或 RL。单次预计超过 RMB 30 的确认线不变。

2026-09-04：完成租 GPU 前全部可做工作；结束后提供适合学习一个月的新手的学习材料，并考核。允许小型官方源码、任务数据、CPU 依赖和 tokenizer 准备；不租 GPU、不下载大模型、不使用付费模型 API、不做训练、不自动进入后续阶段。

后续授权：用户提供个人 AutoDL SSH 访问并明确要求完成 Day 3 全流程，允许在该实例准备环境、下载固定模型、执行 smoke、48 条 B0 与满足预登记条件时的 24 条 B1。继续保留单次预计超过 RMB 30 的审批线；不做 SFT/DPO/RL 参数更新，不扩大模型/卡数/context/seed。凭据不进入项目、Git、日志或聊天回显。

## 固定边界

- 单卡上限 1×A800 80GB；候选约 8B，LoRA/QLoRA，有限 context。
- 总预算约 RMB 1000–2000；单次预计超过 RMB 30 必须明确获批。
- 保留旧 tau2 项目为 Hard-environment Base Qualification Audit，不操作旧目录。
- 只使用公开个人项目资料。公司数据、源码、技能、Prompt、API、测试及内部结论禁止混入。
- API key 只允许远端进程环境，不写文件/Git/日志/聊天。
- BFCL final cases 不用于任何训练、prompt 调试、taxonomy、pair、RL 或 checkpoint selection。
- 所有模型行为结论必须来自真实模型 rollout。脚本回放只证明工具/verifier 性质。
- 在线 RL 必须证明当前权重 rollout → reward → update → 新权重 rollout；离线轨迹不冒充 online。

## 训练与评价

- SFT 的 system/user/tool/environment 内容默认 labels=-100；assistant tool calls/response 是监督目标。
- DPO pair 共享任务与初始条件，各自工具 observation 仅作为 context；检查 policy-token log-prob mask 和冻结 reference 身份。
- S1/S2 控制模型、token、step、adapter、eval 和 seed；分别报告 processed/context/supervised tokens 和采集成本。
- 不能把 reward=1 等同高质量/grounded，也不能把 loss 下降等同 task success。
- 保留成功、失败、无效 run 原始证据；无效 run 不计能力指标，但计费用。

## 长期产物

维护 PROJECT_STATE、ENVIRONMENT_AUDIT、EXPERIMENT_PROTOCOL、FAILURE_TAXONOMY、DECISIONS、HYPOTHESES、COMPUTE_BUDGET、experiments/registry.jsonl 和 docs/daily/YYYY-MM-DD-learning-handoff.md。

每日结束停止新实验，handoff 应包含核心问题、前后状态、执行、变量、结果、代表轨迹、结论/推测、3–5 个代码函数导读、学习点、5 个无答案面试题、路线分叉及证据身份。
