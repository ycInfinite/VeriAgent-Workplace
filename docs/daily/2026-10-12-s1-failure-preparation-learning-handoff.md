# 2026-10-12：当前S1失败采集准备交接（粗颗粒）

**当前状态：准备完成，等GPU，尚未采集。** D62和D47都没有空闲GPU，你选择先保留准备。没有新租、没有库存监控、没有成功开机；本轮GPU/API/参数更新/新rollout均0。

## 今天的问题与开始前状态

上一轮已经真实比较S1、追加chosen-only SFT和DPO，非空任务都30/40，DPO没有额外收益。旧偏好负例来自pre-SFT Base。现在想问：**换成当前S1真实还会犯的错误，能否得到更有信息的偏好对？** 今天只完成这个问题的采集准备，尚无结果。

## 冻结了什么

25道training任务，五个业务域各4道需操作题+1道空reference题；每题只跑seed42一次。固定原S1 adapter、B1、8192 context、最多6轮、累计输出最多2048。既有已审teacher作为chosen来源，不新增teacher API。

25题都避开当前S1训练过的50题；并不声称全项目从未见过，其他独立S100/MIX权重可能用过部分题。按固定SHA256排序选取，不根据S1成绩换题或补采。候选层本身是teacher已审核子集，不代表全training池随机分布。

题目ID已冻结：1082、795、1173、1076、1000、473、349、1194、120、51、79、545、91、979、443、45、1130、746、1179、165、1146、839、902、1114、702。

## 实际完成与原始结果

- 读取原task与共享tool schema bank，重建工具输入并核对与教师相同。
- 检查training池、S1训练集隔离、原prompt/tools/state身份。
- 25个初始上下文全能放进8K，最大4213 tokens。
- 11项CPU控制通过，collector默认只检查数据，不加载模型。
- 4个新增执行文件白名单已准备、已推GitHub；没有远端部署。
- 第一份CPU准备因未展开tool_schema_ref失败，保留001；002正确重建schema后通过，不改选题。

唯一计划变化是新增当前S1 rollout；没有改policy参数。原始新成功/失败轨迹：**暂无**。合格新pair数量：**未测**，不能说“已收获0对”或拿旧Base失败替代。

## 你只需理解三件事

1. **旧失败可能已经太容易。** S1学会某类错误后，继续给它旧Base的同类反例未必帮助当前剩余问题。这是待检验假设，不是已证实解释。
2. **采集与审核分开。** reward0可能来自日期边界歧义、截断或基础设施；reward1也可能有错误解释。不能按reward自动生成全部偏好标签。
3. **两条轨迹必须可比。** 同题、同初始状态/工具/prompt；chosen真实合格，rejected有明确相对缺陷；每个分支保留自己的观察，不拼接造故事。

工具观察进入context，但默认labels=-100；后续完整assistant轮次才是训练目标。这个阶段还没有DPO更新。

## 四处代码地图

| 文件→函数 | 输入 | 输出/作用 |
|---|---|---|
| scripts/prepare_s1_failure_collection.py→main | 既有teacher审批、pool元数据、S1训练清单 | 固定25题/teacher来源/身份哈希/初始token检查 |
| scripts/collect_s1_failures.py→load_eval | 冻结配置和25题输入 | 核验相同prompt/tools、training-only任务 |
| scripts/collect_s1_failures.py→main | 未来可用GPU、原S1、25题 | 真实tool trajectories、状态/reward/tokens/latency；不更新参数 |
| scripts/check_s1_failure_preparation.py→main | 冻结输入与collector源码 | 11项隔离/边界/循环等价/白名单检查 |

审核规则在configs/s1_failure_pair_review_protocol.json。即使发现同reward但明显更差的轨迹，也要记录明确语义理由；不能悄悄塞进旧的“rejected必须reward0”配置。

## 路线判断、未支持推测和预算

已支持：25题输入与S1/teacher来源关系可验证，CPU准备可用。

未支持：S1会失败多少题、哪些failure占主导、能得到多少有信息pair、DPO会不会因此改善。需要真实采集后回答。

未来25rollouts估计0.12–0.25脚本GPU小时，基于历史同模型推理估算，并非实测。若仍6.98元/h，脚本约0.84–1.75元，部署回收另计；上机前再核价。用户选择等已有GPU，不自动新租或加监控。

## 五个考核问题（不给答案）

1. 为什么“真实的旧Base错误”未必是当前S1最有价值的负例？
2. 为什么25题要先固定，不能跑完挑有失败的题替换成功题？
3. 为什么空reference不等于零工具调用？
4. 什么情况下reward0不能直接当作rejected？reward1能否作为较差分支？
5. 当前已经能声称哪些准备事实，哪些实验结论还不能说？

未回答，不标记通过；教学不作为实验执行门槛。

## 下一分叉与证据入口

你选择等已有实例有卡。恢复时沿用原25题、原S1、一次seed42；采完保存、关机，再本地审核；不自动进入DPO训练。若无足够合格pair，如实报告产率，不自动补题。

执行准备commit：8ca196e1bdfbbfade4947916838065a4446a4a6e。后续文档提交不表示采集执行。

- configs/s1_failure_acquisition.json：八字段、模型/data revision、预算及4文件白名单。
- experiments/S1-FAILURE-PREP-20261012-001/invalid_run.json：初始CPU故障。
- experiments/S1-FAILURE-PREP-20261012-002/：config/final_config、identity、selection、tasks/teacher_records、result和cpu_controls。
- evidence/s1-failure-preparation-20261012/resource_status.json：两台freeGPU0、用户等待决定。
- configs/s1_failure_pair_review_protocol.json：后续逐对审核字段和处置门槛。
- docs/S1_FAILURE_COLLECTION_20261012.md：完整准备报告。

未来run ID S1-FAILURE-ACQUIRE-20261012-001尚未使用，没有新模型日志。
