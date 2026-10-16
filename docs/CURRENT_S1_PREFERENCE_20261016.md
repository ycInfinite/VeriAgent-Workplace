# 当前S1六对偏好对照预登记 — 2026-10-16

状态：本地准备通过，尚未开始GPU模型运行。用户已要求继续上一轮建议的六对对照。

【Research Question】

Do six reviewed currentS1 failure pairs improve exposed-dev behavior beyond the same chosen-only SFT data?

【Hypothesis】

CurrentS1 errors may provide useful relative information; six pairs may be insufficient and any gain is exploratory.

【Independent Variable】

Task-mean chosen-only CE versus whole-trajectory sum-logp DPO, both from exact originalS1.

【Controlled Variables】

Same six tasks/chosen exposure/order,oneepoch6taskupdates,lr5e-6,seed42,beta0.1,8192,originalS1,host/driver;fixeddev24x42/43.

【Metrics】

Primary paired nonempty DPO minus chosenSFT success;overall/empty, fresh semantic audit,tokens/VRAM/latency/GPUh;single exposed-dev experiment.

【Evidence Gate】

Six reward-gap data hashes,originalS1,train/dev isolation,HF all39 turns,Torch gradient controls,6finiteupdates,save/reload,144valid evals.

【Cost Bound】

One already-running userPRO6000;each script1800s and process pipeline<=9000s;engineering estimate0.55-0.80scriptGPUh plus setup/retrieval;rateunknown;KEEP_INSTANCE_ON, no poweroffguard.

【Failure Branch】

Stop pipeline on formal integrity/infrastructure failure;preserve partial output;no retries,extra data,seeds,tuning or automatic nextstage.

固定任务顺序：[1000, 51, 349, 1076, 1194, 473]。两组各6次更新，原S1同机新baseline与两组最终adapter各48条dev评估；不从中选checkpoint。相同chosen数据暴露和更新次数，不是相同tokens/FLOPs；不与旧12对做负例来源的单变量因果比较。

六对包含两个正确不操作示范（1000/51），但只覆盖analytics/calendar。702另存，不参加这轮训练。当前开发集已经多次暴露，所有结论仅限探索性机制检查。

13CPU准备检查通过，39个canonical assistant轮次；6对最大序列5885。实际HF模板/mask、Torch梯度、S1权重、训练更新/保存重载都在远端执行前后检查。原12对配置/入口、原S1、旧adapter不修改。

GitHub只新增同步五个白名单文件；比较汇总和准备脚本仅本地。流水线每个模型脚本1800秒，进程总上限9000秒，任一步正式失败停止，保留证据，不自动重试。用户要求保留机器开机，没有关机保护。当前时价未知，RMB留null，报告继续占用。

来源：experiments/CURPREF-PREP-20261016-001/；configs/current_s1_preference_plan.json；执行commit在远端identity中记录。
