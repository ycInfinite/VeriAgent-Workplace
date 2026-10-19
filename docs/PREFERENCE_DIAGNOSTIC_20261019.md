# 29对偏好数据的拟合与执行诊断 — 2026-10-19

本轮只读现有三个策略；没有参数更新。所有正式ID是新建诊断ID，不重跑旧训练或dev。

【Research Question】

DidfinalSFT29/DPO29fit29offlinepreferences,anddoesfittranslateintorealtrainingtaskbehavior?

【Hypothesis】

Preference marginsmayimprovewithoutreliablycorrectonlineexecution;neitherunderfitnorcreditassignmentfailureispresumed.

【Independent Variable】

FrozenoriginalS1reference versusfinalchosenSFT29/DPO29;nooptimization.

【Controlled Variables】

Exact29pairs/taskorder/messages/tools/state;BF16/SDPA/packages;B1/seed42/8192/6rounds/768call/2048total.

【Metrics】

Delta chosen/rejected sumlogp andper-target diagnostics,reference-relativemargin/loss,bydomain/empty/length;58realrollouts tasksuccess/semanticfailures/cost.

【Evidence Gate】

Cachedreferencekeys/SHA and2fixedtask calibration;all179HFmasks;sourceadapterhashes/zero trainableparams;58validrealrollouts;semanticreview.

【Cost Bound】

Existing96GBsingleGPU;expected0.3-0.5scriptGPUh,unknownrate;1800s/script,7200spipeline;KEEP_INSTANCE_ON.

【Failure Branch】

Stoponintegrity/infra/calibrationfailure;preserveraw/noautorerun/noextraepochs/task/seed/API/RL/test.

## 预先固定的判读

先用原始S1复算固定task1099和最长task358的两分支，误差必须<=0.02；全部29的缓存key、模型/adapter/数据/评分配置身份同时验证。不把两题数值复算称为29题全部重算。

两个最终adapter各重算同29pairs的sum-logp：Δchosen、Δrejected、relative margin=Δchosen−Δrejected、DPO loss。按pair平均，不把sum-logp直接当长度无关的chosen质量；每目标token的变化只作诊断，不改原DPO目标。统计所有29的正margin比例、chosen提升/下降、rejected抑制及按域/空reference/长度分组。两者均为训练后完整固定集分数，不能与逐步不同题loss混为下降曲线。

再使用两个最终adapter各运行同29训练任务、seed42一次，共58条。原S1当初reward0是pair入选条件，不能以此称新模型有无偏泛化提升。按本轮真实输出重新审核全部28条空reference，以及所有非空失败/两策略成败不同的轨迹；未全部语义审核的其他成功仅保留official标签。新rollout只用于诊断，不自动准入新SFT/DPO数据。

偏好提高且rollout成功：至少有训练集行为吸收，不等于泛化；偏好提高但rollout失败：定位打分与闭环执行之间的差距，不能直接宣布DPO不适合长程；偏好未提高：再检查拟合强度/数据，但不自动加步数。没有达到某个任意成功率就自动换路线的阈值。

先前dev结果固定35/34/33，不重跑dev，不使用本轮结果挑新checkpoint；final/BFCL封存。对于教师质量，本轮沿用已审29而非宣称完成独立第二审。

## 准备状态

17CPU控制通过。首个SSH连接失败，用户回复恢复后连接同一主机并验证S1/SFT29/DPO29三套adapter SHA。CPUprep001错误假设原S1存在本地，文件缺失后停止；002区分本地缓存与远端强制验证，原失败保留。模型调用0，待GitHub部署。实例不关机；时价未知，计算与等待费用分开记录。
