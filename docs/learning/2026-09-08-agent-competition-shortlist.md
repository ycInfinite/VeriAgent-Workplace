# Agent / 后训练赛事筛选（2026-09-08）

范围：从查询日仍可新报名、2026-12-01 前公布正式结果；综合考虑主办方、实际报名规模、Agent 算法与后训练相关性。国内认可度是基于主办方与赛制的判断，不代表任何学校的竞赛认定目录或招聘保证。

## 优先候选

| 比赛 | 报名/提交 | 结果 | 规模与方向 | 结论 |
|---|---|---|---|---|
| CCF BDCI 华为 openJiuwen：Agent 职场长程生存与晋升挑战 | 9/30 12:00 报名组队截止，9/30 24:00 初赛提交截止，北京时间 | 10月中旬评审，10月下旬颁奖 | 官网显示 1329 参赛人数；48个月部分可观测职场模拟，长期规划、Skills、上下文管理 | 国内综合首选；后训练模型能否接入尚未核实 |
| CCF BDCI 华为 openJiuwen：Agent 科研论文自动生成 | 10/9 12:00 报名截止，10/9 24:00 初赛提交截止，北京时间 | 10月中旬评审，10月下旬颁奖 | 官网显示 1311 参赛人数；选题、调研、方法设计、撰写、分析自动化 | 国内备选，偏研究工作流；非直接后训练赛 |
| AWS Agents for Humans Hackathon | 9/14 17:00 PDT 提交截止，即北京时间 9/15 08:00 | 10/14 14:00 PDT，即北京时间 10/15 05:00 | 官网约8100人（概览8124、日程8100）；Strands Agents SDK 应用开发 | 国际大厂与规模证据较强，偏工程应用，时间紧 |
| ITSAC 2026 创新挑战赛：赛题2/3 | 当前正文报名至9/30，10/11 18:00提交 | 11/15前公示，11/20–22颁奖交流 | 中国智能交通协会；交通仿真智能体、低空任务智能体；人数未公布 | 期限满足，行业性强，不能认定为大规模通用LLM赛事 |

CCF两个候选各奖金池5万元，前5支团队奖项为1个一等奖、2个二等奖、2个三等奖；每队1–5人，获奖证书由CCF颁发。报名人数不是队伍数、有效提交队伍数或获奖概率。

## 强相关但不完全满足条件

| 比赛 | 已核实事实 | 缺口 |
|---|---|---|
| NeurIPS 2026 Agenthon，优先T1 Coding | 9/28报名截止；9/29–10/12私有终评；10/13–25复核；12月会场展示；1–3人队伍；T1为可验证金融代码Agent | 正式公布最终名次的日期未明确，不能把复核结束当公布结果；参赛人数未公布 |
| NeurIPS 2026 The Steerability Challenge | 9/10开放，11/21 AoE截止；允许输入、权重、激活、解码干预及有来源的adapter；优化诚实性并约束通用能力退化 | 结果公布日期、参赛人数未证实；获奖规则要求成员赴巴黎现场报告 |
| PostTrain Arena | 网站列10/21提交、11/7公布；提交RL环境，由主办方固定SFT→GRPO并测泛化 | 官方仓库仍称proposed NeurIPS competition；未出现在已核实的NeurIPS 2026正式16项名单中。官网Qwen3-8B与仓库Qwen3.5-9B不一致；没有赛事人数证据。仅作为待核实技术候选 |
| ARC Prize 2026，ARC-AGI-3 | 10/26报名截止，11/2提交截止，12/4公布获奖 | 严格不满足12月前正式出结果；若可接受12/4才可考虑 |

Agenthon和Steerability均在NeurIPS官方2026 Competition Track名单中。竞赛获奖不等于NeurIPS主会论文录用。

## 排除与网页冲突

- CCF BDCI金融分析Agent：详情页明确“报名截止”，8/23截止报名及初赛提交。列表显示10/31结束不等于还能报名。
- CCF BDCI百度DuMate Skills优化赛：详情页明确“报名截止”，不作为当前新报名候选。
- 腾讯开悟2026全球公开赛：官方总赛程为2–3月报名、4–8月比赛、8月颁奖；某些页面仍显示进行中，不据此推荐当前参赛。
- CCKS2026行为与知识调控：官方天池页复赛8/15结束，不采用聚合站的9/30截止说法。
- ITSAC搜索摘要仍显示9/13报名截止，打开同一官方页正文已为9/30；采用当前正文并记录冲突。
- BDCI科研论文赛正文有“2026/09/31”以及五轮描述后称“三轮”的笔误。10/9两个截止点写得明确，但阶段细节应在投入前向组委会核实。
- BDCI总赛首页顶栏日期与正文/单题不一致；采用单题详细赛程。
- 海信天池比赛与琶洲火山杯仅找到聚合线索或不完整页面，未完成报名、公布结果和规模三项验证，不纳入主推荐。
- 讯飞页面全站标题可能为2026，但具体赛题已完赛；不能凭标题归为当前开放赛题。

## 与当前学习项目的关系

建议以职场长程Agent赛为国内奖项候选，保留独立的VeriAgent后训练学习主线。相似的“职场”名称不代表两个环境相同，也不代表现有数据可以直接用于比赛。后训练岗位证据需实际参数更新、固定评测、训练前后比较与成本记录；Skills/Prompt优化成绩本身不建立SFT/DPO/RL能力。

PostTrain的环境/verifier/泛化机制与现有学习方向贴近，但组织状态与执行规则存在缺口，不能因题目贴近就宣称其含金量或人数已经达标。主办方训练也不等于选手亲自实现训练。

## 官方来源

- [CCF BDCI单题1165：职场Agent](https://www.xir.cn/competition/1165) — 用浏览器读取动态正文，含1329人数、立即报名、详细赛程及奖励。
- [CCF BDCI单题1167：科研论文Agent](https://www.xir.cn/competition/1167) — 浏览器读取，1311人数、立即报名、10/9截止。
- [CCF BDCI赛题列表](https://www.xir.cn/competition/races/BDCI2026/competition) — 动态页面，人数快照；不以列表结束时间代替报名期限。
- [金融Agent](https://www.xir.cn/competition/1166)；[百度DuMate](https://www.xir.cn/competition/1168) — 浏览器读取，均报名截止。
- [CareerSim官方仓库](https://github.com/openJiuwen-ai/CareerSim-BDCI26) — 官方页面链接与环境介绍；未检查比赛评测案例。
- [AWS赛事概览](https://agentsforhumans.devpost.com/)；[AWS赛事日程](https://agentsforhumans.devpost.com/details/dates)。
- [ITSAC官方通知](https://www.its-china.org.cn/ds/26087937c4.html)。
- [NeurIPS正式赛事名单](https://blog.neurips.cc/2026/07/28/neurips-2026-competitions-announced/)。
- [Agenthon官方规则](https://www.agenthon.net/rules/)；[官网](https://www.agenthon.net/)。
- [Steerability官方规则](https://steerability.github.io/competition/)。
- [PostTrain官网](https://posttrain.com/)；[官方仓库](https://github.com/benchflow-ai/posttrainarena)；[规范](https://posttrain.com/docs/spec)。
- [ARC Prize官方赛程](https://arcprize.org/competitions/2026)。
- [腾讯开悟官方赛程](https://tencentarena.com/aiarena/en/match/open-competition-2026)。
- [CCKS2026天池官方页](https://tianchi.aliyun.com/competition/entrance/532479)。

本次仅公开资料检索，不报名、不发信、不提交作品、不运行GPU或训练、不访问Workplace/BFCL最终池。没有新experiment_id或能力指标。实际费用未新增付费GPU/API项目。
