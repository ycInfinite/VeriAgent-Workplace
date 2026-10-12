# 2026-10-12 S100 / MIX100 实验结果

两组训练与开发集评估已经完成，adapter 和原始轨迹已回收校验，官方关机命令已执行，SSH 不可用。当前停在本阶段结果审核，不自动进入 DPO/RL 或继续采集。

**核心发现：扩到100条未显示优于原50条；加入20条合格不修改示范后官方成功率上升，但可靠的不操作判断尚未证明。** MIX100空reference官方8/8中仍有日期和求和错误；相同语义口径下，两组都是4/8有依据地完成不修改、2/8整条干净。

## 执行与控制

固定GitHub commit `64d6610b4412a556609f51294725c3c3bb921dc9` 部署71文件，完整manifest核对86文件，9个模型/Tokenizer哈希通过。两个实际HF预检分别核验310个样本模板、input_ids、labels及CUDA/BF16。未新采集teacher。

Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`；各自从Base新建LoRA，r16/alpha32/dropout0、7类投影、AdamW lr5e-5、seed42、batch1、310updates、1epoch；context8192、不截断。Torch2.8.0+cu128、Transformers4.56.2、PEFT0.17.1、Accelerate1.10.1。同一PRO6000 Blackwell96GB、driver595.58.03。

| 八字段 | 冻结定义 |
|---|---|
| Research Question | 近似同token预算下，100条覆盖是否优于50条重复学习；替换20条不修改示范能否改善行为？ |
| Hypothesis | 更多任务可能改善覆盖；不修改示范可能减少错误修改，同时检查该做却不做。 |
| Independent Variable | S100=100×1对历史S1=50×2；MIX100=80条S100+20条已审no-op。 |
| Controlled Variables | Base、LoRA、学习率、310步、context、B1、dev24×seeds42/43；S100/MIX同机。 |
| Metrics | 官方分层成功、语义复核、调用有效率、steps、tokens、latency、显存、GPUh。 |
| Evidence Gate | 数据/代码/权重身份、实际Tokenizer、CE、梯度、更新、保存重载、48有效rollouts/组。 |
| Cost Bound | 用户单卡；4h资源保护；每组训练60min/评估30min；时价未知，沿用本阶段预算豁免。 |
| Failure Branch | 正式运行失败保留并停止，不自动扩数据/context/seed；本轮无正式模型运行失败。 |

原始八字段见 `experiments/SFT-EXTENSION-RESUME-20261012-001/config.json`。原S100不变；MIX五域各20题。替换也改变具体任务覆盖，不能仅归因于抽象“不操作比例”。S100对历史S1同时改变多样性和重复次数，且新主机驱动不同于历史580.142，存在额外混杂。

## 成绩与配对统计

| 条件 | 官方成功/有效轨迹 | 非空reference | 空reference |
|---|---:|---:|---:|
| 历史BASE_B1 | 15/48 | 9/40 | 6/8 |
| 历史S1 | 35/48 | 30/40 | 5/8 |
| 历史S2 | 33/48 | 31/40 | 2/8 |
| S100 | 32/48（66.67%） | 27/40（67.5%） | 5/8（62.5%） |
| MIX100 | 40/48（83.33%） | 32/40（80%） | 8/8（100%） |

历史三组未重跑。本轮各48 valid、0 infrastructure-invalid，在线执行与离线replay一致。48是24个任务×2seed，不是48个独立任务。以任务为簇、两个seed一同抽样，10,000次配对bootstrap：

| 对比 | 全体差值/95%区间（pp） | 非空差值/区间（pp） | 空差值/区间（pp） |
|---|---|---|---|
| S100−S1 | −6.25 [−14.58,+2.08] | −7.5 [−17.5,+2.5] | 0 [0,0] |
| MIX100−S100 | +16.67 [0,+33.33] | +12.5 [−5,+27.5] | +37.5 [0,+75] |

改善区间均包含0。空任务仅4个簇；S100/S1观测差值相同产生[0,0]，不是总体等价证明。MIX非空8条失败→成功、3条成功→失败；净+5不证明无动作能力损害。单训练seed、重复使用的dev、无独立确认集，不宣布显著优越或泛化。

## 官方状态成功不等于语义正确

空reference表示参考执行不改变目标状态，不表示可以不查证据。官方reward原样保留，诊断另存。

| 事后审核指标（各8轨迹） | S100 | MIX100 |
|---|---:|---:|
| 官方成功 | 5 | 8 |
| 完成回应且关键不修改判断有正确证据 | 4 | 4 |
| 上述通过且整条无观察到的错误/冗余 | 2 | 2 |

Codex新鲜审核，无独立人工复核。标准在MIX评估前已记录；仍是事后诊断，不替换预登记指标。覆盖16条空任务生成决策与相关观察；S100某条巨大无关Backlog表不宣称逐行完整语义复核。开发轨迹全部不可训练。

- task709：MIX两个seed准确查询指定未来会议，返回空，真实说明无需删除。
- task122：MIX把周二误作2023-11-27（周一），正确为11-28。状态正确但前提错误；S100 seed43曾正确比较11-28与11-30。
- task385：MIX先查再决定不画，S100曾直接画图；但MIX把六周写成11月1–30日。seed42声称28/101，观察实际总和69/182；seed43以日胜场代替总量，声称10/20，实际2/26、2天持平。
- task12：MIX查到Leila无In Progress任务，但状态统计仍错。seed43完成了回应；S100 seed43曾触发context cap而官方reward仍为1。

## 非空失败与指标边界

MIX8条官方失败的决定性证据全部复核：task1两seed误把最后一页当最晚事件；task363两seed把四周缩成五天；task684 seed42新增客户代替重新分配、捏造Akira联系方式；task414 seed43误读观察并重复不支持的page参数，生成未完成；task952两seed有日期/条件范围错误。952 seed42修改两条，而官方还要求当天到期的第三条，保留“逾期边界”解释差异，不能只归因轮数上限。

正向例子task918 seed43：S100无负责人筛选、生成未完成；MIX目录查Carlos→按负责人查In Progress→更新观察到的00000086→如实完成。其他官方成功也可能解释错误，不把40条都标成高质量。

| 指标/分母 | S100 | MIX100 |
|---|---:|---:|
| Executable调用/所有尝试 | 188/188 | 162/167 |
| schema错误/所有尝试 | 0/188 | 5/167 |
| 未知工具名/所有尝试 | 0/188 | 0/167 |
| 平均tool steps/48轨迹 | 3.917 | 3.479 |
| input/output tokens | 757228 / 18190 | 804168 / 14175 |
| 平均轨迹秒 | 14.792 | 12.098 |

Executable只是schema/执行门槛，合法参数可能业务错误（如人名填email）、工具选错、日期选错；未知工具名率不是完整Wrong Tool Rate。自动identifier候选2/1、重复调用候选5/4、三次循环候选0/0、premature候选12/6仅为候选数。全96条Wrong Tool/Argument/Grounding/Redundancy/Premature语义率未完整标注。二元成功不按partial计分，部分修改保留events；模型触发context/round/generation cap计能力样本而非infra-invalid，空状态奖励例外如实记录。

## 训练与成本实测

| 项目 | S100 | MIX100 |
|---|---:|---:|
| updates/tasks | 310/100 | 310/100 |
| processed tokens | 1430459 | 1450298 |
| supervised tokens | 28307 | 28695 |
| 平均step秒 | 1.4082 | 1.4321 |
| train含保存重载秒 | 474.931 | 484.854 |
| eval秒 | 733.446 | 605.742 |
| allocated峰值GiB | 32.136 | 33.381 |
| reserved峰值GiB | 88.209 | 90.998 |
| nvidia-smi采样used峰值GiB | 88.896 | 91.685 |
| train利用率采样均值 | 94.19% | 88.95% |
| eval利用率采样均值 | 59.13% | 57.82% |

各43,646,976可训练参数、504个LoRA tensor变化，冻结参数抽样不变；首步手工shifted CE差0、每步梯度有限且非零；保存重载固定读出logit差0，greedy IDs一致。抽样不等于全量Base diff，固定读出不是Agent成绩。

脚本合计 **0.638603822 GPUh（38.316分钟）**；容器启动估计至关机请求 **1.015973377小时**，项目首次观察至请求0.949223273小时。含部署/传输失败/等待/回收，非平台账单。时价未知、金额null，不套历史价格。真实时价p元时，占用近似1.016p元，存储/计费边界另计。

推理GPUh/官方成功：S100=0.006366716，MIX=0.004206543，乘真实时价；不含训练/部署/存储，分母不是语义合格数。当前仅验证96GB，reserved/设备used超过80GB，不能凭allocated33GB断言原配置在A80080GB可跑。DPO/GRPO耗时未测。

## 故障、文件与生命周期

模型run无infra-invalid。部署两次GitHub临时raw链接404后第三次成功；隐藏SSH输入自动审批超时后允许的单次重试成功；base Python缺tokenizers后切正确venv。均永久记录，计占用、不计能力样本，不是隐去失败后重跑模型。

四个run依次：`SFT-S100-20261010-001`、`SFT-EVAL-S100-20261010-001`、`SFT-MIX100-20261010-001`、`SFT-EVAL-MIX100-20261010-001`，各在experiments同名目录。ID保留Oct10预登记日期，identity实际时间为Oct12。config/identity/steps/gpu_samples/result/reload_check/adapter_manifest/trajectories保留。

原始archive和逐成员校验、host preflight、shutdown收据在 `evidence/sft-extension-20261012/`；统计及语义标注在 `reports/sft-extensions-20261012/`。两个adapter在忽略目录 `checkpoints/<train_run>/adapter/`，均已SHA对齐远端，不进Git。本轮只新增分析脚本 `scripts/summarize_sft_extensions.py`，不改冻结执行代码/数据；更新项目状态/决策/假设/预算/taxonomy/registry和学习交接。

官方 `/usr/bin/shutdown` 已执行，新4h保护取消，旧监控保持暂停，旧SSH断开、新探测无banner。平台控制台/账单关机状态未独立确认。

## 路线结论

训练完整性通过；S100规模/多样性收益未获支持。MIX官方状态指标有改善信号，可靠不操作推理改善未获本轮语义诊断支持；不宣称证明无收益或最优混合比例。

下一路线建议：用已有training轨迹准备同题成功/失败DPO pairs，针对条件判断、错误恢复、目标选择审核，再登记单卡cost probe。历史13对只是CPU候选；dev案例仅作分析，不能直接训练。需用户决定是否进入；本轮不自动执行。无需重跑旧S1/S2或盲目扩大SFT，sealed final/BFCL/composition仍未测。
