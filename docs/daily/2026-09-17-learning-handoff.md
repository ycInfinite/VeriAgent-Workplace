# 2026-09-17 学习交接：普通API教师选型

**最新结果：DeepSeek固定20题资格测试已完成。19/20官方成功，15/20整轨迹质量通过，模型费估算0.1163元；三台实例均已关机。下方价格咨询是较早阶段，完整实验交接见末尾。**

发布记录：5bc4d15已成功推送GitHub，同时补齐昨天未发布的8405b54。没有因此开机或部署新采集器。

1. 核心问题：DeepSeek Flash适不适合低成本生成Workplace教师数据？当前建议优先资格测试，质量未测。
2. 开始状态：SFT八步probe已完成；15条完整教师轨迹已批准；Token Plan交互示范成功但协议不合格；昨天三台实例均已关机。
3. 实际执行：读取官方价目表、工具/思考/缓存说明，复用历史token量做情景计算；更新普通API路线决定。没有模型调用、开机、采集或训练。
4. 变量/控制：只是价格算例。token量固定为旧Qwen样本；按峰谷/缓存变动。75%合格率是投影假设，DeepSeek尚未测得。
5. 原始结果：未缓存20次约0.424–0.848元；假定75%合格率，1000条合格约28–57元。详细公式和来源见成本JSON。
6. 代表轨迹：今天无新增轨迹。仍可学习旧training707的grounded lookup→update；不把昨天的9,805个provider tokens直接当作学生tokenizer的超限证明，旧运行配置未加载则已有独立证据。
7. 路线结论：采用用户新指示，回到普通API；停止继续建设Token Plan交互链路。Flash作为候选，先资格测试。
8. 未支持推测：Flash同样75%合格、同样缓存命中/长度、更快或更强，均未验证。
9. 三个代码入口（今天未改训练实现）：
   - `veriagent/teacher_rollout.py` → `teacher_trajectory`：row/task/cohort/config/transport/剩余时间（可选response_sink与producer）→ 完整采集记录；函数内部创建环境和编码器，执行多轮循环。目前是旧百炼链路，不能只改模型名就视为已兼容DeepSeek。
   - `veriagent/teacher_data.py` → `CanonicalTeacherEncoder.encode`：prefix messages、tools、assistant message → student input_ids/labels/token计数；检查完整上下文与监督目标。
   - `scripts/collect_teacher_probe.py` → `summary`：records和config → 成功、有效性、usage与费用汇总；新provider的缓存和费率字段需要单独适配，尚未执行。
10. 今晚知识点：累计请求tokens为什么多于最终轨迹长度；合格样本单位成本与API单价为何不同；默认thinking为什么必须从实际响应验证。
11. 面试追问（不提供答案）：如何比较两位教师的性价比？如何定义合格轨迹分母？为什么缓存率不能照搬？教师和学生tokenizer不同会影响哪些预算？低价教师成功率下降时如何决定是否继续？
12. 下一路线分叉：确认实际使用官方DeepSeek还是转售平台后，登记固定20题资格测试；通过后再决定采样规模。不是本次咨询已启动的实验。
13. 证据：`docs/DEEPSEEK_FLASH_ASSESSMENT_20260917.md`、`evidence/teacher-acquisition/deepseek_flash_cost_20260917.json`；原用量来源`TEACHER-ACQUIRE-20260916-001`。本日无新experiment_id或训练config。

## 后续实际实验：固定20题资格测试

1. **核心问题**：便宜的DeepSeek Flash是否能产生本项目真正可用的完整教师示范？
2. **开始状态**：旧Max有15条质量合格轨迹；DeepSeek仅核价，尚未运行。用户随后明确授权原20题，并取消12–14点窗口。
3. **实际执行**：独立API适配、56项离线控制、GitHub固定提交部署、真实20题采集、全量审核/重放/编码核验、取回证据、关机。没有训练。
4. **变量/控制**：换教师/provider；保留原training20/B1/schema/state/verifier和学生预算。DeepSeek没有发送未核验的seed字段；不能声称与Max相同API随机性。
5. **原始结果**：20有效，19官方成功，60/60工具可执行，65模型请求，88.080秒；300129input/7151output，缓存91.99%。模型费用估算0.11631784元，无卡会话约0.06270元，合计约0.17902元，非账单。
6. **代表轨迹**：707查询获得00000046再更新Proposal；859读取两页日历后重命名最后事件；1175漏掉今天到期的00000246；331官方状态成功但最终学生编码超限。完整原始证据在实验目录，不用手写观察代替。
7. **路线结论**：15条质量通过，值得作为下一阶段主教师候选。与旧Max同样15个任务合格，任务覆盖没有翻倍；新provider训练导出准入未做，尚未更新参数。
8. **未支持推测**：不能推断未见组合泛化、普遍优于Max或学生能力提升；不能把未返回的reasoning_usage写成实测0。
9. **今晚的代码入口**：
   - `veriagent/deepseek_teacher.py` → `request_body(messages, schemas, config, cap)` → 官方DeepSeek请求；关键是`thinking: {type: disabled}`，不同于百炼字段。
   - 同文件 → `usage(response)` / `estimated_cost(response, observed_at)` → 缓存/输入/输出及费率估算；未知费用不强制记0。
   - `veriagent/teacher_rollout.py` → `teacher_trajectory(...)` → API决策、真实工具执行、状态变化、终止和verifier的完整记录。
   - `veriagent/teacher_data.py` → `CanonicalTeacherEncoder.encode(prefix, tools, assistant)` → 学生input_ids/labels；context默认-100，assistant是监督目标，整条超限就拒绝。
   - `scripts/review_deepseek_qualification.py` → `main()` → 请求/响应/重放/编码证据核验与逐题审核理由；15条语义合格不自动变成训练入口已准入。
10. **三个知识点**：reward成功与整轨迹质量的区别；provider tokens与student tokens的区别；总采集费/合格轨迹才是有效数据成本。
11. **五个追问（无答案）**：为什么331成功却不能训练？为什么980/518要保守hold？1175是ID幻觉还是日期语义问题？为什么不能给本轮与Max宣传确定费用倍数？同15题多一份teacher轨迹为什么不等于多15题覆盖？
12. **下一路线分叉**：先完成DeepSeek训练导出准入，再登记数据扩展或SFT效果实验。没有自动重跑这20题、扩大context或进入DPO/RL。
13. **身份与路径**：`DEEPSEEK-QUAL-20260917-001`，执行commit`1ded6b7d2b1cd510dd9adf77ea8076e1e16bac83`；`configs/deepseek_acquisition_plan.json`；实验目录`api_events.jsonl`、`trajectories.jsonl`、`quality_review.json`、`review_summary.json`、`lifecycle_and_cost.json`。4次部署404属于运行前操作故障；模型运行0基础设施无效。完整报告`docs/DEEPSEEK_QUALIFICATION_REPORT_20260917.md`。


## 2026-09-17 remaining-pool window preparation

Added noon acquisition preparation: full project training743 minus original20 =723 new tasks,83 with empty references. CPU schema roundtrip and initial student tokenizer coverage723/723,max4215. No new model data yet. Study scripts/prepare_remaining_teacher_pool.py::main (split→frozen training-only cohort),scripts/collect_deepseek_window.py::preflight (hashes/cohort→eligibility),run_worker (key in memory+clock→raw trajectories),teacher_trajectory (task→real tools/state/verifier). Question: why can empty-reference reward1 be insufficient? Why exclude prior20 without deleting their failures? Why does8192 student limit matter for an API teacher? Why record inflight unknown costs? Why is scheduling collection not permission for SFT?


### Actual queue verified 2026-09-17

Latest handoff at10:31: actual723worker nowARMED at2ca291c,notacquired. ExperimentDEEPSEEK-SFTDATA-20260917-001; configconfigs/deepseek_window_acquisition.json; queueevidence/deepseek/window_schedule_receipt.json. Timer12:00start/14:00stop. Zero new modelcalls atverification. No new representative trajectories yet; use earlier20 qualificationexamples untilthisrunfinishes. Next fork afterresults is full semantic/encoding quality review and training protocol design,notautomaticSFT. Window includes83empty-reference cases,which may reward1 without establishing requested semantic completion.


### 2026-09-17 first running observation

2026-09-17 noon collection RUNNING: actual start 2026-09-17T04:00:00.008623+00:00 (12:00:00 China), PID1398/start_ticks1926709082/boot646ab369-44aa-4cde-b48b-2ff7d518caca matches the queued worker. Snapshot 2026-09-17T04:05:25.710978+00:00: 82/723 completed,0 infrastructure-invalid,75 official successes; quality approvals remain0 and these are interim acquisition counts,not SFT results. No duplicate launch/redeployment. Keep14:00 cutoff/shutdown and currentmonitor; localSSHclosed. Evidence:evidence/deepseek/window_monitor/20260917T0405-progress.json. No new training stage. The observed start time distinguishes a queued process from actual API execution; raw trajectory quality review comes after preservation.


# 午间全量采集完成后的学习交接

1. **核心问题**：普通 DeepSeek Flash 能否在单次午间窗口内，把全部剩余 training 任务变成可审查的真实 trajectory？采集与完整性证据回答“能”；最终 SFT 语义质量尚待审查。
2. **开始前**：原20题资格测试完成；723新题已冻结，12:00排队开始；第一次8步LoRA probe是昨日已完成的独立实验。
3. **实际执行**：今天12:00:00至12:50:28，723题各一次、2443次API请求，真实执行工具和state verifier。之后本地重放723条并核对2443对wire请求/响应。全部原始证据已下载并核验，三台实例均关机，两项监控暂停。
4. **变量与控制**：扩大的是training任务覆盖；teacher/B1/tool/state/verifier、6轮、8192学生context、2048输出不变。这不是学生模型前后对照，不能据此声称能力提升。
5. **原始结果**：664/723官方成功；0infra-invalid；2411/2438executable calls；API约2.12元，含无卡等待与部署总计约2.40元。83空reference任务中80成功。机械未标记629条，94条被标记；最终新增语义批准0条，参数更新0次。
6. **代表轨迹**：task691先查average session duration，再按条件作line plot，reward1；工具返回的是环境模拟的plot路径，不能说已经生成真实图片。task751先查September15与之后日期的engaged users，再按“区间平均值”判断不画图，reward0；属于条件解释/聚合方式的待确认failure候选，不是最终taxonomy标签。原始messages、observations、reference均在trajectory JSONL中。
7. **路线结论**：教师采集通道与完整证据链已建立，全743个training任务均有DeepSeek尝试记录。新增723的整条质量审核是下一步，完成后才能冻结SFT数据；没有自动进入训练。
8. **尚未支持**：629条机械未标记不等于629条可训练。不能证明grounding完全正确、分页完整、自然语言答案正确、学生success提升或held-out composition泛化。官方reward=1和训练可用性是不同门槛。

## 今晚值得理解的四个代码入口

| 文件 → 函数 | 输入 | 输出 | 在流程中的作用 |
|---|---|---|---|
| `scripts/prepare_remaining_teacher_pool.py` → `main` | 冻结split和已尝试20题 | 723名单、schema bank、初始token覆盖 | 保证只选training、不根据新模型成绩换题 |
| `scripts/collect_deepseek_window.py` → `run_worker` | 固定config、名单、临时环境凭据 | 原始API/trajectory JSONL、progress/result/remaining | 到12:00才开始，14:00硬截止；每题后落盘，基础设施错立即停止 |
| `veriagent/teacher_rollout.py` → `teacher_trajectory` | 单任务、真实API transport、时间余额 | 完整messages、tool events、state hashes、reward | 模型决定调用，环境真实执行，把response与新observation再交给模型 |
| `scripts/audit_deepseek_pool_acquisition.py` → `main` | 下载的原始API和trajectory、原名单 | `integrity_summary.json`与`mechanical_screen.json` | 核对请求、重新执行工具并重算学生编码；不批准语义质量 |

核心区别：`env.step(tool_call)` 执行真实动作；`env.verify(reference)` 检查环境结果；`encoder.encode(context, tools, assistant)` 检查学生能否把该assistant决策作为监督目标。三者回答不同的问题，不能用其中一个替代其他两个。

## 今晚三个知识点

- **Verifier覆盖范围**：数据库状态正确，为什么不一定意味着最终回答正确？空reference的任务尤其值得看。
- **整条监督与上下文预算**：API teacher能够回答，不代表Qwen3学生8192token以内装得下全部context与target；不能为通过审核悄悄删掉错误前缀。
- **机械检查与语义审核**：schema正确只证明参数形状合法；筛选未报警还必须核对查询范围、分页、条件解释与事实陈述。

## 五个面试追问（不给答案）

1. 664条reward1为什么最后不一定能得到664条SFT数据？
2. 83条空reference任务应如何评价，为什么不能直接删掉或全部放行？
3. task751的工具调用都能执行，为什么最终仍失败？
4. 如何证明保存的trajectory确实对应当时发出的请求及真实环境状态？
5. processed tokens与supervised tokens为什么差这么多，对S1/S2公平比较有什么影响？

明天路线分叉：先做整条语义审核和DeepSeek学生导出准入；质量通过后讨论正式S1/S2的训练token预算及固定eval。不要直接把全部机械候选拿去训练。

证据：`DEEPSEEK-SFTDATA-20260917-001`；execution commit `2ca291cde64b5c96baec2c9ebeb91e853665ae0a`；配置 `configs/deepseek_window_acquisition.json`；完整原始归档 `evidence/deepseek/DEEPSEEK-SFTDATA-20260917-001-evidence.tar.gz`；派生审核与费用位于同名experiments目录。报告 `docs/TEACHER_FULL_POOL_RESULT_20260917.md`。离线审核首次GBK解码失败已保留为工具故障，未污染模型成绩；没有重发API。
