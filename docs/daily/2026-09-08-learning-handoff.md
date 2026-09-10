# 2026-09-08 Learning Handoff：间隔三天后的复习整理

1. **今天回答的核心问题**：怎样从基础机制重新接回已完成的 Day 3，并把之前分散的四课整合成一份可独立阅读的学习文件？
2. **开始前状态**：CPU 审计、75 条真实模型推理和 Day 3 分析已完成；没有参数更新，考核未评分。前三课的历史“尚未运行模型”措辞需要明确日期边界。
3. **实际执行**：读取约定、当前状态、四课、旧考核、报告与关键代码；编写 [学习合订本](../learning/2026-09-08-return-to-project.md)，更新 README、START_HERE、PROJECT_STATE、考核入口、DECISIONS、HYPOTHESES 和预算记录。未新增实验。
4. **唯一变量 / 控制变量**：本次是学习文档整理，无研究自变量；模型、任务、原始轨迹、标签与实验配置均沿用既有证据。
5. **原始结果**：无新增结果。复习引用 B0 11/48、动作任务 5/40；B1 8/24、动作任务 5/20；主要配对为 seed42 的 5/24→8/24。三个新增成功均为恢复。
6. **代表轨迹**：task 0 的虚构 ID 与成功恢复；task 12 的低质量 no-op 成功；task 184 的姓名当 ID；task 1063 的真实 ID 但错误对象；task 18 的同 prompt 成功/失败学习 pair。路径见合订本，全部为 dev 学习证据。
7. **路线级结论**：保持原停点。硬件/执行链通过，B0 成功任务数量不足，B1 仍是有条件候选；本次不提升训练或泛化资格。
8. **尚未支持的推测**：S1/S2 收益、DPO 效果、在线 RL、严格组合泛化、BFCL 成绩、学习者掌握程度均未有新增证据。H3 仅修正过时的“多轮未测”，引用已有 context-cap 结果。
9. **五处代码 / 函数导读**：

| 文件 → 函数 | 输入 → 输出 | Pipeline 作用 |
|---|---|---|
| scripts/run_day3.py → inference_trajectory | 模型、任务、配置、seed → 完整轨迹 | 决策与预算循环 |
| veriagent/policy_protocol.py → parse_tool_calls | 文本 → calls/errors/content | 解析动作 |
| veriagent/environment.py → WorkplaceEnv.step / verify | action/reference → observation/diff/reward | 实际执行与重放评分 |
| vendor/Gym/resources_servers/workplace_assistant/utils.py → is_correct | 预测/参考动作 → bool | 官方最终状态语义 |
| veriagent/token_mask.py → TokenMaskInspector.inspect | messages/tools → ids/labels | 监督边界检查 |

10. **今晚学习点**：state/observation/reward 的边界；分母、grounding 与目标条件；SFT/DPO 的 context/target 和逐轮对齐。
11. **五个追问，不给答案**：

- 查询不改变数据库，为什么仍可能是完成任务的必要步骤？
- 能执行的调用为何可能让任务失败，reward=1 又为何可能不值得模仿？
- B1 的恢复成功和 wrong-argument 分母变化分别支持什么结论？
- 四个 prefill tokens 揭示了生成和训练之间的什么边界？
- 为什么同任务 DPO 两支要保留自己的 observations，dev pair 又不能正式训练？

12. **下次需确认的路线分叉**：先提交合订本 A1–A5，再按回答安排证据追踪与实验设计。研究路线仍待讨论共同 baseline、弱域 training 数据来源和 composition 设计；学习材料不构成新实验授权。
13. **实验与证据身份**：本次无 experiment_id 或运行 config，不向实验 registry 添加虚构 run。引用 Q0-SMOKE/B0/B1-20260904-001 的各 config/identity/trajectories/result，以及 reports/day3-reviewed-v2、evidence/day3。GPU 执行 commit 为 cb4067c3e0dd21723d5664e7ccd27cdd3120c51e，Day 3 交付 commit 为 5a5dec8aa8c4980a8ef218e78828918c27183167；本次学习整理文件保存于工作区。新增付费 GPU/API 费用为 0。

## 同日补充：手机与 GPT 的完整代码课

用户说明晚上不开笔记本，需要代码直接出现在学习文件中。合订本第 11 章已替换为 21 段源码摘录和逐段解释，覆盖初始化、工具注册、模型主循环、模板/tokenizer、预算、生成、parser、messages 回填、真实工具状态写入、verifier、online/replay 对比、loss mask 与 policy log-prob。

嵌入的 task 0 包括四轮输入/输出 token、五封搜索结果、错误 observation 和真实新增 outbox 行；task 18 包括两支动作与观察、改名前后状态和 dev 限制；CPU token 表保留真实位置、token ID 与 label。新增代码/证据追踪题都可直接用文内内容作答，另附给 GPT 的分段教学请求。

源码摘录来自固定本地文件，教学伪代码和假设 log-prob 明确区分，不作为运行事实；没有修改 runner、工具语义、原始实验或评分结果。考核仍未收到答案、未评分。本次只核对文档中的源码与已有证据，不产生模型 run 或 GPU 费用。

交付核对：21 段共 432 行源码与本地源文件逐段一致，源码片段通过语法解析；14 行 token/label 与保存的 CPU fixture 一致；task 0 的四轮 token 数、嵌入状态差异及 reward 与原始轨迹一致。文内本地链接均可解析，考核 score/pass 仍为 null。这些是文档核对，不是新模型或训练测试。

## 同日补充：Agent与后训练竞赛筛选

后续用户澄清：目的是弥补无论文背景、12月开始投实习；已在做ARC-AGI-3，计划等Milestone2发布再集中投入。不要把先前BDCI推荐误记为用户决定。补查[Kaggle规则](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview)确认里程碑奖金候选Notebook须在对应截止日前开源；[官方Milestone1文章](https://arcprize.org/blog/arc-prize-2026-milestone-1)于7/6发布前三名方案，[冠军团队文章](https://tufalabs.ai/research/duck-harness/)于7/1发布。M2截止9/30，最终提交11/2；未查到M2获奖分析的确切发布日期。等待M2公开方案是基于这些规则的推断，不能替用户确认意图。没有新实验或学习评分。

用户要求国内外高认可度、人数多且12月前出结果的比赛。按2026-12-01前正式结果筛选，交付 docs/learning/2026-09-08-agent-competition-shortlist.md。国内优先CCF BDCI职场Agent（官网1329人，9/30截止、10月颁奖）；科研Agent为备选（1311人，10/9截止）。海外AWS应用赛约8100人，10/14 PDT公布结果；Agenthon与Steerability因正式结果日期未明确列为条件候选。PostTrain官网与仓库存在组织状态/模型信息差异，不能宣称已是正式NeurIPS大规模比赛；ARC最终结果12/4，严格排除。

学习点：截止提交与公布结果不同；报名人数不是有效队伍；Agent工程优化不等于参数后训练；官网摘要与单题正文可能冲突。无新轨迹、代码实验或代码函数导读，本次为只读资料研究。未联系主办方、未报名、未评估学习答案，研究假设与实验阶段不变。后续路线由用户选择，竞赛建议不是训练授权。
