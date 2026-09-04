# BFCL external evaluation protocol

2026-09-04 只审计官方文档；case、reference answer 和模型 response 数据未下载。`vendor/BFCL-docs` 只有 README、TEST_CATEGORIES、pyproject。

当前官方榜单是 V4。当前 main 与榜单复现 commit 不同，见 configs/sources.json。建议以后固定一个 commit，首选 multi_turn_base / miss_func / miss_param 类别；long_context 单列预算与协议。类别/条目数在真正封存运行前从所选版本清单核验。

BFCL 多轮评测执行工具并在各轮做状态和执行结果检查。外部 BFCL 测试的是跨环境工具使用能力，不能代替 Workplace 内部组合隔离。引用：[官方 multi-turn 方法](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html)。

流程：保留 B0 → 在内部 validation 选完 S1/S2/P1 checkpoint → 冻结所有训练与选择 → 同一 BFCL handler/parser/prompt/decoding 下统一测权重。使用自建微型工具例子验证端点，不用 final cases 调适配器。任何基础设施重跑保留旧记录，不能根据成绩改变协议。

若只测三个类别，报告类别分数与样本量，不能称为完整 V4 Overall。修改 context cap/工具处理协议则单列项目变体，不能冒充官方可比成绩。官方 README 指出部分评测模式可能把缺失类别按 0 纳入 summary 列，不直接引用该列。

推荐复用独立 serving endpoint，将 BFCL 与 Gym/训练依赖隔离。当前 BFCL pyproject 的 NumPy/vLLM 固定版本与 Gym 不同。本轮未部署端点或验证 BFCL 对 adapter 的完整推理链。

Sealed 是本项目不使用 final cases 的承诺，不是对 Qwen 上游训练数据未接触 BFCL 的保证。
