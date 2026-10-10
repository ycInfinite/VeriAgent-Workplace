# Failure taxonomy：Day 3 已有真实轨迹

2026-09-17 DeepSeek training20（资格测试，非sealed评测）：331完整学生序列超限；1183无依据的未来截止范围；980/518分页覆盖不足但官方状态成功；1175到期日边界解释造成遗漏。保留原始reward，0基础设施无效模型轨迹。schema错误0/60不代表语义任务完整，质量通过15/20。

2026-09-16 training采集补充：20条均为有效模型交互。450错误枚举后恢复、707虚构ID后恢复、1183状态正确但未来范围论证不足，均未批准整条监督；1183是过程质量暂缓，不改官方成功标签。仅Codex审核，未独立人工裁决。详见SFT_ACQUISITION_REPORT_20260916.md。

以下定义最初来自 CPU 阶段；Day 3 已用 48 条 B0 和 24 条 B1 实际轨迹作逐条复核。当前计数见 reports/day3-reviewed-v2/metrics.json 和 annotations.json，reviewer=Codex，尚未独立人工复核。它们描述本 cohort 和本 harness，不是模型的一般能力结论。

| 标签 | 判定证据 | 排除/注意事项 |
|---|---|---|
| wrong_tool | 未注册工具，或观察/任务证据表明选择错误 | 不因与 reference 顺序不同判错 |
| wrong_argument | JSON/schema 不合法，或状态证明参数语义错误 | HTTP 200 仍可能包含工具错误 |
| identifier_hallucination | ID 不存在且无来源依据 | 与存在但未 grounding 的 ID 区分 |
| ungrounded_identifier | 用户与前序 observation 中无可追溯来源 | 正确猜中 ID 也不自动算 grounded |
| missing_prerequisite | 尚未获取做出该决策需要的状态/实体信息 | 不机械要求某个唯一查询工具 |
| redundant_action | 无新增信息/必要状态效果，也无合理恢复目的 | 状态改变后的重复查询可能合理 |
| retry_loop | 相同参数/相同结果/无状态推进的连续重复，初稿阈值 3 次 | 正常纠错不是循环 |
| premature_termination | policy 主动停止，必需任务仍未完成 | 达到 token/round cap 单列 |
| failure_after_partial_progress | 已完成部分目标，后续动作使最终目标失败 | partial progress 不折算正式成功 |
| unsupported_completion_claim | 自然语言宣称完成但观察不支持 | 官方 reward 不直接检测它 |
| infrastructure_invalid | 模型 API/环境进程/工具适配等非 policy 原因失效 | 保留原始记录，不计能力指标，计费用 |
| attribution_pending | 尚不能区分模型错误、数据歧义和环境问题 | 不强行塞入模型 failure 标签 |

每条标注记录 task_uid、trajectory_id、最早因果错误步骤、支持的 observation/state diff、主要标签、次要标签、置信度和复核说明。优先报告 earliest causal failure，而非把每个后续症状都算一次主因。

CPU 发现的 noop blindness、未评分的自然语言、plot-path simulation 属于环境/评分覆盖发现，不是 Qwen 失败。

## 新观察到的具体模式

| 模式 | 实际例子 | 注意 |
|---|---|---|
| 姓名/占位符被当成 ID | task 184 的 Quinn Taylor；task 0 的 last_email_id / 12345678 | JSON 字符串合法不代表 typed identifier 合法 |
| 准备写入的新值被当成检索条件 | task 1/18 用目标新名称查旧事件 | B1 在这两题通过后续扩大查询恢复 |
| 未 grounded 邮箱/虚构可选属性 | task 356/220/314/918/12 | task 12 即使 reward=1 仍有错误 |
| 参数接口迁移错误 | task 414 把其他工具的 page/page_size 带入 PM search | schema-invalid，属 policy 参数错误，不是 API 故障 |
| 合法 ID、错误目标范围 | task 1063 删除别人的客户；B1 task 1219 删除过去事件 | 不计作缺少 ID 来源，计作语义参数/约束错误 |
| 错误 metric / temporal 参数 | task 561/669、363/385 | 工具返回成功也可能对应错误目标参数 |
| observation 膨胀与有限恢复空间 | task 669/952 超出 8K | 保留完整观察，按预算失败处理，不裁剪后冒充原协议 |
| 不必要的能力否认/提前停止 | task 510/1219 的 B0 | 工具实际可用；不能把模型的否认当作基础设施不可用 |

原始自动计数是 candidate：字符串出现检查会漏掉“姓名当 ID”，failed-finalization 也不等于所有情况都是提前停止。复核后的提前停止排除预算 cap 和“做错修改后结束”；每个口径及分母在 DAY3_REPORT 中说明。成功恢复中的错误保留在 call-level 指标，但不把整条轨迹改成官方失败。


## 2026-09-17 completed723 acquisition

Full723 acquisition preliminary diagnostics (not finalized semantictaxonomy):27 schemaargumenterrorcalls on26trajectories;unknownnames0;2samestate-repeatcalls;0three-callloops;0unobservedIDcandidates/1181(notproofnoIDerrors). Terminations702assistantfinal/15contextlimit/3roundlimit/1generationincomplete/2encodingrejected. Example751 is conditional interpretation candidate:comparesperiodaverageinstead of checkingdailythreshold,doesnotplot,reward0. Must review usersemantics/observations before finalfailurelabels.


## 2026-09-17 pre-SFT readiness

Wholeteacherreview150 finds13held despite mechanical success:263cross-domain taskID usedwithcalendartool;1160/1204/615/1100/415/1123latest-emailpaginationunproven;1045dateboundaryunresolved;1079unnecessaryout-of-rangepage;1124announcedbroaderverificationnotperformed;802/83/764faultynumericalaggregation. These teacherqualitylabels do notalterofficialreward or becomeBasefailurecounts; S2targetbasis remainspriorDay3failureevidence.


## 2026-10-10 new SFT development trajectories

Fresh144validtrajectories,notreusedDay3labels. Typedcandidatecallcounts24/76(BASE),0/76(S1),2/125(S2);thesearemechanicalvisibility/currenttablechecks,notfullsemanticrates. Reviewedtask184showsname-as-ID→lookup→observedIDdeletion;S1task0recoveringunsupportedrecipientkeyword;S1task414groundedIDbutCompletedwrongtarget;S2task1wronglast-eventordering;S2task220inventedoptionalcontactattributes;S2task12mutatesInReviewafterInProgressisempty. S1task952excludesdue-todaywhileofficialreferenceincludesit:attributionpending,notautomaticDPOrejected. Officialrewardsunchanged. See reports/sft-comparison-20261010/representative_review.json;Codexsingle-reviewer,posthocillustrations,nofullwrongargument/redundancy/prematuremetricclaim.


补充诊断盲点：S2 task363/seed42重复创建同一图表直到轮数上限，但每次都会修改analytics._plots_data，所以原same-state循环检测始终为false。已人工确认该例的重复行动；“state changed”不等于“任务有进展”。原始自动指标保留，不把候选循环数0写成真实循环率0，也不在本轮中途修改harness。


## 2026-10-10 全部 post-SFT 官方失败初步归因

覆盖S1失败13条、S2失败15条，分母仅失败轨迹。S1：日期/时间范围/条件7，Completed目标2，过滤与放弃2，due-today归因待定2。S2：日期/条件6，排序目标3，可选属性虚构2，范围越界4。文件experiments/POSTSFT-AUDIT-20261010-001/postsft_failure_triage.json包含每条source SHA、seed、理由；Codex单审，未独立人工裁决。成功轨迹仍可包含错误，不把此次triage宣称为完整call-level语义错误率。DPO候选负例单独审核，全部属于原training20，不移用dev失败。
