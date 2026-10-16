# 当前 S1 小规模失败采集与偏好对审核

2026-10-16 完成。当前阶段止于采集和数据审核，未做 DPO 更新。

## 实际执行与结果

固定25个 training 任务、seed42，各一次真实 rollout；20个非空 reference、5个空 reference。使用原 S1 adapter、原 B1、non-thinking、8192 context、最多6轮、每次最多768输出、单轨迹累计2048输出。没有换题、重采、调用新教师或打开 sealed test。

执行 commit：`4efbf07e3410cad64b20989498247405e2026a0d`。保留原预登记 ID `S1-FAILURE-ACQUIRE-20261012-001`，实际执行日期是10月16日。用户提供单卡 PRO6000 96GB 新克隆，driver595.71.05；9个模型/tokenizer文件和原S1三文件哈希通过，实际HF初始25个context全部通过。所有模型参数requires_grad=False，抽样参数前后一致。

| 指标 | 原始结果与分母 |
|---|---:|
| 有效 / infra-invalid trajectories | 25 / 0 |
| 官方 Task Success | 18/25，72% |
| 非空 reference成功 | 15/20，75% |
| 空 reference成功 | 3/5，60% |
| Executable Tool Call | 87/90，96.67% |
| 未知工具名 / schema-invalid call | 0/90 / 3/90 |
| 解析错误 | 0 |
| identifier自动未grounded候选 | 0/37含identifier调用；不是所有语义选错ID率 |
| 相同状态重复调用候选 | 1次 |
| 自动retry-loop命中 | 0/25；不代表没有错误恢复循环 |
| 正常assistant final / round limit | 24 / 1 |
| 平均工具步数 / 模型轮数总计 | 3.6 / 89 |
| 累计输入 / 输出tokens | 408,835 / 8,634 |
| 平均轨迹耗时 | 12.307秒 |
| 脚本总耗时 / GPU-hours | 329.248秒 / 0.09145779 |

这是预选 training 子集的采集统计，不能与旧dev24成绩直接比较，更不是泛化分数。官方reward保持二元，不把partial progress计作部分成功。基础设施无效记录应从模型成绩分母剔除并单独保留；此次为0。

自动 `premature_termination_candidates=6` 只是“失败且正常结束”的筛选规则。人工复核其中5题已经执行了错误动作，只有1194明确未执行所需改名；不能把6/25直接写成提前终止率。

## 逐对审核

全部25组、50条完整可见轨迹由Codex重新阅读，工具观察、state before/after、state diff、奖励也全部CPU重放一致。没有独立人工复核。只将明确优劣且完整终止的轨迹导出；原始错误前缀、各自观察均保留。

| Task | 决定 | 当前S1问题 / 教师行为 |
|---|---|---|
| 1076 | reward-gap准入 | 已知道direct最多，仍额外画另外3种来源；教师只画最热门来源 |
| 1000 | reward-gap准入 | 擅自把阈值2变成2小时，并把秒说成分钟；教师正确判断条件不满足、不画图 |
| 473 | reward-gap准入 | 把11月6日当未来并删除，遗漏已观察到的12月11日；教师选择正确未来会议 |
| 349 | reward-gap准入 | 已列出12月5/6/18/19，仍把18日当next；教师选择5日 |
| 1194 | reward-gap准入 | 把用户要求的新名称当现有会议名搜索；教师找到当日最晚会议后改名 |
| 51 | reward-gap准入 | 已查到最近见过面，仍创建新会议，且16点与15–17点会议重叠；教师正确不创建 |
| 702 | same-reward单独准入 | 都不修改，但S1编错总数与状态分布；教师正确报告22条、6/12/4/0 |
| 1179 | 暂缓：截断 | 错上一周日期，连续编造3个不支持的筛选参数，6轮耗尽；有效模型失败，非infra |
| 746 | 暂缓：日期边界 | 两者都删8封，包含11月23日11:50；在11月30日23:59锚点下，日期包含制和滚动7天解释不同，不能把教师直接作为明确优者 |
| 其余16题 | 不建pair | 没有足够强的偏好证据；保留839总数20说成19的附带错误，不为单个无关计数强凑pair |

六对reward-gap占全部固定任务6/25=24%，占7个官方失败6/7；加上702是7/25=28%。这两个产率不可混为一种奖励差。六对只覆盖analytics和calendar，并非五域均衡；702增加PM回答准确性信号。

| 导出 | pairs | chosen targets | rejected targets |
|---|---:|---:|---:|
| reward_gap_pairs.jsonl.gz | 6 | 1,774 | 2,858 |
| same_reward_pairs.jsonl.gz | 1 | 433 | 357 |
| 总计 | 7 | 2,207 | 3,215 |

总共48个完整assistant轮次（23 chosen/25 rejected），canonical processed tokens229,730，最长7,194。完整assistant工具调用和回答参与目标；system/user/tool observation全部labels=-100。12项CPU控制包括篡改context、篡改observation、缺EOS、超长不截断的拒绝测试。新数据的实际HF训练预检、DPO reference score、更新、重载和评测尚未执行。

现有冻结12对的loader要求rejected reward=0。702只能单独存放；未来若采用必须明确支持其语义偏好类型，不能改旧文件悄悄混入。此次7对中5对chosen更短、2对更长；偏好依据是正确性，不是长度。跨provider风格和长度混杂仍然存在。

## 假设与数据量

支持的结论：当前S1在已审教师覆盖、未被原S1训练的25题中仍有可归因失败，能够产生6个新的成功/失败偏好对。训练过S1并没有消除时间排序、条件执行、操作范围和指令角色理解问题。

尚未支持：这些负例比旧Base负例训练效果更好；DPO会改善任务成功；失败可跨seed重复；当前模型已饱和；更多教师数据无用。本轮每题只有一个seed，25题来自已审教师分层而非全training均匀样本。

**7对仍不足以宣称稳定DPO收益。** 现有结果说明“可用数据”取决于新失败、教师质量、完整性、无歧义四个条件，不是收集总数。下阶段可先用6个reward-gap做原S1起点的chosen-only SFT对照DPO，作为有界机制检查；702单独保留。若选择扩大采集，应先冻结新的training cohort，不能按dev失败直接造训练集或为了凑pair反复重采。本轮不执行这些后续实验。

## 资源、故障与机器状态

torch allocated峰值17.363GiB、reserved19.482GiB，设备采样峰值20.161GiB，306个样本平均GPU利用率66.16%（含加载/检查阶段）。实际只验证当前96GB推理范围，不推定所有训练配置的80GB可用性。

从容器启动估计到原始证据保存时约0.46775小时，首次项目观察到保存约0.30999小时；脚本执行约0.09146小时，三者不可相加。时价未知，人民币费用保持null；若真实时价p元/小时，保存时累计容器占用估计为0.46775p元，存储另计，且此后持续计费。这不是账单。

按用户明确要求保留GPU资源：**未关机、未切无卡模式、未设置关机保护**。保存时collector PID已不存在，nvidia-smi显示无计算进程、显存0MiB；SSH已关闭。机器继续开机，后续闲置占用不包括在329秒里。

首次会话中断发生在GitHub部署完成但模型尚未启动时，SSH socket reset10054已经记录；恢复后检查无重复run再启动一次。正式25条0infra-invalid。历史CPU schema unpack失败仍保留，没有删除重算。

## 文件与证据

- 原始执行：`experiments/S1-FAILURE-ACQUIRE-20261012-001/`，包括config、identity、trajectories、result、GPU samples。
- 准入数据、全25题处置、50分支回放、12CPU控制：`experiments/S1-PAIR-REVIEW-20261016-001/`。
- 原始归档：`evidence/s1-failure-execution-20261016/raw.tar.gz`，15个成员全部SHA256一致；归档SHA256为`06f0c4702d8c10c928bd69f92877d9d91e7e2ee1cc9eadd61d88856669d04586`。
- 部署/主机/启动/保留开机收据：`evidence/s1-failure-execution-20261016/`。
- 新增离线代码：`scripts/show_s1_pair_review.py`、`review_current_s1_pairs.py`、`check_current_s1_pairs.py`、`verify_s1_collection_archive.py`。
- 原始采集和训练代码、模型、旧DPO12对及旧S1均未改动。

已更新长期状态、预算、假设和failure taxonomy；日报见 `docs/daily/2026-10-16-learning-handoff.md`。本阶段完成后停止新实验。
