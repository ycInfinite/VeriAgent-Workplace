# 2026-09-17 学习交接：普通API教师选型

1. 核心问题：DeepSeek Flash适不适合低成本生成Workplace教师数据？当前建议优先资格测试，质量未测。
2. 开始状态：SFT八步probe已完成；15条完整教师轨迹已批准；Token Plan交互示范成功但协议不合格；昨天三台实例均已关机。
3. 实际执行：读取官方价目表、工具/思考/缓存说明，复用历史token量做情景计算；更新普通API路线决定。没有模型调用、开机、采集或训练。
4. 变量/控制：只是价格算例。token量固定为旧Qwen样本；按峰谷/缓存变动。75%合格率是投影假设，DeepSeek尚未测得。
5. 原始结果：未缓存20次约0.424–0.848元；假定75%合格率，1000条合格约28–57元。详细公式和来源见成本JSON。
6. 代表轨迹：今天无新增轨迹。仍可学习旧training707的grounded lookup→update；不把昨天的9,805个provider tokens直接当作学生tokenizer的超限证明，旧运行配置未加载则已有独立证据。
7. 路线结论：采用用户新指示，回到普通API；停止继续建设Token Plan交互链路。Flash作为候选，先资格测试。
8. 未支持推测：Flash同样75%合格、同样缓存命中/长度、更快或更强，均未验证。
9. 三个代码入口（今天未改训练实现）：
   - `veriagent/teacher_rollout.py` → `teacher_trajectory`：row/task/cohort/config/transport/剩余时间（可选response_sink与producer）→ 完整采集记录；函数内部创建环境和编码器，执行多轮循环。目前是旧百炼链路，不能只改模型名就视为已兼容DeepSeek。
   - `veriagent/teacher_data.py` → `CanonicalTeacherEncoder.encode`：prefix messages、tools、assistant message → student input_ids/labels/token计数；检查完整上下文与监督目标。
   - `scripts/collect_teacher_probe.py` → `summary`：records和config → 成功、有效性、usage与费用汇总；新provider的缓存和费率字段需要单独适配，尚未执行。
10. 今晚知识点：累计请求tokens为什么多于最终轨迹长度；合格样本单位成本与API单价为何不同；默认thinking为什么必须从实际响应验证。
11. 面试追问（不提供答案）：如何比较两位教师的性价比？如何定义合格轨迹分母？为什么缓存率不能照搬？教师和学生tokenizer不同会影响哪些预算？低价教师成功率下降时如何决定是否继续？
12. 下一路线分叉：确认实际使用官方DeepSeek还是转售平台后，登记固定20题资格测试；通过后再决定采样规模。不是本次咨询已启动的实验。
13. 证据：`docs/DEEPSEEK_FLASH_ASSESSMENT_20260917.md`、`evidence/teacher-acquisition/deepseek_flash_cost_20260917.json`；原用量来源`TEACHER-ACQUIRE-20260916-001`。本日无新experiment_id或训练config。
