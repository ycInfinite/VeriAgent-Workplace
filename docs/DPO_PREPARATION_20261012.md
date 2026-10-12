# DPO 数据审核与训练前准备（2026-10-12）

本地准备完成：原13对逐条审核，12对通过数据准入，1对暂缓；26条原轨迹重新执行官方工具并验证状态、观察和reward相同。已准备单卡8步DPO入口与后续chosen-only SFT对照草案。本轮GPU/API/模型加载/参数更新均0，未部署或开机。

## 研究范围与八字段

| 字段 | 本轮 |
|---|---|
| Research Question | 现有training偏好对能否支持完整、可追溯的轨迹级DPO完整性探针？ |
| Hypothesis | 同题、同初始状态、真实工具观察的成功/失败对可以提供偏好训练信号；不预设当前Agent收益。 |
| Independent Variable | 本轮只有审核/编码/训练准备；拟执行8步DPO。 |
| Controlled Variables | 原任务/messages/tools/state、Qwen3-8B revision、8K、整条assistant监督；不读取sealed测试内容。 |
| Metrics | 语义处置、重放一致、tokens/长度、mask、loss/梯度数学控制、reference身份、部署白名单。 |
| Evidence Gate | chosen全轨迹合理且成功，rejected为模型错误；两分支完整终止、无infra-invalid；完整保留观察。 |
| Cost Bound | 本轮仅本地CPU；后续单96GB卡8步，估计0.05–0.15 GPUh，30min脚本上限，估计非实测。 |
| Failure Branch | 故障永久保留；不改原轨迹、不截断、不自动采样/训练/扩大context。 |

登记：configs/dpo_preparation.json；具体未来探针：configs/dpo_probe_plan.json。用户本轮授权数据与训练前准备，不含GPU执行。

## 审核结果

来源chosen=DEEPSEEK-QUAL-20260917-001；rejected=SFT-ACQUIRE-20260916-001原始pre-SFT Qwen3-8B。原候选来自POSTSFT-AUDIT-20261010-001，旧文件不覆盖。

| task_id | 处置 | 核心相对质量证据 |
|---|---|---|
| 565 | 通过 | 执行请求的histogram，而非只给均值后反问是否画图 |
| 972 | 通过 | 两个distribution用histogram，rejected用line |
| 247 | 通过 | 目录查Lena、保持会议标题；rejected编造邮箱且改标题 |
| 859 | 通过 | 遍历两页定位最晚会议；rejected虚构12345678 |
| 123 | 通过 | 按日期与时间找最早会议；rejected把first meeting当名称反复查 |
| 770 | 通过 | 正确邮箱、仅请求字段；rejected把Lena直接存为邮箱 |
| 271 | 暂缓 | rejected越权删除其他owner，且round cap无最终回答；首probe排除截断分支 |
| 20 | 通过 | 正确负责人及Qualified/Proposal并集；rejected错用Qualified,Won字符串 |
| 177 | 通过 | 正确最新邮件、两个收件人都查目录；rejected编造邮箱 |
| 76 | 通过 | 观察到真实最新邮件ID并准确回复；rejected用占位ID |
| 965 | 通过 | 完整In Progress列表中定位Dmitri；rejected捏造邮箱并错误放弃 |
| 687 | 通过 | 查到Jinsoo两条任务并更新；rejected参数错误和虚构邮箱 |
| 8 | 通过 | Chenwei真实邮箱/任务ID；rejected查错邮箱后声称不用操作 |

由Codex重新阅读全部可见消息，无独立人工裁决。271属于有效模型失败，不是基础设施失败；只是为避免首轮学习“被轮数上限截断”的偏好而暂缓，不永久宣称其不能用于DPO。247关于constraints的表述仅按办公时间解释，不视作独立日程冲突检查。965查询范围较宽但结果完整、目标正确。analytics图路径是环境模拟返回，不证明生成了真实图片。

12对覆盖五域，与原S1/S2的训练task IDs均无交集；pool元数据全部training_candidate。完整pair包含task_id/uid、相同初始prompt/tools/state hash、两分支messages和逐轮编码、source run/hash、verifier、终止、tool steps、tokens、failure category、审核理由。观察与状态用原轨迹重放核对，未手工改造失败或拼接分支。

| 数据量 | chosen | rejected |
|---|---:|---:|
| 完整assistant轮次 | 38 | 37 |
| processed tokens | 174097 | 162614 |
| 直接监督target tokens | 3258 | 1885 |

总processed336711，最长单轮5431，小于8192，不截断。两分支轮次可不同，不能按第n轮机械配对。11/12对chosen更长，全部chosen来自同一teacher、rejected来自旧Base，存在长度/风格/来源混杂；不把长短当标签、不根据长度改reward。

没有新的正确no-op优于错误修改pair；也不是当前S1/MIX100重新采样的失败。12对适合验证机制，不足以支持泛化/显著收益，更不能承诺修复上一轮条件推理。若后续信号饱和，需要另行决定是否采当前policy training rollout，不能用dev失败直接训练。

## 目标函数与实现选择

原始DPO使用chosen/rejected相对reference的log-prob比构造偏好loss，不要求训练期间online rollout。[DPO论文v3](https://arxiv.org/abs/2305.18290v3)。本项目在真实环境历史上计算policy生成的assistant token概率：

```text
score_theta(branch) = sum_turns sum_assistant_tokens log pi_theta(token | branch自己的历史)
margin = (score_theta(chosen) - score_theta(rejected))
       - (score_ref(chosen)   - score_ref(rejected))
loss = -log sigmoid(beta * margin)
```

这是项目明确登记的trajectory policy-action DPO目标。user/system/tool观察保留作上下文、labels=-100；每轮完整assistant输出（含tool call/final）计分，token概率求和，不按长度平均，不只截取“正确片段”。环境转移由环境提供，不能让模型为生成工具观察承担loss；不直接把完整交互拼成普通纯文本completion计分。

采用已有Transformers+PEFT固定版本，新增小型目标函数与探针，不安装TRL或升级库。官方TRL支持预计算reference概率以减少模型驻留显存，但这不自动证明本项目多轮mask/实现正确。[TRL DPO官方文档](https://huggingface.co/docs/trl/dpo_trainer)。核验日期2026-10-12；该网页非固定版本安装依据，实际软件仍为既有Torch2.8.0+cu128/Transformers4.56.2/PEFT0.17.1/Accelerate1.10.1。

policy从原S1 adapter继续；reference=同Base+同S1 adapter的冻结初始策略，不能用disable_adapter误退回裸Base。选择S1沿用Oct10候选比较计划，不因本轮MIX分数最高就临时换anchor。先在参数未更新时计算reference并保存，cache key绑定模型/adapter/实际pair编码/计分定义/包版本，每个run重新建立，不跨run盲用。

为了单卡每次只保留一轮图：先无梯度计算整对分数与loss系数，再重算每轮得分，按链式法则反传，整对结束才optimizer.step。额外forward换显存，不是把DPO改成逐轮独立偏好。要求所有dropout=0、重算分数一致；CPU有限差分通过，真实Torch直接全图与逐轮重算梯度对照脚本已准备，执行前强制运行。

## 已完成与未测门槛

已完成：DPO-PREP-20261012-001审核/26次真实工具重放/75轮重新编码；DPO-CONTROLS-20261012-003的25项CPU控制，包括mask污染/截断/非training负控、偏好方向、稳定loss、系数与多轮梯度有限差分、S1本地adapter SHA、reference key变更、GitHub白名单与旧同步分支。001/002控制记录保留，增加attention_dropout门槛，并修正同步需保留既有S100/MIX100文件后003保存最终源码/传输身份，均非模型运行。

未测：本地未安装Torch，实际autograd测试尚未执行；目标主机的HF Tokenizer检查、8B概率/梯度、显存、DPO step time、8步更新及重载、Agent效果均未测。脚本默认只校验数据，不构造LLM；只有另行获准使用--execute后才进行这些门槛。准备完成不等于GPU资格通过。

## 冻结8步探针与后续对照

探针8个不同task：[565,972,247,859,770,20,177,965]，覆盖五域；chosen24轮/2303targets，rejected21轮/1073targets，总204089 processed（单次读过一遍口径，实际包含reference和重算多次forward）。beta=.1、lr5e-6、seed42、现有S1 LoRA继续8次更新；固定终点，不做checkpoint selection、Agent评估或自动正式训练。

拟用一张96GB PRO6000；前次设备used峰值超过80GB，不能宣称A80080GB直接兼容。计划0.05–0.15脚本GPUh仅工程估算、未含部署等待；硬脚本上限1800秒。实际时价未知，不估造金额。必须实测reference时间、每步时间、allocated/reserved/设备采样显存、GPU利用率、GPUh与实例全占用。通过后再决定扩为12对完整一遍与开发评估。

后续对照草案 `configs/dpo_matched_control_plan.json`：同一S1起点，unchanged S1 / chosen-only SFT / DPO；两训练臂同12任务、相同chosen曝光、相同12 task-level updates、lr/seed。DPO额外处理rejected/reference，**不是严格等tokens/GPU算力比较**，报告额外成本。chosen-only loss按任务内target平均。此草案未实现或执行新的完整对照runner，不冒充正式矩阵已经ready；本轮准备的是8步probe入口。

## 文件与执行交接

- `experiments/DPO-PREP-20261012-001/`：原始新审核、26branch replay、12pair压缩包、manifest、config/identity/result。
- `experiments/DPO-CONTROLS-20261012-001/`与`002/`：初始/最终CPU控制及身份记录。
- `veriagent/dpo.py`：数据准入、cache key、target-only logp、两遍梯度。
- `scripts/run_dpo_probe.py`：默认validate-only，未来有界8步执行/保存/重载/故障保全。
- `scripts/check_dpo_torch.py`：小张量真实autograd对照，在加载8B前强制运行。
- `scripts/github_file_sync.py --include-dpo`：仅7个新增执行文件白名单，无权重/凭据；本轮未连接远端。
- `configs/dpo_probe_plan.json`、`configs/dpo_matched_control_plan.json`、`docs/daily/2026-10-12-dpo-learning-handoff.md`。

下一步是用户授权的单卡8步DPO cost/integrity probe，先核实实例/资产，固定新GitHub commit部署，再过Torch/HF/权重门槛。S1权重和历史SFT结果保持不变，输出新adapter；通过后保存证据关机并停止。当前机器未开机，旧监控未恢复，没有自动下一阶段。
