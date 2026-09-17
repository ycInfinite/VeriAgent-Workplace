# 从已采集 trajectory 到首轮 SFT

现在的阶段是：**SFT 数据与训练协议就绪，正式两组训练未开始。** 昨天的 8 步 LoRA 更新是真实实验；今天只是把新数据和下一轮训练、评估准备好，没有再次更新模型。

## 今天最值得理解的三个变化

第一，reward=1 只是其中一道门槛。完整看过 150 条后，137 条通过，13 条保留但暂缓。比如 task263 把任务 ID 拿去调用了日历查询，最终状态仍然成功；task83 最后选择的图是对的，但把四类流量总数算错了。把这些整条拿去 SFT，会同时教会模型中间的错误。

第二，首轮训练数据是两组各 50 个完整任务，每组有 155 个 assistant 决策轮次。完整轨迹拆成逐轮样本，**每个轮次都保留，每个样本都有该轮之前的完整历史**。这和“删掉错误轮次、只监督正确片段”不同。

第三，S1 随机选，S2 按此前真实 Base failure 选。S2 更集中地示范先查邮箱/实体、完整处理多个目标和范围条件。两组各域都是 10 题，更新次数相同；processed tokens 差 0.67%，目标 tokens 差 1.99%。这是近似匹配，不能说 token 完全相同。

## 代码一：一条 SFT 样本实际是什么

下面摘自真实实现 `veriagent/teacher_data.py → CanonicalTeacherEncoder.encode`，省略了断言和元数据：

```python
prefix = self.inspector.render(prefix_messages, tools, generate=True)
complete = self.inspector.render(
    prefix_messages + [assistant_message], tools, generate=False
)
suffix = complete[len(prefix):]
target_text = suffix[:-1]  # 去掉模板的分隔换行，保留 <|im_end|>
prefix_ids = tokenizer.encode(prefix, add_special_tokens=False).ids
target_ids = tokenizer.encode(target_text, add_special_tokens=False).ids

input_ids = prefix_ids + target_ids
labels = [-100] * len(prefix_ids) + target_ids
attention_mask = [1] * len(input_ids)
```

`prefix_messages` 是输入上下文，包括 user、此前 assistant 决策和真实工具 observation。`assistant_message` 是本轮要学的完整回答/工具调用。模型 forward 会处理全部 input_ids，但只用非 -100 的 labels 计算监督损失。mask 不意味着上下文不用计算。

一个实际导出的例子：task22、turn1，prefix=4,195 tokens，target=132 tokens。边界是：

| input位置 | token片段 | label |
|---:|---|---:|
| 4192 | 两个换行 | -100 |
| 4193 | `</think>` | -100 |
| 4194 | 两个换行 | -100 |
| 4195 | `I` | 40 |
| 4196 | `'ll` | 3278 |
| 4197 | ` help` | 1492 |

这里的空 non-thinking prefill 属于生成输入，保持 mask。不要看到 assistant 标记就把它之后所有模板 token 都当成模型当时生成的目标。

## 代码二：CE 为什么要错开一格

下面是准备好的真实训练入口第一步的检查；**本轮尚未在 GPU 执行它**：

```python
output = model(**batch, use_cache=False)
loss = output.loss

labels = batch['labels'][:, 1:]
mask = labels != -100
manual = F.cross_entropy(
    output.logits[:, :-1, :].detach()[mask].float(),
    labels[mask],
)
assert torch.allclose(manual, loss.detach(), atol=1e-4, rtol=1e-4)

loss.backward()
torch.nn.utils.clip_grad_norm_(trainable_parameters, 1.0)
optimizer.step()
```

位置 t 的 logits 预测位置 t+1 的 token。因此上面例子中，4194 位置的 logits 要预测 4195 的 `I`。4194 自己的 label 虽是 -100，它产生的 next-token logits 仍可以用于首个 assistant target。不要混淆“输入 token 的位置”与“这个位置预测的目标”。

`backward` 计算梯度，`optimizer.step` 才更新参数。这里只有 LoRA 参数 trainable，固定为 43,646,976；基础模型约 81.9 亿参数不进入 optimizer。每个样本一次更新，155 个样本 × 2 epochs = 每组 310 次更新。

## 代码三：完整轨迹怎么防止被悄悄修改

`veriagent/teacher_data.py → export_teacher_turns` 的关键检查包括：

```python
if review['trajectory_sha256'] != content_sha256(record):
    raise ValueError('review does not match this trajectory')

for turn in record['rounds']:
    # 必须与原始 API response 一致，不能换成事后改好的答案。
    assistant, finish, errors = assistant_from_response(turn['raw_response'])
    assert assistant == turn['assistant_message']
    # 每一轮的 context 必须接得上此前真实 messages。
    assert turn['input_messages'] == messages[:cursor]
    # 工具返回必须与实际 event observation 一致。
    # 然后重新用学生 tokenizer 编码并核对 ids/labels/token counts。
```

这一段是检查逻辑的缩写，完整实现还有 pool、模型/配置、API request hash、所有工具事件、token budget 和审核范围校验。正式 export 不允许只拿机械筛查标签充当语义批准。

本地已跑过 20 项核心 CPU 检查，包括故意篡改 provider、工具 observation、assistant response、mask、review hash 和 pool，确认都会拒绝；也确认旧 probe 的 8 轮、582 个 target tokens 仍保持原样。额外 3 项统计报告检查使用明确标记的 CPU 合成 fixture，不是模型评测成绩。

## 四个文件在 pipeline 中的作用

| 文件 → 函数 | 输入 → 输出 | 作用 |
|---|---|---|
| `prepare_sft_comparison.py → main` | 审核判断和原始轨迹 → 通过/暂缓清单、两组压缩样本 | 冻结数据选择和预算 |
| `sft_stage.py → load_inputs` | arm配置与固定文件 → 校验后的examples和310步顺序 | 阻止混入dev/未审数据或改变目标 |
| `run_sft_comparison.py → main` | 已批准执行的arm → LoRA adapter、loss/梯度/显存/重载证据 | 真实参数更新；当前未运行 |
| `evaluate_sft_comparison.py → main` | Base或合格adapter → 新的真实Agent trajectories/reward | 检验模型自己决策、执行工具后的能力；当前未运行 |

SFT 本身使用已采集的真实轨迹做 teacher forcing，不会一边算 CE 一边执行这些工具。之后的 Agent Eval 才会让新权重重新选择工具、执行工具、看新的 observation 并继续决策。

## 下一步如何知道训练有没有用

固定相同 development24、两个seed42/43，对 BASE_B1、S1、S2 各跑48条。先看非空reference任务的成功，再看 typed grounding、参数/范围错误和提前停止。最终 checkpoint 固定，不用这24题挑epoch。

这些开发任务被用过做failure分析，共享初始数据库也可能让模型记住ID。即使分数提高，仍不能自动宣称未见工具组合泛化。后续最终评估和BFCL继续封存；本轮先回答一个更具体的问题：在近似相同预算下，这两种数据选择能否改善当前开发任务上的行为？

## 今晚五个追问

1. 为什么 task263 最终成功，却没有被批准做整条 SFT？
2. 为什么 50 个任务会变成 155 个训练样本、310 次更新？
3. 为什么最后一个 context 位置的 logits 可能参与 loss，即使它自己的 label 是 -100？
4. S2 的数据特征分数高于 S1，为什么还不能说明 S2 训练后更好？
5. adapter 重载结果一致、训练 loss 下降、Agent success 提高分别证明什么？

本页不提供标准答案；学习考核尚未进行，也不作为实验执行门槛。
