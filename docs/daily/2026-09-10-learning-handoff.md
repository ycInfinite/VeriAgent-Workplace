# 2026-09-10 Learning Handoff：开始逐步学习 SFT 输入与监督目标

**文件同步更新：用户要求GitHub传文件后，bc5aa55已推送，并由远端直接从GitHub取得20个执行白名单文件、逐项核验；发布阻碍已解除。私有仓库匿名clone失败已保留，改用临时只读文件链接，不传账号token或保存链接。没有模型或训练运行，当前仍等待GPU模式。**

**最新交付：新个人 AutoDL 实例的无卡准备已经完成。固定权重/依赖、20题实际 tokenizer/CPU工具检查通过，8步 LoRA probe 入口已部署；模型尚未加载或更新。当前等待用户切回 GPU 模式，金额门槛已由用户覆盖。详见 SFT_NO_CARD_HANDOFF.md。**

**最新进度：用户要求直接推进实验，教学保持粗颗粒。已完成 SFT-PREP-20260910-001，下一步等待 GPU 实例与实际价格后采集固定 training 任务。前面的教学安排不再作为工程入口；本页末尾记录实际实验。**

这是持续更新的学习记录，今天尚未收到学习者考核回答。没有新增实验。**当前方向已由用户更正为直接进入 SFT/LoRA 学习；下方最初的基础复习安排保留为历史，最终安排见末尾补充。**

1. **核心问题**：轨迹中的 observation 与 assistant action 怎样成为不同的训练角色？
2. **开始前状态**：学习合订本已交付，Day 3 完成，SFT/DPO 未执行，考核未评分。
3. **实际内容**：开始一段讲解配一个问题的互动学习；读取当前状态与 `TokenMaskInspector.inspect`，解释 `labels.append(token if inside else -100)`。
4. **变量 / 控制**：无实验变量；教学例子以 task 0 中 observation 提供的 00000057 为依据，消息展示为教学简化，不伪装成完整原始轨迹。
5. **结果**：尚无学习答案或新实验数字；不能判断已掌握。
6. **代表轨迹**：引用 Day 3 task 0 的查询取得 ID 再回复。仍为 dev，不用于训练。
7. **路线结论**：只推进学习；工程仍在 Q0 资格收尾，未批准下一训练阶段。
8. **未支持推测**：不能推断已掌握 CE、mask、DPO，不能将教学规则视为完整 trainer 对齐通过。
9. **代码导读**：

| 文件 → 函数 | 输入 → 输出 | 作用 |
|---|---|---|
| veriagent/token_mask.py → TokenMaskInspector.inspect | messages/tools → ids/labels | 当前小节的 context/target 划分 |
| scripts/run_day3.py → inference_trajectory | 模型/任务/配置 → 真实轨迹 | 说明 observation 怎样进入模型上下文 |
| veriagent/environment.py → WorkplaceEnv.step | action → observation/state diff | 区分环境提供的信息与模型生成内容 |

10. **本轮知识点**：input_ids 与 labels；-100 仅忽略直接监督损失，不删除输入。
11. **五个递进追问（逐次进行，不一次发给学习者）**：删除所有 masked 输入会怎样？同一个 ID 出现在不同角色为何有不同 labels？logits/labels 为何 shift？模板 prefill 为何不能自动算生成目标？loss 下降为何不直接证明 Agent success？
12. **下一步**：等待 LEARNING-20260910-Q1 的解释；根据回答纠错或进入 shifted CE，不预判通过。正式 A/B/C 考核保持未评分。
13. **证据与成本**：引用已有 Q0-B1-20260904-001 和 Q0-TOKENS-20260904-001；GPU 执行 commit cb4067c3e0dd21723d5664e7ccd27cdd3120c51e。本次无 experiment_id、无新模型运行 config，不追加实验 registry；新增付费 GPU/API 费用 0。

## 用户更正后的最终学习安排

用户说明 Day 3 前内容基本掌握，希望进入 SFT。取消等待 LEARNING-20260910-Q1 的安排，保留其未评分历史；不要求先做完基础复习才继续学习。

本次交付 [第五课：第一次 LoRA SFT](../learning/05-first-lora-sft.md)，按 SFT-A 机制、SFT-B 数据/实现准备、SFT-C 完整性与 cost probe、SFT-D 正式 S1/S2 对照划分。重点直接解释 LoRA 矩阵、PEFT 接入、teacher forcing、batch、forward/loss/backward/step、参数变化、保存重载。代码为新写教学示例，不在本轮执行。

官方核验：2026-09-10 阅读 PEFT quicktour/LoRA/配置文档、PyTorch 自动微分教程，并核对 Transformers v4.56.2 的 Qwen3 forward 与 causal-LM loss 内部 shift。文档 main 或 v0.20.0 不是已选项目训练版本；实际软件组合仍需锁定和验证。

五处教学函数及管线作用：

| 所在文件 | 函数 | 输入 → 输出 / 作用 |
|---|---|---|
| 第五课第 2 节 | TeachingLoRALinear.forward | 特征 → 原层输出加低秩增量 |
| 第五课第 3 节 | attach_lora | 已加载 base → 带 LoRA 的模型 |
| 第五课第 5 节 | collate_audited_records | 已审计 ids/labels → batch 张量 |
| 第五课第 6 节 | one_sft_update | 模型/优化器/batch → 教学中的单步更新与诊断 |
| 第五课第 8 节 | save_and_reload_for_eval | adapter/干净 base → 重载模型 |

今晚知识点调整为：LoRA 冻结与增量、反向传播和参数更新的区别、保存重载与效果评测的区别。五个新追问见第五课第 11 节，不附答案。没有实际训练 loss、梯度、权重差异或新任务结果，43,646,976 仍是条件明确的理论参数数。

下一步由用户按阶段掌握 SFT 内容；实际工程仍需共同 baseline、training-pool 高质量数据、冻结 eval、模板对齐与 probe 成本配置。新增 GPU/API 费用 0，无 experiment_id，不将教学片段登记为模型 run。

## 最终实际实验：SFT-PREP-20260910-001

1. **核心问题**：逐轮真实输入/输出能否形成严格 SFT 目标，且避免 dev 混进训练？
2. **开始状态**：未开始训练，没有合格 training 轨迹；旧 role-only 编码存在 forced-prefill 差异。
3. **实际执行**：编写 TurnEncoder 与训练准入；固定 training20；跑 CPU 审计；准备真实模型采集入口并白名单打包。
4. **变量/控制**：改用逐轮编码，模型权重不变；固定 tokenizer、原始轨迹、split、选题 seed、B1 候选 prompt 和 8K 边界。
5. **原始结果**：75 条/200 次生成全部输入哈希与 target 匹配；11,186 supervised、912,164 processed tokens；75 条 dev 均拒绝训练；7 个负向检查通过。training20 五域各4，初始 context 20/20 适配。
6. **代表证据**：原始 Day 3 task18 仍用于编码诊断，不能训练；本次逐轮证据在 turn_audit.jsonl，只导出数值/哈希诊断，不导出 dev 训练 token 数组。
7. **路线结论**：CPU 准备通过，推进真实 training 数据采集；没有把整个 Q0/训练资格标为通过。
8. **未支持**：新数据成功率、质量审核、训练 loss/梯度/adapter/重载、泛化均未测试；B1 与组合资格保留局限。
9. **五处代码**：sft_data.py → TurnEncoder.encode（轨迹/轮次→ids/labels）；admit_training_trajectory（轨迹/审核/固定任务→准入）；prepare_sft_probe.py → run（配置→CPU证据/任务清单）；collect_training_probe.py → main（固定training任务/实际报价→未来真实采集）；build_sft_acquisition_bundle.py → main（白名单→上传包/哈希）。
10. **三个学习点**：dev 不能转训练；输入/目标边界要与实际生成一致；质量审核通过后才做参数更新。
11. **五个备用追问**：为什么逐轮编码重复 context？为什么 reward=1 还不能训练？prefill 应如何计数？怎样阻止任务改名后跨 pool？CPU 编码通过还缺哪些训练证据？不要求答完才推进。
12. **下个路线分叉**：等待单卡 A800/A100 80GB 型号、报价和入口；最多20条B1候选采集；若合格成功不足两个不同任务，报告数据来源分叉，不自动加采样或改 prompt。
13. **身份/费用**：CPU 源码 commit 23fa06f；采集包 commit 537b1876；配置/identity/raw/result 在 experiments/SFT-PREP-20260910-001；下一轮卡 configs/sft_acquisition_plan.json；包回执 evidence/sft-preparation。CPU 3.97秒、新增GPU/API费用0，无 invalid prep run。采集入口只在本地验证输入与打包，未执行GPU。

## 后续实际推进：个人 AutoDL 无卡准备

1. **核心问题**：能否在0.5CPU/2GB的无卡环境完成固定模型、依赖与训练入口准备，避免付费GPU时段做这些工作？
2. **开始状态**：用户提供新个人SSH入口，目录无既有项目/权重；镜像已有Torch2.8.0+cu128。随后用户明确免除当前金额门槛。
3. **执行内容**：固定SSH主机公钥后连接（密码仅不回显输入）；白名单上传与哈希核验；独立venv复用Torch；固定revision下载权重；完整SHA核验；复制并检查四个tokenizer/config文件；远端20题模板/token比对；脚本工具/reset检查；PEFT与probe导入检查。没有规避no-card的GPU权限。
4. **变量与控制**：迁移到新Linux运行环境；固定任务、模型revision、tokenizer哈希、官方工具与单卡范围。预算政策改变被明确记录，未知费用为null。
5. **原始结果**：5分片共16,381,516,776 bytes全部匹配；20/20模板与token匹配；task565脚本参考动作reward1、状态变化、reset通过；training_import_check中CUDA初始化false、模型实例化false。最终约34.49GiB可用磁盘。
6. **代表轨迹**：无新模型轨迹。部署smoke只执行training task565参考动作，不作为训练样例或模型成绩。Day3与原始dev仍保留隔离。
7. **路线结论**：无卡准备完成，可以进入GPU采集；准备好的LoRA入口限定8更新，数据审核和完整性门槛仍须实际通过。
8. **未支持**：具体GPU硬件/模型加载兼容性、真实training成功率、质量批准数据、SFT loss/梯度/更新/重载与Agent收益均未实测。
9. **五处代码**：prepare_sft_model_files.main（固定配置→文件与辅助哈希）；verify_model_integrity.main（固定Hub元数据/文件→权重校验）；validate_sft_no_card.main（上传任务/真实tokenizer→CPU准备结果）；collect_training_probe.main（未来单GPU→真实training轨迹）；run_sft_probe.main（未来质量批准轨迹→8步更新/重载证据）。
10. **粗颗粒学习点**：环境准备与训练是不同阶段；真实训练数据要先采集审核；更新证据与Agent效果仍要分别验证。
11. **五个备用追问**：为什么无卡可下载权重但不加载8B？为什么导入PEFT不证明能反向传播？为什么首步LoRA部分梯度可能为零？为什么保存adapter后要重新加载base？为什么模型文件校验与trajectory来源校验都需要？无需答完才继续工程。
12. **下一步**：用户切回单GPU模式后检查实际显存/CUDA，执行training20→质量审核→8步LoRA probe；不再要求预算确认，不自动扩大S1/S2/DPO/RL。
13. **证据与费用**：最终远端代码4e5f9102aadf01eb35d6f852e496e466442a75d3；32文件准备包与35文件最终包各有回执，未覆盖历史。17文件证据归档SHA256为9814b5a13147f1fb7972abb3b49c3d32d9f2bd4e34ad05e87d3815764ddb80d3，保存在evidence/sft-remote。两次Python路径探查失败及一次no-card GPU查询异常永久记录；后续准备主流程退出码0，没有模型invalid run。无卡实例有运行时间，单价/实际费用未知，不能记成免费。没有API Key或SSH密码写文件或Git。

发布补充：自动权限审核在进程创建前拒绝了包含 GitHub push 的命令，要求明确同意本批实验记录/元数据的外部披露。没有执行推送，没有改用其他渠道规避；本地保存与无卡准备不受影响。用户需切回GPU模式以继续实际采集；发布授权作为独立问题处理，不是训练门槛。准备后台进程已退出，SSH helper 已正常关闭，实例保持用户选择的无卡模式。

后续授权和结果：用户在上述范围说明后明确要求“用github传文件”，随后同一GitHub push获批并成功，不是绕过拒绝。官方接口核实仓库private；远端无GitHub登录导致匿名clone失败，未改变执行目录。最终用已有本地Git登录向GitHub取得临时固定ref文件链接，远端直接下载20文件，SHA256和Git blob一致。回执evidence/sft-remote/github_sync_receipt.json，脚本scripts/github_file_sync.py；账号凭据不发送远端，链接不写文件/日志。代码传输改为GitHub；模型、venv和既有training20保持原状。无新增实验ID或模型能力结果。
