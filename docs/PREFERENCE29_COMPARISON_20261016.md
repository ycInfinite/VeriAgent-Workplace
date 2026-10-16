# 29对当前S1偏好数据：同chosen的SFT与DPO对照

执行commit：`033a53f`。用户确认继续后登记，所有旧实验与adapter保留。

【Research Question】

Does cumulative29 reward-gap DPO improve fixed development behavior beyond chosen-only SFT from originalS1?

【Hypothesis】

Expanded failures may help beyond chosen-only supervision;prior6pair/12pair did not establish stable DPO gains.

【Independent Variable】

Task-mean chosen CE versus whole-trajectory sum-logp DPO.

【Controlled Variables】

OriginalS1,29tasks/order,oneepoch29updates,lr5e-6,seed42,8192,samehost;DPOreference originalS1,beta.1.

【Metrics】

Primary paired nonempty DPO minus chosenSFT success;overall/empty, fresh semantic audit,tokens/VRAM/latency/GPUh;single exposed-dev experiment.

【Evidence Gate】

Preflight plus newly registered execution IDs;finite updates,frozen reference/save-reload,matched144valid devrollouts/fresh semantic audit.

【Cost Bound】

Engineering estimate0.7-1.2scriptGPUh plus preparation/retrieval,not measured matrix. Longest-pair SFTbackward5.156s/DPO15.723s/reference3.595s withoutoptimizer;rateunknown;KEEP_INSTANCE_ON. Eachscript1800s;pipeline9000s processbound;no poweroffguard.

【Failure Branch】

Stop on integrity/infrastructurefailure;no retries/tuning/extra seeds;preserve IDs.

## 实验结构

原始S1 → 同主机baseline48条；原始S1 → chosen-only SFT29步 → eval48条；原始S1 → DPO29步 → eval48条。两组各一轮，不延续旧六对adapter。DPO参考为原始S1且先缓存，不用禁用adapter后的Base冒充reference。

训练29题、179个assistant回合、五域。chosen目标9856tokens，rejected11609；4个同奖励语义pair不加入。相同chosen曝光/任务顺序/更新数不等于同总tokens/FLOPs；DPO的rejected、reference和重算额外开销单独报告。

dev24×seed42/43保持不变；这是多次使用的开发集，不能称sealed最终测试或组合泛化。主分析为20个非空taskcluster的DPO−SFT差，另报24任务整体与4个空reference任务。按task聚类bootstrap10000次，固定统计seed20260917。样本小，置信区间退化不证明总体等价。

## 预先固定的审核范围

新读全部24条空reference轨迹（3policy×4task×2seed），重新核对日期/条件/查询/修改与最终声明。审核DPO全部非空失败及非空成败发生变化的对照轨迹。只生成本轮标签，不照搬旧annotation；基础设施失败永久保留、有效policy失败留在分母。没有全面语义审核的其他call不报告完整wrong-tool/wrong-argument率。

## 执行前证据

14项本地CPU控制通过：29题一次/不混same-reward/数据与dev隔离/原S1与超参/旧评测不变/179回合/实际HF与最长梯度证据/旧runner仅登记差异/白名单/新ID/保持开机。旧零更新preflight已实测179HF/7Torch控制，通过task358的8073token反向。

当次GPU计算尚未启动时本文件创建。实际结果、无效run、证据、资源和路线结论在执行后补充。KEEP_INSTANCE_ON；脚本只限定自身进程，不关机。


解释限制：与历史6对实验相比，本次同时改变了pair数量、域覆盖、任务组成和更新次数，不能把分数差单独归因于“覆盖更广”。当前主因果对照只限同29题的chosen-SFT与DPO；相同chosen数据下DPO额外使用rejected信息且计算量更大。


## 最终结果与假设判断

五个正式run各执行一次，144/144有效、infra-invalid=0。两组各29次真实更新，504个LoRA张量改变，冻结参数抽样与原始S1文件不变。两组实际HF各179回合、7Torch控制通过；重载logits最大差0，生成ID一致。DPO首次margin0/lossln2，29步重算差最大0，reference缓存SHA保持不变。

| 条件 | 整体/48 | 非空reference/40 | 空reference/8 |
|---|---:|---:|---:|
| 原始S1 | 35 | 30 | 5 |
| chosen-only SFT29 | 34 | 29 | 5 |
| DPO29 | 33 | 29 | 4 |

主指标DPO−SFT：非空0pp，按20个taskcluster bootstrap95%区间[−7.5,+7.5]pp；整体−2.083pp，24clusters区间[−8.333,+4.167]pp；空reference−12.5pp，4clusters区间[−37.5,0]pp。

**本轮不支持“DPO带来额外Agent收益”的假设。** 也不能据此证明DPO总体无效或两者等价；只有一个训练seed、小且反复使用的dev。SFT−S1整体−2.083pp，DPO−S1整体−4.167pp，均未显示新增优势。相同非空总分不是相同逐题结果。

## 新读轨迹的得失

| task/seed | S1 | SFT29 | DPO29 | 行为 |
|---|---:|---:|---:|---|
| 18/42 | 1 | 0 | 1 | SFT把返回列表最后一行09:30当最晚事件；S1/DPO选对15:30。 |
| 1/43 | 1 | 1 | 0 | DPO翻到末页后把09:00事件当最晚；S1/SFT选择15:00。 |
| 122/42 | 1 | 1 | 0 | S1/SFT错误认定Nov27为周二但不画图；DPO改用Nov26并错误画图。三者推理均不干净。 |

其余二元成败在三组间一致，但行为可以不同：684/42的SFT/DPO都只转交第一页两位客户，漏掉第二页两位；DPO684/43未正确过滤负责人，还把其他人的客户转交。DPO952/42生成一串包含未来到期任务的操作，输出截断后严格gate不执行整个未完成turn。952/43依然保留“今日到期是否算overdue”的语义边界 caveat；不能将全部官方失败都贴成单一明确推理错误。

所有24条空reference已新读，另新读28条非空轨迹（包括DPO全部11条非空失败、成败变化对照及基线失败）。共52条不同轨迹完整可见语义审核，不声称144条全部语义审核。

| 空reference审核（每组8条） | S1 | SFT29 | DPO29 |
|---|---:|---:|---:|
| 官方成功 | 5 | 5 | 4 |
| 有证据且完整结束的不修改 | 4 | 4 | 3 |
| 整条干净 | 2 | 2 | 0 |

DPO12/43的空查询循环触及六轮上限，状态保持不变所以officialreward1；“有证据且完整结束”指标排除这条，不能把停止条件失控当正确克制。whole-clean是单审核者判定，额外排除虚假计数、不必要重复或无关查询；DPO709两seed分别出现无关扩搜/超出已知总页数的查询。不操作结论正确也不等于整条轨迹干净。

## 机械指标、分母与边界

| 指标 | S1 | SFT29 | DPO29 |
|---|---:|---:|---:|
| 可执行gate通过 /（解析calls + 解析失败responses） | 159/161 | 162/164 | 177/180 |
| 未知工具名 / 解析calls | 0/161 | 0/164 | 0/179 |
| schema错误calls / 解析calls | 2/161 | 2/164 | 2/179 |
| ID未出现于context候选 / 含IDcalls | 0/76 | 0/77 | 0/85 |
| 相同state重复call候选 / 解析calls | 3/161 | 2/164 | 4/179 |
| 三次连续重复loop轨迹 / 有效轨迹 | 0/48 | 0/48 | 1/48 |
| final且reward0候选 / 有效轨迹 | 13/48 | 12/48 | 14/48 |
| 平均工具步数 / 有效轨迹 | 3.354 | 3.417 | 3.729 |
| 输入tokens（整组求和） | 775142 | 780354 | 815779 |
| 输出tokens（整组求和） | 15603 | 17099 | 18616 |
| 平均trajectory秒 / 有效轨迹 | 12.915 | 13.883 | 14.905 |

第一个分母混合了call与无法解析的模型response，不能叫纯call-level率；DPO为179解析calls+1解析失败response。unknown-tool不等于语义wrong-tool；schema错误不等于全部wrong-argument；字符串ID-grounding候选为0仍会发生选错已知ID。本轮不声称完整wrong-tool/wrong-argument/冗余/提前停止语义率，标签与机械候选分开保留。

Task success为每组48个有效task-seed的二元officialreward均值；partial完成仍计0，仅作诊断。有效预算截断保留在分母，infra-invalid永久保留且剔除能力指标、计入成本，本轮没有此类模型run。sealed final、官方validation、BFCL及strict tool-combination泛化仍未测。

## 成本与资源

| 阶段 | wall秒 | GPU小时 | 平均实际update秒 | 设备峰值GiB |
|---|---:|---:|---:|---:|
| S1评测 | 645.081 | 0.179189 | — | 21.310 |
| SFT29训练含重载 | 155.809 | 0.043280 | 4.003 | 37.583 |
| SFT29评测 | 692.611 | 0.192392 | — | 21.079 |
| DPO29训练含reference/重载 | 440.585 | 0.122385 | 11.239 | 37.563 |
| DPO29评测 | 740.753 | 0.205765 | — | 22.868 |

合计0.74301086scriptGPUh，DPOreference打分74.769秒单列；SFT/DPO训练allocated峰值21.539/23.003GiB，reserved36.896/36.877GiB。利用率采样均值分别75.73%/91.60%，评测约59–60%；不是恒定GPU利用率或独立性能benchmark。

每次官方成功的评测GPUh为S1 .00511969、SFT .00565858、DPO .00623529，仅包含该次评测，不摊销历史训练；RMB单价未知，费用为null。当前host/driver同一，少量已完成结果文件回收与后续计算重叠；大型adapter下载全部在GPU流程结束后，不影响本矩阵评测时间。

流程启动至原始归档回执0.753599小时；容器启动估计至该回执累计1.990320小时，包含以前的91题采集、preflight及准备等待。两者与script时间重叠，不能相加。实例按用户要求保持开机，传输及后续等待继续占用，最终回收时间另见资源回执。

## 无效操作和证据

正式训练/评测无失败重跑。本轮回收时普通SFTP两份大adapter下载速度约0.3MB/s，主动中断后保留未完成文件、字节数和SHA；这是传输故障记录，不计为模型infra-invalid。改用最多4个只读SSH分段，整文件SHA通过后才接受新adapter副本，不改变远端权重。

已核验62个原始归档成员，`evidence/preference29-20261016/raw_manifest.json`与`raw.tar.gz`为原始证据。两个adapter六文件完整性结果在`adapter_download.json`；比较统计`reports/preference29-20261016/comparison.json`，新语义标签`empty_semantic_reviews.json`、`nonempty_semantic_reviews.json`、`semantic_summary.json`，资源在`resources.json`。旧S1文件SHA未变，原始probe/6对/12对adapter不覆盖。

## 路线分叉

建议在这里收敛本轮偏好训练结论，不因分数不升自动加epochs、seed、teacher或RL。项目已证明真实SFT/DPO参数更新、严谨数据审核与负结果分析；尚缺独立泛化证据。下一步优先准备未污染的独立验证/组合泛化协议，先核验split可用性、冻结候选checkpoint及指标，再由用户决定执行。若继续研究DPO，则必须明确新的可证伪问题，例如条件判断与分页覆盖的数据缺口；不能直接用dev失败题生成训练答案。


最终保存回执：两个adapter六文件均已本地完整SHA256核验，全部SSH连接关闭，未发出任何关机命令。矩阵启动至备份完成0.989213小时；容器启动估计至备份累计2.225934小时。详情`evidence/preference29-20261016/completion.json`。新实验之外仅修改独立runner/白名单、报告/学习文件和append-only登记；旧训练入口与模型不变。
