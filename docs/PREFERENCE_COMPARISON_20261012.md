# 2026-10-12 偏好方法小对照（已登记，待执行）

用户在8步probe完成后要求继续，进入固定12对的chosen-only SFT vs DPO开发对照。原SFT/probe文件不改。S1是同起点控制，新主机同一次运行再做一次48条baseline评估，避免旧主机/驱动混杂。

| 字段 | 定义 |
|---|---|
| Research Question | DPO是否比同批chosen继续SFT有额外行为收益？ |
| Hypothesis | rejected相对信息可能有帮助，但12对旧Base负例也可能已经太简单。 |
| Independent Variable | task-mean chosen CE vs整轨迹sum-logp DPO。 |
| Controlled Variables | 同原S1、12任务/次序、12updates、一遍chosen、lr5e-6、seed42、8K、LoRA、同机三组dev24×42/43。 |
| Metrics | 主指标非空任务DPO−CHOSEN_SFT；总体/空任务、语义审核、调用/tokens/延迟/显存/GPUh/费用。 |
| Evidence Gate | 原始pair/S1身份、7项真实Torch控制、HF75轮、真实更新/重载、三组各48有效rollouts。 |
| Cost Bound | 一张已有96GB卡；每个训练/评估<=30min；估计0.55–0.85脚本GPUh+部署/回收，6.98元/h；4h资源保护。 |
| Failure Branch | 正式run失败即保存停止，不自动重跑、加数据/seed/context、改超参。 |

两组均从原S1开始，不能接8步probe权重继续。beta0.1；无checkpoint selection。SFT每task的所有chosen token按该task总target数平均，累积各轮梯度后更新一次；DPO处理整对，额外rejected/reference，因此不声称等tokens/FLOPs。正式主比较是DPO−CHOSEN_SFT，S1是辅助基线。

runIDs、task order、模型/data revision、12pair SHA在configs/preference_comparison_plan.json。CPU门槛与源码身份在experiments/PREF-PREP-20261012-001/。新training/eval runners独立保存，旧inference loop AST完全相同。数据少/单训练seed/已暴露开发集，不能宣布heldout泛化。没有读取BFCL或final内容。

执行顺序：PREF-EVAL-S1-20261012-001 → PREF-CHOSEN-SFT-20261012-001 → PREF-EVAL-CHOSEN_SFT-20261012-001 → PREF-DPO-20261012-001 → PREF-EVAL-DPO-20261012-001。

首次独立Torch预检因入口缺项目import路径失败，模型尚未加载、正式run未创建。失败在PREF-HOST-PREFLIGHT-20261012-001和first_launch/保留。修复仅新增common.ROOT导入；PREF-PREP-20261012-002通过12项CPU检查。执行版本更新为df1680c574ef9310f6289aa5e6e112f6d05c87ff，数据/超参/正式runIDs不变，使用新运行日志目录。
