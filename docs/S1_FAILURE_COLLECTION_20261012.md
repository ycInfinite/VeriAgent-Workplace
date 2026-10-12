# 当前S1 training失败采集（已冻结）

用户要求小规模采集当前S1失败并审核DPO数据，不训练。固定25题：每域4道需操作+1道空reference，五域均覆盖。候选来自87条S1未训练且teacher已审的非空任务和29条已审空任务。按SHA256(S1-TRAIN25-v1:task_uid)在每个层中选最小rank，不使用采集成绩换题；只有seed42各一次，不补采。

| 字段 | 定义 |
|---|---|
| Research Question | 当前S1能否在这些training任务产生可归因、可配对的剩余失败？ |
| Hypothesis | 当前策略负例可能比旧Base负例更有信息，合格pair数量未知。 |
| Independent Variable | 25次新S1 rollout，无权重更新。 |
| Controlled Variables | 原S1/B1/tools/state、8K/6轮/2048输出、seed42、预定25题。 |
| Metrics | 官方/分层成功、工具/成本指标、失败类别、合格pair产率。 |
| Evidence Gate | training池隔离、避开S1已训练任务、teacher及上下文哈希、真实执行/replay、完整pair语义审核。 |
| Cost Bound | 已有单96GB卡；脚本30min、生命周期2h；估计0.12–0.25GPUh+部署回收，无新teacherAPI。 |
| Failure Branch | infra异常保存停止；截断/歧义/污染pair暂缓，不重采、不更新DPO。 |

计划configs/s1_failure_acquisition.json，数据experiments/S1-FAILURE-PREP-20261012-002/。001在解析旧压缩任务时未展开tool_schema_ref而失败，永久保留；002使用原schema bank重建并与教师schema逐个相等。25初始context都可容纳，max4213，11项CPU控制通过。

这些题只对当前S1的50题训练集未见，可能已被S100/MIX等其他独立adapter使用，不宣称全项目从未见过或代表全training分布。已有教师approval只是来源门槛，形成新pair时仍重新审核chosen/rejected的关键语义，不把所有reward0都当模型错。完整结束/有效context/真实观察保留，不将基础设施故障作为负例；合理的同reward语义偏好需单独明确标签，不能暗换旧12pair配置。没有使用dev/final/BFCL作训练。

## 当前停点：用户选择等已有GPU

D62与D47均返回空闲GPU0，未开机成功。用户选择先保留准备，等已有实例有卡再执行；不新租、不重试、不创建库存监控。采集代码/4文件白名单已推GitHub commit8ca196e1bdfbbfade4947916838065a4446a4a6e，未远端部署。既有teacher25条仅作未来chosen来源，尚无新S1 rollout，新的pair产率未测、数据对未审核，绝不以CPU准备冒充采集。审核步骤和处置标签见configs/s1_failure_pair_review_protocol.json。未来按原25题执行一次、回收后关机，再本地审核，不追加DPO更新。
