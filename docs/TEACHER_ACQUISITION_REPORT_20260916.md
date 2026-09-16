# 真实教师采集与首次 SFT 输入资格

## 结论

`TEACHER-ACQUIRE-20260916-001` 完成固定20题：18/20官方成功，15/20通过完整轨迹质量审核。教师是百炼普通按量API `qwen3.8-max`，学生保持固定Qwen3-8B。获得合格示范，尚不构成学生训练效果证据。

教师采集代码commit：`ccc890d2191328c94132ac8affb163c2e17eb27b`。任务/工具/Gym/数据revision未变，B1未改；每题1条、seed42、non-thinking、最多6轮/768每次输出/2048每轨迹输出、学生8K约束；调用真实CPU工具/状态/verifier。闭源API的seed与返回model标签不能证明固定权重或完全可复现。

## 原始结果

| 指标 | 结果及口径 |
|---|---|
| 尝试 / 有效 / infrastructure-invalid轨迹 | 20 / 20 / 0 |
| 官方成功 | 18/20；包括一条轮数耗尽的状态成功 |
| 完整质量批准 | 15/20；由Codex审查，尚无独立人工裁决 |
| 实际工具调用 | 63/63通过已知工具+schema+无exception gate；不是语义正确性的充分证明 |
| API请求 / 自动重试 | 80 / 0 |
| 供应商输入 / 输出tokens | 387839 / 9023，包含整次采集所有已知usage |
| 学生格式目标tokens | 7247；包含未批准记录的格式统计，不是训练tokens |
| 采集进程wall time | 202.1212秒 |
| GPU计算 | 0小时；采集由无卡实例承载 |
| API费用估算 | 4.978896元，按核验时的公开原价；未扣缓存/免费额度，非实际账单 |
| 每次官方成功API费用 | 4.978896/18≈0.2766元 |
| 每条完整质量批准API费用 | 4.978896/15≈0.3319元 |

未知usage请求为0。部署/审核期间无卡实例费用另记在operational_events.json，不与GPU计算混淆；此前本地8B采集费用不是本轮API费用。基础设施失败会永久保留并排除能力分母；本次模型run没有此类失败，GitHub传输失败单列运维记录。

## 审核结果与代表案例

批准：565、450、972、247、859、123、770、271、20、707、177、76、965、687、8，共15条、57个完整assistant轮次。全部真实状态与重放一致；所有上下文仍保留，每条完整轨迹审核，不采用被拒绝的“仅正确片段”方案。

| 未批准任务 | 官方reward | 原因 |
|---|---:|---|
| 331 | 0 | 第5轮学生canonical序列超过8192，不截断，拟绘图动作未执行 |
| 1183 | 1 | 查完四页、正确删除两个未来会议，但6轮结束后没有assistant_final |
| 980 | 1 | 邮件只读第1/2页即断言全局最新；policy-visible schema未保证排序 |
| 518 | 1 | 同上，保持状态成功但暂缓完整示范资格 |
| 1175 | 0 | 第4轮达到单次768输出上限，未完整生成，不执行截断动作 |

707先查Kerry Moore得到ID00000046，再更新Proposal，完整3轮；此前8B同题先编造ID再恢复，本次未发生该错误。965先查员工邮箱、查全体匹配任务、移入Backlog、验证空余匹配、最终确认，共5轮。它们适合学习grounding→mutation→completion的完整链路。

Analytics获批仅按环境定义的plot状态与返回路径审核；环境没有真实渲染PNG，不能据此声称图像产物实际生成。输出中的长解释全部保留为assistant目标；non-thinking参数不代表回答一定简短。

## 训练输入资格

首次probe固定选择707和965两条完整轨迹，3+5=8轮，8次更新可以各用一轮。选择理由是覆盖两个此前较弱的业务域并让完整轨迹都参与这次完整性检查；这不是Random SFT或Failure-Targeted SFT正式比较。

CPU `TEACHER-ADMISSION-CPU-20260916-001`，代码`5fd411b`：15条已批准轨迹/57轮全部准入，0删轮；16/16负向检查通过。选定2题/8样本共35972 processed tokens、582 supervised tokens，最大序列4741。旧dev、脚本producer、错误reward、基础设施无效、删轮、改observation、改原始response、改request hash等均被拒绝。

远端`run_sft_probe.py --source-format canonical-teacher --validate-only`再次通过，未加载模型。教师token IDs没有被伪装成学生采样IDs；教师完整可见assistant行为按学生chat template重新编码，context/prefill/user/tool labels=-100。真实Transformers模板/IDs、CE、梯度、adapter更新与重载留给GPU probe。

## 执行范围与当前资源问题

SFT配置已在`configs/sft_probe_plan.json`登记：固定学生revision、rank16/alpha32、7类projection、lr5e-5、seed42、单卡、microbatch1、8步、1800秒进程上限。部署`d429eb6`的27文件哈希通过；原条件8步probe不等于授权S1/S2完整矩阵、DPO或RL。

本轮已按用户“继续，以后不用管即可”开启并结束新实例无卡模式。尝试切回PRO6000时AutoDL提示0空闲GPU，未启动GPU。A800启动入口曾被自动审批拦截；用户随后明确“允许已有 A800 执行 8 步 probe”，再次检查后A800也显示0空闲GPU。因此两台关机、更新0，外部库存是当前阻塞，已有A800的同一probe无需重复审批。没有租新实例或建立假SFT结果；未来GPU运行须另立不可变实验记录。

## 源码、证据与可学习内容

- `veriagent/teacher_rollout.py`：请求→原始response→真实tool/state→verifier。不会把API错误当作模型任务失败。
- `veriagent/teacher_data.py::export_teacher_turns`：审核哈希、任务来源、原始API输出、每轮输入连续性、真实observation与完整目标逐一核对。
- `scripts/run_sft_probe.py::prepare_examples`：将已批准的两条完整轨迹变成8个per-turn CE样本；`canonical-teacher`与旧exact sampled-ID路线明确分开。
- `scripts/audit_teacher_admission.py`：用改坏的样本证明准入门槛会拒绝，而非只测试正常路径。

原始文件：`experiments/TEACHER-ACQUIRE-20260916-001/{config,identity,result,quality_review_full_trajectory,probe_quality_approvals}.json`，`trajectories.jsonl`及`api_events.jsonl`。取回压缩包SHA256为`f3275f118a11ff62ea58c49cecfbdd1f4e3886bbf623551782fe355fee774506`，未覆盖原始记录。CPU准入与远端同步证据各有独立目录/receipt。

自动审批曾质疑工作场景字段的公开来源；已核验13份官方源文件哈希、220个输出邮箱均来自公开CSV、初始状态精确匹配，未发现密钥，随后同一GitHub推送获批。证据为`evidence/teacher-acquisition/public_data_provenance.json`；NVIDIA数据卡注明[Synthetic与CC BY4.0](https://huggingface.co/datasets/nvidia/Nemotron-RL-agent-workplace_assistant)。没有使用公司数据、BFCL或final cases。
