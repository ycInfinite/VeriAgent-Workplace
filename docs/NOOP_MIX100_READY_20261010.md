# 空 reference 审核与混合100条对照：离线准备完成

83条已有training候选均已给出处置：**29条通过、54条暂缓**。29条原始完整轨迹通过provider响应一致性、真实工具观察、状态未改变、完整assistant target编码和8K限制检查，并单独导出。未重采样、未修正文案、未挑正确片段监督；原始reward和轨迹不改。

原S100配置、100条清单和编码数据的SHA256均保持不变。另建MIX100：**80条原S100 + 20条新审核通过的“不修改”轨迹**。目前两组都还没执行，等待GPU资源；本轮GPU/API/参数更新均为0。

## 审核依据和范围

来源是原`DEEPSEEK-SFTDATA-20260917-001`的723条中全部83条空reference任务，未查看sealed case。主数据集revision为`c86a908379e0a361a573c395e175d3c1aa128e6c`，学生Qwen3-8B revision为`b968826d9c46dd6066d109eabc6255188de91218`。83条在审阅前冻结身份、source SHA和S100哈希；研究问题、假设、变量、指标、门槛、成本和失败分支均登记在本次config。

审核者为Codex，未做独立人工裁决。**58条完成可见决策与观察的完整语义复核；25条在未完整结束/编码或调用错误门槛暂缓，不声称完成了这些条目的全部语义分析。** 已通过的29条全部完整复核。大量相同观察使用精确hash的无损去重显示，原始内容保留在源轨迹和rendered_observations.json；不是用摘要代替未看的观察。

准入要求：任务和检索条件正确，身份grounding有依据，分页或结果覆盖充分，数值和日期判断成立；确实无需修改时保持状态不变并如实解释。最终没有改状态、reward=1或工具全部可执行，都不足以单独批准。无依据的精确重复核验暂缓；能够增加实体/条件覆盖的不同查询允许，不要求工具调用数量绝对最少。

## 结果

| 业务域 | 原候选 | 通过 | MIX100采用的不修改任务 |
|---|---:|---:|---:|
| Analytics | 29 | 18 | 11 |
| Calendar | 10 | 1 | 1 |
| Email | 2 | 1 | 1 |
| CRM | 7 | 2 | 1 |
| Project management | 35 | 7 | 6 |
| 合计 | 83 | 29 | 20 |

83条中80条官方成功，但其中51条仍未达到整条监督质量门槛。暂缓不是把原官方成功改判失败；例如报告数字错误但状态保持不变，依然保留reward1。

| 主要暂缓原因 | 条数 |
|---|---:|
| policy调用不支持的参数等 | 15 |
| 任务数量汇总错误 | 11 |
| context/encoding/round终止，轨迹不完整 | 10 |
| 无新增证据的重复核验 | 7 |
| 数值求和错误 | 4 |
| 错误比较并执行了修改 | 3 |
| 生成未完整结束 | 1 |
| 无依据的比较/趋势表述 | 1 |
| 用期间均值替代当前值 | 1 |
| 错误的中间时间判断 | 1 |

代表性证据：

- 通过task17：完整读取9月12日至11月30日，最低恰好3，严格“小于3”不成立，准确解释并不画图。
- 通过task51：解析Anaya身份，完整查询得到最近7天内两次会议，条件不成立，不创建新会议。
- 通过task329：解析Nia/Carlos，完整Nia任务集与In Progress任务集不相交；6 Completed、4 In Review、12 Backlog计数正确，没有改其他状态。
- 通过task358：Yuki全部16条中，10条Backlog最早12月3日才到期；两条过去到期任务已Completed，因此不转交。没有due-today边界争议。
- 暂缓task44：结论不画图正确，最终声称51/54次，原观察实际求和48/51次。保留reward1，整条不用于SFT。
- 暂缓task94：确实没有In Progress，但声称Completed5/Backlog13，实际6/12。与通过的Nia轨迹分开处理。
- 暂缓task712：把三天累计35与周二单日19相比而画图，当前单日实际7，官方reward0。
- 暂缓task47：最终不修改的结论正确，但向不支持分页的PM工具传page=2；不把错误前缀偷偷mask掉。

## 混合100条的控制

| 项目 | 冻结S100 | 新MIX100 |
|---|---:|---:|
| 总任务数 | 100 | 100 |
| 空reference训练任务 | 0 | 20 |
| 每业务域任务 | 20 | 20 |
| epochs/更新次数 | 1/310 | 1/310 |
| processed tokens | 1,430,459 | 1,450,298（+1.3869%） |
| supervised tokens | 28,307 | 28,695（+1.3707%） |
| 最大序列 | 7,208 | 7,756 |
| context上限 | 8,192 | 8,192 |

选择策略在审核前登记：从原100和合格no-op中选100、各域20、整轮310、两类token均在±2%，在10～20条no-op范围内优先最大化数量并用固定SHA打破并列。一次CPU求解找到20条可行最优方案；未读取S100/MIX100模型成绩，也未修改S100来适配混合组。它不是均匀随机抽样。

固定原Base全新LoRA、r16/alpha32/lr5e-5/seed42，不接着S100继续训练。MIX100同时移除了20条行动任务，结论应解释为数据组成的取舍，不能声称只改变了一个no-op标签。20个任务ID中有共享实体和类似请求，尤其多个Nia任务；不等于20种独立业务机制，也不证明跨数据库泛化。

## 评测设计

仍用原dev24×seeds42/43、B1/non-thinking/8K/6轮/2048输出，固定最终checkpoint。主要观察空reference任务，但必须同时报告非空任务：

1. 官方任务成功，分空/非空，不用总分掩盖拒绝或越界。
2. 对空reference逐条判断是否有充分依据不修改。什么都不查但reward1不算已证明正确克制。
3. 对非空任务检查无必要拒绝/提前停止，防止学成一律不动。
4. 工具步数、错误参数、重复行为、tokens、latency、显存和GPU-hours。

开发集只有4个空reference任务、8条rollout，统计不确定性很大。使用任务成簇的配对比较，不把8条当8种独立任务。它是开发pilot，不是final/BFCL或组合泛化验证。不会拿这次dev轨迹生成训练数据。

## 工程准备和执行顺序

`MIX100-PREP-20261010-001`通过全量重新编码和16项CPU控制：无held/dev混入、完整assistant mask、100唯一任务、各域20、310样本一次遍历、原S100哈希不变、训练/重载/rollout循环AST一致。新增10个文件进入GitHub严格部署白名单。代码参数差异保存在runner_transformations.json和runner_delta.patch，不改原S100入口。

数据：`NOOP-REVIEW-20261010-001/noop_examples.jsonl.gz`导出全部29条；`mixed100_examples.jsonl.gz`导出混合100条。质量依据与训练元数据不会作为模型输入；模型只看到原任务、工具、历史消息和观察。

未来资源可用时，先按已定方案完成S100，再执行新MIX100；不重跑旧S1/S2。以下都是**尚未执行**的命令：

```bash
.venv/bin/python scripts/validate_sft_mixed_host.py --run-id SFT-MIX-REMOTE-PREP-20261010-001
.venv/bin/python scripts/run_sft_mixed.py --arm MIX100 --execute --run-id SFT-MIX100-20261010-001
.venv/bin/python scripts/evaluate_sft_mixed.py --condition MIX100 --training-run SFT-MIX100-20261010-001 --execute --run-id SFT-EVAL-MIX100-20261010-001
```

逐步核验通过再执行下一命令。实际HF模板、单卡/包/模型权重、CE/梯度、显存、保存重载和新Agent成绩都还未验证。混合组最长7756，不能用S100的7208样本显存直接作保证。工程估算每组训练+评估0.3～0.5scriptGPUh，硬上限训练60min/评估30min，价格未知，部署/回收等待另计；本轮实际GPU/API为0。

未来本地比较入口：`scripts/compare_mixed100_evaluations.py --output reports/mixed100-20261010/comparison.json`。它检查共享文件、真实训练/eval身份和允许的runner转换。先保全所有结果和adapter再关机，异常停止保留，不自动重采样或扩大context。

## 证据和当前停点

审核ID：`NOOP-REVIEW-20261010-001`；运行准备ID：`MIX100-PREP-20261010-001`。主配置：`configs/sft_mixed100_plan.json`。原S100仍用`configs/sft_scale_plan_v2.json`。

重点文件：manifest.json、judgments.json、quality_approvals.json、arithmetic_evidence.json、pm_count_evidence.json、policy_error_evidence.json、noop_corpus.json、mixed100_selection.json、result.json；以及MIX100准备目录下cpu_controls.json、deployment_plan.json、runner_transformations.json。

所有准备完成后等待GPU资源；没有开机/租卡/新API/参数更新/库存监控。DPO和RL保持暂缓。
