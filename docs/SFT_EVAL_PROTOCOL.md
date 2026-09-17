# 首轮 SFT 开发评估口径

固定 BASE_B1 / S1 / S2，各 development24 × seed42/43=48 条；执行前批准，配置见 `configs/sft_comparison_plan.json`。不使用 checkpoint validation、final 或 BFCL。所有模型使用同一已发布执行版本、同一 GPU 类型、软件和采样配置；S1/S2 训练也需相同 GPU 类型和代码版本。

主比较是 **S2−S1 的非空 reference task success**；S1−BASE_B1、S2−BASE_B1 为辅助比较。24 题和 failure targeting 的设计都使用过 development 信息，因此不能称为 sealed test。

| 指标 | 分子 / 分母与层级 |
|---|---|
| Task success | 官方 reward=1 的有效 trajectory / 有效 trajectory；另报20个非空reference任务与4个空reference任务 |
| Task 聚合 | 一个 task 的两个 seed 先平均，再对 task 求平均；完整48条时与trajectory均值相同 |
| Executable call | `call_diagnostics` 中 name/schema 合法且工具无异常 / 该列表全部调用；无法解析的输出另报 parse-error轨迹率，不能藏在分母外后说全部调用合法 |
| Wrong tool | 新人工语义标注的未知/功能不符工具调用 / 可定位的全部调用；过早使用相关工具可另标missing prerequisite |
| Wrong argument | schema错误或观察证明的错误目标/字段/条件调用 / 全部可定位调用；一调用多个问题去重一次 |
| Identifier grounding | 类型正确且可追溯到当前user/前序observation的ID或邮箱槽位；分别报错误槽位/槽位数、受影响轨迹/轨迹数；字符串出现不等于类型正确 |
| Redundant action | 无新增信息或合理恢复价值的动作 / 全部调用；重确认不机械全判错 |
| Retry loop | 三次连续相同参数、相同状态/无推进的模式；报受影响轨迹/有效轨迹，另报重复调用计数 |
| Premature termination | 仍可继续完成却主动结束的轨迹 / 有效轨迹；context/output/round cap单列，不把预算耗尽算主动结束 |
| Steps / tokens / latency | 每有效trajectory工具步数、实际输入/生成token及耗时；资源总账另包含无效尝试 |
| GPU / RMB | 进程含加载/核验的wall time与GPU-hours、采样utilization、peak allocated/reserved；实例闲置/准备/存储另列；不重复相加 |
| Cost per success | inference费用/该condition的官方成功数；0成功记不可定义；包含训练的amortized成本另列 |
| Generalization | 本轮未执行；composition reserve未资格通过，BFCL保持sealed，不能填0或用dev替代 |

Partial progress 仅作诊断，不能折算正式 success。基础设施故障的trajectory永久标记、保留成本；同一run中此前有效记录保留，但三条件不完整时不输出伪装完整的配对比较，也不自动补跑。

三组完整后，`compare_sft_evaluations.py` 按 task 成簇保留两个seed，使用固定seed20260917、10,000次配对bootstrap计算95%区间。小样本区间宽时照实报告，不扩大seed追显著。词法/自动错误候选不替代新的语义标注，不把旧Day3标签复制到新policy。

固定最终checkpoint，不做dev驱动的early stopping/挑epoch。即使训练loss下降、teacher reward很高或某几个demo变好，也不足以证明Agent提升。共享初始数据库的ID记忆风险通过显式grounding审核揭示，严格状态/组合泛化留给后续单独获批协议。
