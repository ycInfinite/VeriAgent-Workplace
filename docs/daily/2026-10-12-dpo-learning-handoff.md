# 2026-10-12 DPO学习交接（粗颗粒）

今天只学一个区别：**SFT模仿好轨迹；DPO比较同一道题的好轨迹和坏轨迹，让模型相对固定起点更偏向前者。** 数据是离线历史记录，不是online RL。

## 今天做到哪

开始前：S1/S2/S100/MIX100都已完成，只有13个历史DPO候选，没有正式偏好数据准入。

今天：重新阅读13对全部可见消息，回放26条轨迹，12对通过、1对暂缓；准备编码、reference、8步训练入口及后续对照草案。75个assistant轮次，总5143个直接target tokens，最长单轮5431。25项CPU控制通过；GPU/API/参数更新=0。没有去租卡或开机。

唯一变化是进入DPO准备阶段；原SFT配置/数据/结果不动。12对均来自training池，与S1/S2训练task IDs无交集；开发和sealed测试不进训练。完整日志与路径见末尾。

## 用一个真实案例理解

training task859：把12月1日最后一场会议改名。

chosen：查询当天会议→查第二页→正确选15:00的00000252→改名→如实报告，官方reward1。

rejected：直接把12345678当会议ID→工具说不存在→要求用户给ID，reward0。

这对有效的原因是任务、初始状态与工具相同，差异来自模型行为。不是因为chosen更长，也不是随便找两道题拼一起。

task271暂缓：rejected越权删了其他负责人的客户，这是明确模型失败；但它被轮数上限截住、没有最终回应。首轮probe先排除这种截断分支，仍保留原始失败，不能改称基础设施错误。

## 四个对象不要混

- chosen：审核合格的成功轨迹，是训练数据。
- rejected：同题模型行为失败轨迹，也是训练数据。
- policy：将继续更新的Qwen3-8B+S1 LoRA。
- reference：训练开始时同一份Qwen3-8B+S1，之后固定。它不是生成chosen的DeepSeek教师，也不是禁用LoRA后的裸Base。

官方原始DPO是偏好优化，可用固定数据训练，不需要在每一步做新rollout。[原论文](https://arxiv.org/abs/2305.18290v3)。本项目用多轮assistant行为token的概率求和，tool观察只作为条件输入。

```python
# 教学简化式；实际实现见veriagent/dpo.py
margin = (policy_chosen_logp - policy_rejected_logp) \
       - (reference_chosen_logp - reference_rejected_logp)
loss = -log_sigmoid(0.1 * margin)
```

这里每个logp是整条轨迹所有assistant目标token的log概率之和。不同分支有自己的工具结果，不能给rejected塞chosen的观察。User/Tool tokens的labels=-100；以前assistant在后续轮是context，不重复作为那一轮的target。

初始policy和reference一致，margin约0，loss约log(2)。往chosen方向提高相对概率，应使loss下降。下降仍不等于Agent成功率提高。

## 为什么不用两份8B同时放显卡

先在更新前算好固定reference分数，保存身份哈希。每步先算policy分数，再按loss对分数的导数逐轮重算/反传，一对完成后才更新一次。多做forward换少保留计算图。官方TRL也支持预计算reference概率节省驻留显存，但我们的多轮mask和梯度仍需自己验证。[官方文档](https://huggingface.co/docs/trl/dpo_trainer)。

本地已经做有限差分验证；没有Torch，因此真正autograd与整图梯度一致性还没跑。未来脚本先用小张量测试通过，再加载8B；不是把数学示例当真实LoRA训练。

## 五处代码，只掌握输入输出

| 文件→函数 | 输入 | 输出/作用 |
|---|---|---|
| scripts/prepare_dpo.py→main | 13候选+原始两来源轨迹 | 12pair导出、13处置、26重放证据 |
| veriagent/dpo.py→load_pairs | 固定配置、哈希锁定pair文件 | 通过mask/完整性/池检查的pairs |
| veriagent/dpo.py→turn_logp | policy、一个完整assistant轮编码 | 只计算assistant目标token的log概率和 |
| veriagent/dpo.py→pair_backward | 两条完整轨迹+固定reference分数 | 偏好loss/梯度；整对后才由runner更新 |
| scripts/run_dpo_probe.py→main | S1 adapter、固定8对、另行执行授权 | 未来8步新adapter/资源/重载证据；今天未执行 |

## 路线结论与不足

可以准备小规模机制probe，不能说12对足够训练出泛化。chosen全部DeepSeek，rejected全部旧Base，11/12对chosen更长；模型可能学到文风/冗长特征。它们不是当前SFT失败分布，也没有“正确不操作vs错误操作”的专门偏好对。

后续正式比较需要S1、S1+同批chosen继续SFT、S1+DPO，否则新12题带来的收益可能被误算成DPO收益。这三组对照目前只有设计草案，未实现完整实验矩阵；相同任务/更新数不等于相同算力，DPO额外forward成本要单独记录。

未来8步probe选8对覆盖五域，beta=.1、lr5e-6、seed42、context8192，从S1继续。不是从今天分数最高的MIX临时换起点，沿用原偏好候选的S1对照计划。先验证完整性和成本，再决定正式对照。

## 今晚三个知识点

1. preference数据必须同题同初始条件，reward只是审核入口。
2. reference是固定起点；多轮tool observations是上下文，不是policy生成目标。
3. DPO probe、正式方法对照、最终泛化是三种不同证据。

## 五个追问（不附答案）

1. 为什么不能拿A任务成功轨迹和B任务失败轨迹凑一对？
2. 为什么reference不能直接等于DeepSeek教师，也不能直接禁用S1 adapter？
3. 工具观察进入input_ids但不进入loss，这对trajectory DPO有什么意义？
4. 12对里11对chosen更长，会带来什么混杂？为什么不能直接改成“短=好”？
5. DPO比原S1提高了，为什么仍需同批chosen-only SFT对照？

未回答前不标记掌握；考核不阻止已授权工程准备。

## 下一步与证据

下一步需决定是否执行单96GB卡8步cost/integrity probe。预计0.05–0.15脚本GPU小时，估算非实测，部署等待另计；实际时价未知。本轮没有GPU或API费用。Torch自动求导、目标主机HF模板、显存/真实梯度/8次更新/重载尚未验证；不自动进入正式训练或RL。

基线commit8890b985b504358610478d382ebe9f17b875e4fb；新准备源码SHA在控制结果中，发布commit以GitHub该文件提交为准。

- experiments/DPO-PREP-20261012-001/{config,identity,review,replay,manifest,result}.json 与pairs.jsonl.gz。
- experiments/DPO-CONTROLS-20261012-003/result.json：最终25项控制和源码SHA；001/002前版控制永久保留。
- configs/dpo_preparation.json、configs/dpo_probe_plan.json、configs/dpo_matched_control_plan.json。
- docs/DPO_PREPARATION_20261012.md：八字段、逐对理由、范围/成本/未测门槛。

SFT当日学习文件继续保留在2026-10-12-learning-handoff.md，本文件单独补充DPO，不覆盖上午结论。
