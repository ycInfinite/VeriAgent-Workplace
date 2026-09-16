# 2026-09-16 Handoff：采集质量审核与教师准备

**最新停点：用户确认百炼普通按量API和workspace端点。教师采集器已实现、55/55无网络检查通过，等待用户允许无卡启动和远端终端隐藏Key输入。没有教师调用或SFT更新，两台实例本轮再次确认关机。下面查价与采集停止是较早记录，最新交接见末尾。**

1. **核心问题**：对当前单卡8B LoRA方案，市场上哪些配置更值得选？
2. **开始状态**：无卡准备与GitHub同步已完成，GPU训练尚未执行；用户要求直接查看AutoDL，而非让其转述价格。
3. **实际执行**：通过浏览器查看官方首页及用户已登录的算力市场，按量筛选北京B区、A800专区、西北B区，核对GPU、价格、CPU/RAM、驱动与空闲量。
4. **变量/控制**：无模型实验；比较单GPU按量配置，会员展示价与原价分开，不混用NVLink版和普通A800。
5. **结果**：普通A8005.59/5.88元每小时；PRO6000 96GB6.98/7.35；北京B区A800-NVLink7.98/8.40；H8009.98/10.50。完整过滤条件见GPU_PRICE_CHECK_20260916.md。
6. **代表轨迹**：本日无新增轨迹，未检查封闭评测案例。
7. **路线结论**：PRO6000为综合候选；普通A800最低小时费；NVLink版非单卡优先；H800需吞吐证据判断总费用。
8. **未支持推测**：没有证明PRO或H800在实际SFT/rollout上快多少，没有确认用户最终会员结算价，没有租卡或迁移。
9. **后续应理解的三处代码**：collect_training_probe.main（固定任务→采集时间/token）；run_sft_probe.main（批准数据→step time/VRAM/更新检查）；github_file_sync.main（固定commit→远端执行文件校验）。本次均未执行。
10. **粗颗粒知识点**：小时价≠每次成功成本；高价卡需要足够吞吐增益；驱动/功耗/显存也影响实际可用性。
11. **五个备用追问**：为何6.98元卡可能比5.59元卡更省？H800要快多少才抵消价格？单卡为什么不直接受益于GPU间NVLink？峰值TFLOPS能否当实测吞吐？已有实例迁移成本如何计入？
12. **下一步分叉**：选择继续使用现有80GB实例，或采用PRO6000候选；实际运行前核对配置。没有自动启动/迁移。
13. **证据/费用**：页面https://www.autodl.com/market/list，日期2026-09-16；本次不是训练实验，无experiment_id、新模型config或GPU计算费用。既有实例是否持续计费未查看，不能将其累计费用记为0。没有读取或保存账号凭据、余额或支付信息。

## 最终实验交接：迁移 → 采集 → 质量门槛未通过

1. **核心问题**：原A800准备目录能否迁移至PRO6000，固定20题能否产出至少两个可整条监督的高质量成功轨迹？
2. **开始状态**：两台均关机，新盘空；旧盘已有固定权重、venv、任务和执行代码。没有可训练模型轨迹，SFT代码仅准备。
3. **实际执行**：按用户指定平台跨实例拷贝目录；用户明确批准开新机；核验35文件/5权重与BF16；执行SFT-ACQUIRE-20260916-001；取回逐项验哈希；审核3条成功；用户选择保持原目标并停在审核；关闭新机。
4. **变量/控制**：新的training任务与PRO6000运行环境；保持既定20题、seed42、B1、8K/6轮/2048输出和官方工具语义。未按结果换题、加采样或改prompt。
5. **原始结果**：20/20有效，3/20官方成功，0基础设施无效；51calls中47可执行，输入306647/输出3310，88.021秒。allocated峰值16.519GiB；采样GPU used峰值18547MiB、平均利用率78.11%。整轨迹批准0，参数更新0。
6. **代表轨迹**：450错枚举后恢复；707编造ID后查到正确ID再恢复；1183删对当前对象但把“全部未来”限定到12月，范围依据不足。官方reward均保留1，质量标签由Codex审核而非独立人工裁决。
7. **路线结论**：迁移和真实推理通过；完整高质量数据门槛未通过。SFT未启动，不能报告CE/梯度/LoRA结果。
8. **未支持推测**：没有证明PRO相对旧卡加速倍数（任务不同）；没有证明选择性正确片段能提升Agent；没有训练或泛化结果。
9. **三处代码与两份审核产物**：

| 文件 → 函数/产物 | 输入 → 输出 | pipeline作用 |
|---|---|---|
| scripts/collect_training_probe.py → main | 固定20题/模型 → 原始rollout与资源指标 | 本轮实际采集 |
| scripts/run_day3.py → inference_trajectory | 单任务/seed/B1 → messages/events/verifier | 真实模型工具循环 |
| veriagent/sft_data.py → admit_training_trajectory | 轨迹/任务来源/审核 → 准入或拒绝 | 不让reward1自动进入训练 |
| quality_review_full_trajectory.json | 三条成功证据 → 0批准 | 显式过程质量决定 |
| route_decision.json | 用户选择 → 原方案停止状态 | 防止自动改变mask目标 |

10. **三个粗颗粒知识点**：状态成功与可监督质量不同；错误恢复有价值但不能未经设计把错误动作也当正目标；不以跑通训练为理由放宽门槛。
11. **五个备用追问**：为什么450/707成功仍未批准整条监督？1183为何保留成功标签却暂缓训练？只监督正确片段改变了什么训练目标？为什么20条结果不支持跨卡性能结论？如何区分模型失败、数据质量拒绝和基础设施无效？
12. **下一步路线分叉**：选择性目标提案（2任务5片段、245目标tokens）未被用户采纳。保持原整轨迹要求，后续高质量数据来源待新指示；不追加采样、重启GPU或执行更新。
13. **身份、证据、费用**：执行commit bc5aa55c3b97174822893c789b236cf5e43fcaf3；模型revision b968826d9c46dd6066d109eabc6255188de91218。实验目录含config/identity/trajectories/gpu_samples/result、完整审核、未采用提案和用户决定。迁移GPU preflight与原始日志在evidence/sft-acquisition；copy/lifecycle在evidence/migration/2026-09-16。采集运行估算0.1707元，保守观察窗口线性估算1.96元，两项不可相加且非实际账单。新旧机均确认关机、源数据未删除。

总报告：[SFT采集与质量门槛](../SFT_ACQUISITION_REPORT_20260916.md)。原始失败与成功全部保留，未修改旧tau2或封闭评测内容。

## 最新交接：完整教师轨迹的 CPU 准备

1. **核心问题**：保留完整轨迹监督目标，能否准备隔离答案的教师输入及学生训练格式？用户指定的百炼Token Plan能否用于采集？
2. **开始状态**：原20条中3条官方成功但0条获整轨迹批准，选择性正确片段方案已拒绝。用户恢复下一步推进。
3. **实际执行**：实现请求隔离与canonical学生编码；CPU运行TEACHER-PREP-20260916-001；核验百炼工具调用、渠道规则与价格；没有接触Key、开机、发API或训练。
4. **变量/控制**：只变数据来源准备和格式，不改20题/B1/工具/学生revision/整轨迹质量门槛；旧轨迹仅格式压力样本。
5. **原始结果**：20/20请求哈希匹配；69/69轮编码、无删轮；processed309957/supervised3310，最大5316；5/5负向检查通过；1轮canonical IDs不同于原采样。CPU2.0213秒、付费实验0元。
6. **代表证据**：oracle字段被拒绝；dev请求被拒绝；旧450错枚举和707假ID仍不能整条监督，1183范围问题仍保留。没有新教师success/failure轨迹。
7. **路线结论**：输入隔离与已有样本格式可行。Token Plan个人/团队均排除自定义批量脚本，先落实普通按量API；不能把编程套餐暗中用于此次采集。来源见[报告](../TEACHER_PREPARATION_REPORT_20260916.md)。
8. **未支持推测**：尚未证明qwen3.8-max能稳定完成本环境；尚未获得可训练示范、真实CE/梯度/adapter保存重载结果。API采集器与教师准入尚未完成端到端实现。
9. **今晚理解的代码**：

| 文件 → 函数 | 输入 → 输出 | 作用 |
|---|---|---|
| veriagent/teacher_data.py → teacher_request | training行+固定manifest+B1 → messages/tools | 明确只送任务与工具，不送ground_truth |
| veriagent/teacher_data.py → validate_request | 请求+任务manifest → 通过或ValueError | 拒绝额外oracle字段、错pool、改prompt/tools |
| veriagent/teacher_data.py → CanonicalTeacherEncoder.encode | 历史messages+tools+完整assistant轮 → input_ids/labels | 学生tokenizer重编码，历史mask，完整决策作为target |
| scripts/prepare_teacher_data.py → main | 固定20题/旧格式样本 → audit/result | 记录证据和负向检查，不请求模型 |
| veriagent/sft_data.py → admit_training_trajectory | 轨迹+身份+质量审核 → 准入/拒绝 | 当前旧准入不会自动放行新的API教师数据 |

实际编码中的核心部分如下；已经在CPU格式样本上执行，但不是训练结果：

```python
prefix = self.inspector.render(prefix_messages, tools, generate=True)
complete = self.inspector.render(
    prefix_messages + [assistant_message], tools, generate=False
)
if not complete.startswith(prefix):
    raise ValueError('Canonical assistant prefix is not a continuation of the input')
suffix = complete[len(prefix):]
if not suffix.endswith('<|im_end|>\n'):
    raise ValueError('Unexpected canonical assistant termination')
target_text = suffix[:-1]  # 仅去EOS后的模板分隔换行，不删除动作或轮次
prefix_ids = self.inspector.tokenizer.encode(prefix, add_special_tokens=False).ids
target_ids = self.inspector.tokenizer.encode(target_text, add_special_tokens=False).ids
# 返回值中的训练表示：
input_ids = prefix_ids + target_ids
labels = [-100] * len(prefix_ids) + target_ids
```

这里的target_ids是学生重编码后的示范目标，不是闭源教师生成时的token IDs；保留全体assistant轮次也不意味着它们已获质量批准。

10. **学习点**：格式合格与行为合格是两道门槛；跨模型SFT要用学生tokenizer；APIusage成本tokens与学生监督tokens要分开。
11. **五个追问（不附答案）**：为什么不能向教师发送ground_truth？为什么需要每轮真实observation？教师token IDs和学生target IDs为何不能混用？69轮编码通过为何仍0条可训练？更强教师的轨迹能否保证SFT后Agent更强？
12. **下一步路线分叉**：是否已有普通按量百炼API访问；只告知可用性，Key不发聊天。确定接入后实现/登记固定20题采集，再做完整质量审核。此时无需GPU；不自动扩大到S1/S2/DPO/RL。
13. **身份与路径**：CPU代码b1f67b34b5fc18dd8e607ade68524332d58c4193；config为configs/teacher_preparation_audit.json及实验目录快照；原始日志为request_manifest.jsonl、format_audit.jsonl、negative_controls.json，汇总result.json，身份identity.json。模型/data保持固定revision；官方网页核验日期2026-09-16、无公开commit。没有新无效运行。学习测验未评分，不作为推进门槛。

## 补充交接：普通 API 采集器就绪

1. **问题**：能否在不开GPU、无Key落盘的条件下，准备真实教师→工具→状态→verifier采集？
2. **起点**：已有输入/格式隔离模块；普通API渠道此前待落实。
3. **执行**：用户确认普通Key和workspace端点；新增transport/采集器/八字段配置；扩展4文件GitHub白名单；运行CPU回归。聊天所贴密钥未写入项目/日志，建议换新后远端隐藏输入。
4. **变量/控制**：改变采集接口，保持20题/B1/工具语义/学生revision和预算；无模型实验。
5. **结果**：55/55检查通过；网络请求0、新模型轨迹0、新数据批准0、更新0、GPU-h0。
6. **代表轨迹**：仅重放旧training707四轮，动作与最终状态相同；截断fixture不执行动作，401 fixture不重试且usage未知，非法JSON仍是policy格式失败。
7. **结论**：CPU采集器可进入远端预检；不代表教师能产出高质量成功示范。
8. **待证**：账号权限、真实API兼容性、模型质量、教师canonical数据训练准入、CE/LoRA完整性均未实测。
9. **代码导读**：

| 文件 → 函数 | 输入 → 输出 | pipeline作用 |
|---|---|---|
| veriagent/teacher_rollout.py → request_body | messages/原始schema/config → HTTP JSON body | 只改协议外壳，不给参考答案 |
| veriagent/teacher_rollout.py → BailianTransport.__call__ | body/超时 → API JSON或安全错误 | 普通API、无自动重试、无Key日志 |
| veriagent/teacher_rollout.py → teacher_trajectory | 固定任务/transport → 全轨迹、状态、verifier | 真实工具闭环，未自动批准训练 |
| scripts/collect_teacher_probe.py → preflight/main | GitHub部署清单/Key → 有界实验目录 | 校验、隐藏输入、费用记录及停止 |
| scripts/audit_teacher_collector.py → run | 旧707 fixture → 55项检查结果 | 无网络验证协议和状态，不是新rollout |

10. **学习点**：HTTP body与Authorization header分离；模型参数错误与API基础设施错误不同；已知usage费用与未知请求费用分别记录。
11. **五个追问**：为何401不能算模型任务失败？为何截断JSON即使看似完整也不执行？为何工具strict字段不能静默删除？为何供应商tokens不能替代学生tokens？为何55项通过不意味着SFT数据已合格？
12. **下一步**：用户允许新实例无卡开机后，GitHub同步/远端预检/隐藏Key输入/固定20题采集。Key不再发聊天，GPU保持关闭，不自动进入SFT。
13. **证据**：TEACHER-COLLECTOR-CPU-20260916-001；代码16a36e9；实验config/identity/checks/replay_fixture/result；下一采集配置configs/teacher_acquisition_plan.json；操作文档TEACHER_API_HANDOFF_20260916.md。无无效CPU run，无教师运行或费用，学习未评分。
