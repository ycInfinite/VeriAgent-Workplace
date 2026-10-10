# 2026-10-10：恢复首轮 SFT 阶段

核心问题：假期后能否直接执行冻结的S1/S2？本地数据和评估入口复核通过，当前缺可用的远端访问，GPU实验尚未开始。

开始前：9月17日准备和无卡预检完成；尚无两组310步训练或对应Agent评估。今天用户已要求进入下一阶段，因此旧“等开训指示”在冻结范围内已满足，不必重复询问是否允许同一实验。

实际执行：读取状态/合同/配置和实验目录，核对Git状态；S1与S2各50任务/155轮/310计划更新的CPU准入重跑通过；BASE_B1固定dev24×两seed输入通过。检查两个旧监控仍暂停。浏览器连接三次失败，未认证旧SSH、未开机/租机/生成教师数据/更新参数。

变量和控制：没有修改算法或数据；冻结Qwen3-8B、LoRAr16、seed42、两组样本和近似token预算；评估仍是同一dev24及42/43两个seed。执行顺序已登记：新BASE_B1→S1训练/评估→S2训练/评估，均使用新20261010实验ID，不覆盖旧run。

原始结果：三个本地命令退出码0；真实GPU训练、Agent成功率和新step time均未测。今天没有新的success/failure trajectory；可复习旧teacher task945的grounded reassignment、task263的跨域ID误用和task83的错误加总，不能当今天的新模型结果。

路线结论：本地材料保留，接下来需要恢复登录AutoDL的浏览器连接或提供当前自有GPU实例入口；旧实例和缓存是否仍存在必须重核，不能假定已删除或仍可用。尚未支持SFT收益或组合泛化。现有阻塞是浏览器访问，不是数据质量或训练失败；操作失败永久保留，不计模型能力指标。

今晚可看四个入口：

| 文件→函数 | 输入→输出 | 作用 |
|---|---|---|
| veriagent/sft_stage.py→load_inputs | arm→已审examples/固定顺序 | 复核来源、hash和完整labels |
| scripts/run_sft_comparison.py→main | 执行开关/arm→adapter及训练日志 | 未来真实CE和LoRA更新，今天未执行 |
| scripts/evaluate_sft_comparison.py→load_eval/main | 固定dev与policy→真实轨迹 | 将参数更新与Agent能力检验分开 |
| scripts/compare_sft_evaluations.py→main | 三组完整结果→配对开发比较 | 校验控制变量并按task成簇估计不确定性 |

学习点：CPU数据检查不等于GPU训练；LoRA重载一致不等于Agent任务成功；假期后的环境可用性需要重新确认，实验数据和预算无需随意改动。

五个追问（不给答案）：
1. 为什么不能把9月17日的无卡预检视为今天GPU可用的证据？
2. 为什么重新开始要用新实验ID但保留同一批数据？
3. S1/S2各310步为什么仍须披露token差异？
4. 为什么需要同条件重新跑BASE_B1？
5. 遇到OOM后直接扩大context或换监督mask，会怎样影响实验解释？

下一路线：恢复实际远端访问后核验归属/缓存/软件/GPU，执行已授权冻结矩阵；不自动新租、进入DPO或RL。本轮无需新的学习考核来解除执行权限。

证据：experiments/SFT-RESUME-20261010-001/config.json、result.json；原配置configs/sft_comparison_plan.json；计划执行代码commit f9d45c282b7cbebeedb1063e3c2c705330e0b23c；当前仓库原HEAD ff79c1f。GPU/model/API执行均为0，当前单价未知。
