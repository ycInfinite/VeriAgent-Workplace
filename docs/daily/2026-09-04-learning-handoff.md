# 2026-09-04 Learning Handoff

停止新实验：CPU 部分已收尾。接下来学习/考核和路线讨论，不租 GPU。

1. **今天回答的核心问题**：Workplace 核心是否可执行？reward 到底检查什么？数据能否直接做组合 held-out？真实 tokenizer 的输入和监督量有多大？

2. **开始前状态**：空项目目录；只有上一轮官方只读审计，无本地实验，无模型。用户授权完成所有租卡前可做工作，并要求学习材料和考核。

3. **实际执行**：建立 Git/项目约定；固定 193 个官方源码/数据/文档文件；下载 tokenizer/config 无权重；完成结构、环境、token、HTTP/数据契约、词面相似及保守切分审计；整理学习材料。

4. **变量/控制**：环境测试改变动作序列（正确/省略/空动作/错误前缀/无关写入）；其余固定源码、初始 CSV、任务和 CPU runtime。token 测试改变 role 与 context/target log-prob。没有模型自变量或参数更新。

5. **原始结果**：1255 train+545 validation；每个 split 五类等量。138 条脚本轨迹 0 无效；reference/repeat 各 24/24 reward=1，漏必要动作 18/18 为 0，无关写入 24/24 为 0；reset/isolation/138 次重放一致。955 个初始 prompt 为 4112–4153 tokens；学习 fixture 为 4536/89 processed/supervised。9 个 mask 检查、8 个接口检查通过。

6. **代表轨迹**：成功结构在 `Q0-TOKENS-20260904-001/grounded_fixture_DEV_ONLY.json`，实际 search→取 ID→reply，reward=1；失败结构在同目录 preference_mechanics_fixture 中，直接 Done，reward=0；`Q0-CONTRACT-20260904-001/noop_lookup_DEV_ONLY.json` 展示查询无会议后停止与盲停都得 1。所有 producer=SCRIPTED，不是 LLM trajectories。

7. **路线级结论**：可使用轻量适配器执行官方工具核心；binary state reward 适合结果检查，但不足以单独代表 grounded 决策。严格组合泛化未资格化，暂缓 GPU。当前清单 training/dev/checkpoint/组合预留=743/85/93/181，另保留 540 条过滤 final；原数据未变。

8. **尚未支持的推测**：Qwen 能否成功、主要 failure 是什么、S2 是否优于 S1、DPO 是否有效、单卡实际速度/显存、RL 收益，全部未知。并未证明 170 条空 reference 标错；也未证明语义泄漏为零。

9. **晚上最该读的五处函数**：

| 文件 → 函数 | 输入 → 输出 | pipeline 作用 |
|---|---|---|
| veriagent/environment.py → WorkplaceEnv.step | action → observation/error/diff | 可执行工具边界 |
| vendor/Gym/resources_servers/workplace_assistant/workplace_assistant_tools/email.py → search_emails / reply_email | query/ID/body → 数据/状态 | lookup 与写操作 |
| vendor/Gym/resources_servers/workplace_assistant/utils.py → is_correct | 两组 actions → bool | reward 语义 |
| veriagent/token_mask.py → TokenMaskInspector.inspect | messages/tools → ids/labels | supervised/context 分离 |
| scripts/audit_dataset.py → run | 数据+seed → 统计/manifest | 数据用途与隔离 |

10. **今晚三个知识点**：state 与 observation；reward 的充分性/必要性与反例；assistant-only loss mask 及 DPO 分支的条件概率。先读 docs/learning/START_HERE.md。

11. **五个面试追问（不附答案）**：

- reference replay 全通过，为什么不能等同于 oracle 的语义正确性？
- 没有写操作的任务，如何避免一个“总是结束”的 policy 被错误资格化？
- tool output 不参与 CE，为什么仍然会影响后续动作的训练？
- DPO chosen/rejected 的 observation 不同，序列 log-prob 应如何定义？
- 为什么“27 个工具定义都在 prompt”不足以证明工具组合泛化？

12. **下次需要用户确认的路线分叉**：是否收窄为 grounded lookup/state mutation 的数据选择研究；是否坚持严格 composition 并另外审计补充数据；或重新比较环境。先完成学习与考核，未自动决定。

13. **身份/配置/日志**：所有 run 在 experiments/registry.jsonl。DATA-001 的 code commit `2ef3f3b`，ENV-001=`d38cb53`，TOKENS-001=`a76fa59`，CONTRACT-001=`5b4dab5`，SPLIT-001=`3577631`，SPLIT-002=`8ceae72`，最终 SPLIT-003=`41ec3e3`；完整 SHA 在各 identity.json。最后一版还把 pilot reference 调用上限设为 4，避免七次必要写调用与六轮预算的明显冲突。配置均为各目录 config.json，原始轨迹为 ENV 的 trajectories.jsonl；对应 result.json 为摘要。所有正式 CPU run 有记录；SPLIT-001/002 仅被替代，未删除。没有正式 infrastructure-invalid run；Git 所有权与 shell 语法设置问题另记在 evidence/setup/notes.json。

考核状态：未开始。已提供 A/B/C 题目和评分标准，等待用户提交 A1–A5；不得提前宣称通过。

后续补充：用户允许继续推进。已新增 GPU_HANDOFF.md、只读 gpu_preflight.py，并准备三个 dev tasks 的独立加载/接口 smoke 实验卡。脚本通过语法检查；尚无个人平台、实际报价或 GPU 实例，因此未租卡、未下载权重、未运行任何模型。学习考核记录不变。单卡建议为 A800 80GB/A100 80GB，实际选型取决于报价与镜像兼容性。
