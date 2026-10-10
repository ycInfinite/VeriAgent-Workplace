# 100 条 SFT：本地准备完成，等待 GPU 空位

用户在2026-10-10明确选择先做100条SFT规模检查，随后告知GPU已无空位，要求提前完成其他准备。本轮只有本地CPU操作；未开机、租卡、采样或更新参数。DPO暂缓。

## “一百多条是否够”的准确回答

| 数据层级 | 实际数量 |
|---|---:|
| 已采集的不同training任务 | 743（原20+后续723） |
| 后续723中已完整审核 | 150 |
| 其中通过/暂缓 | 137/13 |
| 后续723中尚未审核 | 573 |
| S1/S2各自实际训练 | 50/50 |
| 两组重叠/合计不同任务 | 16/84 |
| 主批已通过但两组都未使用 | 53 |

原20题还有15条DeepSeek完整质量审核通过记录，但原记录明确未准入训练导出，不能直接混称“137+15条都已可训练”。新DPO候选检查与旧审批分别保留。

50条已经足以证明这轮参数更新能改善开发任务；**不足以证明数据规模饱和或泛化充分**。当前也没有learning curve可以判定“再加数据没用”或“必须几千条”。一条轨迹可有多个assistant训练轮，本轮每组50条形成155样本、两遍310步，监督目标约2.9万tokens。

优先解决可检验的问题：在相同预算下，多见不同任务，是否比重复看50条更好？暂不把573条未审轨迹全部加进来。

## 已冻结的 S100 方案

| 控制项 | 已完成S1 | 待执行S100 |
|---|---:|---:|
| 不同任务 | 50 | 100，包含原S1全部50条 |
| 每业务域任务 | 10 | 20 |
| epochs | 2 | 1 |
| assistant turn样本/epoch | 155 | 310 |
| optimizer updates | 310 | 310 |
| processed tokens总计 | 1,425,440 | 1,430,459（+0.3521%） |
| supervised tokens总计 | 28,546 | 28,307（−0.8372%） |
| 最大单样本长度 | 7,208 | 7,208 |

两组均从固定Qwen3-8B Base全新初始化LoRA；保持r16/alpha32、lr5e-5、seed42和其他优化器参数。S100不接着S1继续训练。新增50条从已通过的137条中按固定SHA排序目标和token约束一次求解，未读取模型分数；它是**匹配预算的选择，不是均匀随机抽样**。

这个对照同时改变不同任务数与重复次数，研究的是“固定预算的数据多样性/重复权衡”；不冒称只改变数据条数而保持其他训练维度全部不变，也不是增加GPU算力的scaling curve。

评估仍是同一dev24×seeds42/43，共48条，B1/non-thinking/8K/6轮/2048累计输出。固定最终checkpoint，不重跑原S1，不选择更好seed，不碰sealed validation/final/BFCL。主要指标为非空reference的S100−S1任务簇配对差值，同时报告空reference、tokens、latency和新错误。

## 已完成与仍需实机验证

`SFT-SCALE-PREP-20261010-002`：100个完整已审核任务重新导出，310个样本逐项重编码通过；13个CPU控制检查通过。训练优化循环、重载readout和评估rollout循环的AST与原执行版本一致，只新增arm/数据入口及元数据。7个新增部署文件已列入严格GitHub白名单。

`SFT-SCALE-PREP-20261010-001`曾因本地CRLF与远端LF的原始SHA不同停止，未进入模型执行。失败数据、配置和匹配原始SHA的脚本快照永久保留；002只允许CRLF规范化后仍精确匹配原远端SHA的源代码。**执行配置是`configs/sft_scale_plan_v2.json`，旧v1不在部署白名单。**

尚未测量：新100条在实际Transformers上的完整编码复核、GPU/包/权重复核、真实CE和梯度、显存、step time、adapter重载、Agent结果。本地通过不能替代这些门槛。

## GPU 可用后的固定执行顺序

使用既有PRO6000 96GB同一类GPU及缓存，通过GitHub明确commit部署并核对hash；不需要重下模型。执行文件以本次发布commit为准，不使用随时变化的main内容。

```bash
# 全部命令在项目根目录执行；预检只加载Tokenizer，不构造LLM
.venv/bin/python scripts/validate_sft_scale_host.py \
  --run-id SFT-SCALE-REMOTE-PREP-20261010-001

# 仅在预检通过后：单组310次更新，最多60分钟
.venv/bin/python scripts/run_sft_scale.py \
  --arm S100 --execute --run-id SFT-S100-20261010-001

# 仅在训练保存重载通过后：48条评测，最多30分钟
.venv/bin/python scripts/evaluate_sft_scale.py \
  --condition S100 --training-run SFT-S100-20261010-001 \
  --execute --run-id SFT-EVAL-S100-20261010-001
```

命令逐个核验后执行，不盲目串联、不重复使用已有run_id。完成后保全adapter/原始结果/哈希再关机；任何OOM、梯度、重载或infra-invalid停止并保存，不扩大context或自动重试。

实际训练循环不变，但代码commit不同；`compare_sft_scale_evaluations.py`逐项核对共享部署文件、控制参数以及只允许的runner差异，不能直接把不同commit忽略掉。正式结果出现后，本地命令为：

```text
.venv/Scripts/python.exe scripts/compare_sft_scale_evaluations.py --output reports/sft-scale100-20261010/comparison.json
```

基于刚才同卡实测，训练+评测估计0.3～0.4 GPU小时；这是工程估算，环境检查/部署/回收额外计时。当前单价未知，不沿用旧价；每次训练60分钟、评测30分钟硬上限保留。具体八字段预登记在`configs/sft_scale_plan_v2.json`。

## 同步完成的失败与DPO准备

新审阅覆盖S1的13条、S2的15条官方失败：S1主要为日期/条件/时间范围7条、Completed目标2条、状态过滤与放弃2条、due-today归因待定2条；S2为日期/条件6条、排序目标3条、虚构可选信息2条、范围越界4条。分母是28条失败，不是全144条轨迹或所有calls；成功轨迹中的错误还需要全量语义审核。

发现13个旧Base失败与DeepSeek成功的同training任务偏好对，上下文、工具、初始状态相同；完整assistant分支编码不超过5431tokens，chosen/rejected目标tokens分别3489/2071。失败轨迹已重新审核，教师审批hash与旧记录匹配。另5题教师暂缓、2题双方成功未准入。原training20成员检查通过，无dev/final进入pairs。

这些是**CPU候选，不是DPO已训练或已通过GPU数值验证**：负例来自SFT前Base，而非当前S1；teacher/base的风格和长度混杂。正式DPO若增加这些任务，需要同起点、相同chosen数据的继续SFT对照，才能区分新数据收益与偏好目标收益。轨迹打分必须仅累计assistant token log-prob，分支各自的工具观察只作context。

## 当前停点

本地准备已完成，GPU缺货。没有自动租其他实例、创建库存监控、重新采样或开始DPO。显卡有空位后继续已选S100路线即可，不需要重新审核或重新选100题。

证据：`experiments/POSTSFT-AUDIT-20261010-001/`、`experiments/SFT-SCALE-PREP-20261010-001/`（失败保留）、`experiments/SFT-SCALE-PREP-20261010-002/`（当前通过）。


数据覆盖补充：137条已审轨迹中空reference为0；S1/S2/S100也均为0。因而100条扩充未增加空reference任务覆盖。“这可能关联无需修改时过度行动”只是待检验的机制假设，不能由相关性作因果结论。保持当前S100冻结；未来若补合法no-op/约束拒绝样本，须单独审核和登记对照，不能悄悄改变本轮100条。证据：experiments/POSTSFT-AUDIT-20261010-001/noop_coverage.json。

口径注意：空reference与执行后无状态变化不是同一概念；137条中有1条教师执行没有状态变化。因此这里只确认“空reference子集未覆盖”，不声称所有合法no-op语义样本完全为零。state_change_coverage.json保留了该核验。
