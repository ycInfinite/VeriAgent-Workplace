# 第五课：第一次 LoRA SFT，从模型前向到真正更新参数

2026-09-10。你已说明 Day 3 前的内容基本掌握，希望进入 SFT。本课直接向训练模块推进，不再逐题复习环境和 tool call。旧考核未评分，不把“未评分”设成继续学习的障碍。

本课是供手机与 GPT 阅读的独立材料，代码与解释都在这里。**代码是为讲解编写的示例，尚未执行，不是已通过验证的项目 trainer。** 本次没有安装训练依赖、加载模型或更新参数。模型执行证据仍停在 Day 3。

## 1. 你现在要走的 SFT 阶段

| 子阶段 | 要解决的问题 | 完成标志 |
|---|---|---|
| SFT-A：训练机制 | SFT 优化什么，LoRA 改哪里，一步更新怎样发生 | 能解释下面的 forward → loss → backward → step |
| SFT-B：数据与实现准备 | 用什么训练轨迹，怎么选目标、组织 batch、控制 token | 合格 training-pool 数据与可审查 trainer；关键模板问题解决 |
| SFT-C：完整性与 cost probe | 参数真的更新了吗，重载对吗，单卡多贵 | 梯度、权重变化、重载和实际资源证据 |
| SFT-D：S1/S2 对照 | 数据选择策略是否改善实际 Agent 行为 | 同预算 random / failure-targeted SFT 与独立评测 |

我们现在进入 **SFT-A 的学习与 SFT-B 的方案理解**。开始 SFT 学习不要求先证明所有研究假设成立。实际训练前仍要处理 baseline、training 数据质量、评测切分和四个 prefill tokens 的实现问题。

## 2. SFT 与 LoRA 分别回答什么

SFT 是训练目标：给定示范上下文，增加示范中目标输出的概率。LoRA 是参数更新方式：冻结原有的大矩阵，在选定层加上较小的可训练矩阵。两者可以组合成“用 LoRA 做 SFT”；后面的 DPO 也可以用 LoRA 更新参数。

以一个线性层为例，使用列向量记法：

```text
原线性层：          y = W x
加入 LoRA 后：      y = W x + (alpha / r) B A x

W: [d_out, d_in]，原有权重，冻结
A: [r, d_in]，可训练
B: [d_out, r]，可训练
r: rank，低秩维度
```

在 `d_in=d_out=4096，r=16` 的例子中，W 有 16,777,216 个数，而 A+B 有 `16×4096 + 4096×16 = 131,072` 个数。冻结 W 后，只为小矩阵维护训练参数相关的梯度和优化器状态。但整个模型仍参与前向，激活和计算成本没有消失。

下面是**只解释线性层数学的教学代码**，不含 dropout、量化、adapter 管理等工程功能。它不用于替代 PEFT：

```python
import torch
from torch import nn

class TeachingLoRALinear(nn.Module):
    def __init__(self, base_linear, rank=16, alpha=32):
        super().__init__()
        self.base = base_linear
        self.base.requires_grad_(False)

        self.A = nn.Linear(base_linear.in_features, rank, bias=False)
        self.B = nn.Linear(rank, base_linear.out_features, bias=False)
        self.A.to(device=base_linear.weight.device,
                  dtype=base_linear.weight.dtype)
        self.B.to(device=base_linear.weight.device,
                  dtype=base_linear.weight.dtype)
        nn.init.zeros_(self.B.weight)
        self.scale = alpha / rank

    def forward(self, x):
        original = self.base(x)
        correction = self.B(self.A(x)) * self.scale
        return original + correction
```

PyTorch 的 Linear 接收最后一维为输入特征的张量，所以实际调用看起来是 `B(A(x))`。`base.requires_grad_(False)` 冻结原层；A/B 默认可训练。此处 B 初始化为零，因此初始 correction 为零，模型从原有函数开始调整。

PEFT 的默认 LoRA 初始化同样令 B 为零；标准缩放为 alpha/r。特别初始化或 rsLoRA 等变体不是本例。一个容易误判的细节是：**B=0 时，第一次反向传播的 A 梯度可能为零，而 B 已经有梯度。** 所以不能要求第一步每一块 LoRA 张量都出现非零梯度；要看整体证据和后续变化。[PEFT LoRA 官方说明](https://huggingface.co/docs/peft/v0.20.0/package_reference/lora)

## 3. 用 PEFT 将 LoRA 接到实际模型

下面假设 `base_model` 已由未来获批的训练入口按固定模型 revision 加载。本课不提供自动下载、租卡或开训命令。示例 rank、alpha 和 learning rate 都用于理解代码，尚未被选为正式超参数。

```python
from peft import LoraConfig, TaskType, get_peft_model

def attach_lora(base_model):
    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,
        lora_alpha=32,
        lora_dropout=0.0,
        bias="none",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )
    model = get_peft_model(base_model, config)
    return model
```

`target_modules` 指定哪些模块加入 adapter，不是训练样本的 target。q/k/v/o 属于 attention 投影；gate/up/down 属于前馈网络。这里的模块选择是明确示例，不意味着覆盖越多越好。

`get_peft_model` 会在原模型上包装目标层。做 S1/S2 时要分别从同一份干净 base 加载，再加新 adapter，不能在已经训练过 S1 的模型上直接接着当 S2 起点。[PEFT 配置与模型说明](https://huggingface.co/docs/peft/guides/peft_model_config)

接完后应检查真实可训练参数，而不是只相信配置里写了 LoRA：

```python
def inspect_trainable_parameters(model):
    trainable = []
    frozen_count = 0
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            trainable.append((name, tuple(parameter.shape), parameter.numel()))
        else:
            frozen_count += parameter.numel()

    return {
        "trainable": trainable,
        "trainable_count": sum(size for _, _, size in trainable),
        "frozen_count": frozen_count,
    }
```

结合项目固定 Qwen3-8B config，36 层、上述七类线性模块、rank16、无额外可训练模块时，解析期望为 **43,646,976 个 LoRA 参数**。这是结构计算，不是已经加载 PEFT 测出的结果。未来应逐模块核对名称、形状和数量，若不一致先解释原因。Day 3 的 trainable count=0，因为当时纯推理。

## 4. SFT 的前向为什么不用一边生成一边调工具

Day 3 rollout 的过程是：模型生成动作，工具执行，再将 observation 放回下一轮。**离线 SFT 的训练样本则已经包含采集时真实执行过的交互。** 一次训练 forward 读取保存好的序列，用其已知历史预测后续示范 token，这叫 teacher forcing。

```text
采集阶段：policy → 生成 action → 真实 tool → observation → 继续
SFT 阶段：已有轨迹 → 对示范 token 计算概率与 loss → 参数更新
评测阶段：更新后的 policy → 再次真实生成、执行工具、评分
```

训练 forward 本身不需要重新执行邮件发送工具，但采集记录中的 observations 必须来自可信的真实执行。评测时也不能继续喂训练轨迹里的答案，要让新 policy 自己决策。

Teacher forcing 下，模型看到的是示范前缀，容易与自由 rollout 的状态分布不同：训练时看过正确查到 ID 的上下文，推理时却可能第一次就猜错 ID。这是为什么 loss 下降不能直接证明 Agent success 提升，也是恢复数据可能有价值的原因。

当前已经保存的 75 条是 dev，不能作为正式训练集。SFT-B 需要从 training pool 获得新轨迹；不能直接把不含 prerequisite lookup 的官方 reference 当成完整专家对话。

## 5. 从样本到 batch：这里只要求明确接口

前面的模板/mask 概念作为已学基础。本课假设每条训练记录已经通过来源与质量检查，得到：

```python
# 教学接口，不是真实任务，也不是完整数据文件。
record = {
    "input_ids": [101, 205, 306, 407],
    "labels": [-100, -100, 306, 407],
}
```

这些四位编号是假设 token，用于展示形状，不是 Qwen 的真实编码。下列 collator 展示右侧 padding 和 mask 的配合，**不解决轨迹序列化、EOS、前缀或截断的资格问题**：

```python
import torch

def collate_audited_records(records, pad_token_id):
    if not records:
        raise ValueError("Empty batch")
    max_length = max(len(r["input_ids"]) for r in records)
    if max_length < 2:
        raise ValueError("No next-token training positions")

    ids, labels, attention = [], [], []
    for record in records:
        length = len(record["input_ids"])
        if length != len(record["labels"]):
            raise ValueError("input_ids/labels length mismatch")
        if not any(x != -100 for x in record["labels"][1:]):
            raise ValueError("No supervised next-token targets")
        padding = max_length - length
        ids.append(record["input_ids"] + [pad_token_id] * padding)
        labels.append(record["labels"] + [-100] * padding)
        attention.append([1] * length + [0] * padding)

    return {
        "input_ids": torch.tensor(ids, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
        "attention_mask": torch.tensor(attention, dtype=torch.long),
    }
```

三组张量都是 `[batch_size, max_length]`。attention_mask 的 0 表示填充位置；labels 的 -100 控制哪些位置不贡献直接监督损失。不要混淆这两种 mask，也不要为了统一长度截掉关键 observation。

项目已有四个 forced-prefill token 的问题仍要在 collator 前解决。上述函数接收“已审计 records”，并没有自动修复它。正式数据入口必须检查 training-pool 归属、轨迹 producer、verifier、过程质量和完整性；`training_eligible=true` 一个布尔值不足以代替这些检查。

## 6. 一次真正的 SFT 参数更新

这是本课最重要的代码。它是**自编教学示例，未执行**：假设 `model` 已加 LoRA、已放在指定单卡上，`batch` 已通过上一节审计并移动到同一设备。示例按 BF16 路径理解；不是 FP16 GradScaler 或梯度累积的完整实现。

```python
import torch

def make_optimizer(model):
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise ValueError("There are no trainable parameters")
    # 教学示例值，正式配置尚未确定。
    return torch.optim.AdamW(parameters, lr=1e-4, weight_decay=0.0)

def one_sft_update(model, optimizer, batch):
    model.train()
    optimizer.zero_grad(set_to_none=True)

    # labels 未手动 shift；指定模型的标准 loss 路径内部负责 shift。
    output = model(
        input_ids=batch["input_ids"],
        attention_mask=batch["attention_mask"],
        labels=batch["labels"],
        use_cache=False,
    )
    loss = output.loss
    if loss is None or not bool(torch.isfinite(loss).item()):
        raise ValueError("Invalid loss")
    if not loss.requires_grad:
        raise ValueError("Loss is disconnected from trainable parameters")

    loss.backward()

    gradient_norms = {}
    for name, parameter in model.named_parameters():
        if parameter.requires_grad and parameter.grad is not None:
            gradient = parameter.grad.detach().float()
            if not bool(torch.isfinite(gradient).all().item()):
                raise ValueError("Non-finite gradient")
            gradient_norms[name] = gradient.norm().item()
    if not any(value > 0 for value in gradient_norms.values()):
        raise ValueError("No nonzero trainable gradient")

    optimizer.step()
    return {"loss": loss.detach().item(), "gradient_norms": gradient_norms}
```

按执行顺序理解：

| 代码 | 具体做什么 | 此时是否已更新权重 |
|---|---|---|
| `model.train()` | 切换训练行为，如 dropout；不负责开启全部参数训练 | 否 |
| `zero_grad()` | 清掉上一更新周期积累的梯度 | 否 |
| `model(..., labels=...)` | 前向得到 token 分布，按目标计算 CE | 否 |
| `loss.backward()` | 沿计算图把 loss 对参数的导数累计进 `.grad` | 否 |
| `optimizer.step()` | 按优化规则使用梯度修改参数 | **这一步才发生参数更新** |

`model.train()` 与 `requires_grad` 是不同机制。训练还不能被放在 Day 3 的 `torch.inference_mode()` 外壳里，否则不会建立所需梯度图。冻结基础权重，不等于把整个模型前向放进 no_grad；后者可能切断 adapter 所需的梯度传播。[PyTorch 自动微分说明](https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html)

当前固定 Day 3 版本 Transformers 4.56.2 的 Qwen3 forward 在提供 labels 时调用 loss_function；其标准 causal-LM loss 内部处理 next-token shift。因此这个示例传原位置 labels，不能再提前 shift 一次。未来训练版本仍需单独锁定和核验。[Qwen3 v4.56.2 源码](https://github.com/huggingface/transformers/blob/v4.56.2/src/transformers/models/qwen3/modeling_qwen3.py)、[对应 loss 源码](https://github.com/huggingface/transformers/blob/v4.56.2/src/transformers/loss/loss_utils.py)

这里还省略了 gradient checkpointing、累积、梯度裁剪、OOM 恢复、资源监测和实验落盘。正式 8B cost probe 必须补齐适当实现并实测，不能因这段代码短就假设其显存开销小。尤其长序列的 logits 和 loss 计算可能占显存。

## 7. 怎样证明参数真的变了

只看 loss 不够。下面示例在 CPU 保存可训练参数副本，比较一步前后的最大绝对变化。它用于小型 probe 审计，会有额外复制开销，不应无条件每一步都全量记录。

```python
def snapshot_trainable(model):
    return {
        name: p.detach().cpu().clone()
        for name, p in model.named_parameters()
        if p.requires_grad
    }

def compare_trainable(before, model):
    after = snapshot_trainable(model)
    if before.keys() != after.keys():
        raise ValueError("Trainable parameter identities changed")
    return {
        name: (after[name].float() - before[name].float()).abs().max().item()
        for name in before
    }

# 未来 probe 中的调用顺序，本文未执行：
# before = snapshot_trainable(model)
# stats = one_sft_update(model, optimizer, batch)
# deltas = compare_trainable(before, model)
```

这能检查 adapter 变化，不能凭它独立证明冻结权重全都未变。正式 probe 还应对冻结权重做适当的前后完整性检查，并核对 optimizer 只包含获准训练的参数；如果只抽样哈希，要明确证据仅为抽样。

应区分几种常见故障：

- loss 有值、`requires_grad=False`：梯度被禁用或没有可训练路径。
- 有梯度、参数没有可见变化：检查是否调用 step、学习率、优化器参数列表和数值精度。
- 参数变化、任务没提高：更新发生了，但训练目标、数据覆盖或泛化可能有问题。
- 第一步某些 A 梯度为零：结合 B 的零初始化分析，不要立即断言训练断了。

## 8. 保存、重载与继续训练不是同一件事

LoRA adapter 必须与其训练时的 base 配套。PEFT 可以单独保存 adapter；重载需要正确基础模型与配置。[PEFT quicktour](https://huggingface.co/docs/peft/main/quicktour)

```python
from peft import PeftModel

def save_and_reload_for_eval(model, fresh_base, output_dir):
    # fresh_base 由调用者按同一 base revision 加载。
    model.save_pretrained(output_dir, safe_serialization=True)
    reloaded = PeftModel.from_pretrained(
        fresh_base,
        output_dir,
        is_trainable=False,
    )
    reloaded.eval()
    return reloaded
```

示例接口要求 `fresh_base` 是新加载的干净 base，不是再次传入被 get_peft_model 改造过的旧对象。单卡正式实现可先保存验证输入与 logits，再释放原模型、加载新模型，避免两份 8B 同时常驻；不能从这段接口推断显存足够。

重载检查应固定输入、模板、dtype、设备和 eval 模式，比较有容差定义的 logits；greedy 输出也可辅助检查。只看一句相同回答太弱；随机采样输出不同也不直接证明重载失败。

adapter 文件可用于恢复模型推理，但**完整继续训练**还可能需要 optimizer、scheduler、随机状态、训练 step 和数据顺序。不能把 save_pretrained 自动等同完整训练恢复点。

## 9. 为什么第一次 cost probe 不是 S1/S2 正式结果

第一次训练 probe 的研究问题是“训练管线和资源预算是否合格”，重点检查完整性与成本。少量 training-pool 样本上 loss 下降，只能支持实现诊断；如果用重复样本过拟合检查，也必须标为诊断，不能报告泛化提升。

以下是**教学用实验卡草案，尚未登记或执行**：

| 字段 | 草案 |
|---|---|
| Research Question | 固定 8B policy 的单卡 LoRA SFT 是否能正确更新、保存、重载，并在预算内执行？ |
| Hypothesis | 模板/目标对齐后出现有限 CE、有效梯度和 adapter 变化；重载一致；资源开销可接受。 |
| Independent Variable | 参数更新前与更新后；不是比较不同数据选择策略。 |
| Controlled Variables | 固定 base revision、合格 training 子集、共同 prompt、token 上限、adapter 配置、seed 与验证输入。 |
| Metrics | processed/supervised/padding tokens；loss；梯度与权重差异；重载误差；peak VRAM、step time、GPU-hours、RMB。 |
| Evidence Gate | mask 与 per-turn 条件检查通过；更新发生在预期参数；保存重载通过；成本有实测依据。 |
| Cost Bound | 先据实际设备报价和短步测量制定上限；单次预计超过 30 元仍需明确确认；本卡不构成开训许可。 |
| Failure Branch | 数据质量不足、目标对齐失败、无梯度、重载错误、OOM 或超预算时，保留证据并停止扩大。 |

正式配置、软件版本、样本 ID、步数、学习率和最大 wall time 要在执行前补全。当前无法把尚未测出的 SFT step time 写成费用事实。

probe 通过后才回答核心对照：S1 与 S2 均从相同 base 和共同质量门槛出发，主要区别是数据选择规则；同时比较相同口径的训练预算、Agent success、失败类别和成本。不会只凭 training loss 选出“更好的 Agent”。

## 10. 本项目进入实际训练前还有哪些决定

你可以现在继续学这些机制；以下是工程上的待办，不要求先回去做所有旧复习题：

1. 确定后续共同 baseline prompt；B1 当前是有条件候选，不能悄悄替代成已充分合格。
2. 从 training pool 取得可信且覆盖弱项的轨迹，明确高质量成功/recovery 的标准。Day 3 dev 不转成训练集。
3. 冻结评测边界与组合泛化口径，避免训练后按结果挑 held-out。
4. 在实际 trainer 中解决模板、四个 forced-prefill token、每轮条件与 EOS/padding 的对齐。
5. 固定软件版本与实际设备，登记完整 probe 配置和预算后再执行。

当前研究工程仍处于 Q0 资格收尾和训练准备之前；本次明确向前推进的是 **SFT 学习模块**。并未运行本课的任何模型或训练代码。

## 11. 今晚怎样和 GPT 学

可将本文件单独交给 GPT，并附上：

```text
Day 3 前的内容我已基本理解，请直接从本课的 SFT/LoRA 开始。
我只用手机，不能打开仓库。每次带读一个代码块，解释张量形状、
输入输出、哪些参数冻结、哪些参数更新，以及这一步会留下什么证据。
优先讲第 2、3、6、7、8 节，不要重新从 state/tool 的定义讲起。
教学代码均未运行，不要把它当成已完成的项目实验。
我解释不清时再补对应基础；一次只追问一个问题。
```

读完应能回答下面五题，暂不附答案，也不预判通过：

1. SFT 与 LoRA 为什么不是两种互斥方案？如果 W 冻结，输出为什么还能改变？
2. `model.train()`、`requires_grad=True`、`backward()`、`optimizer.step()` 分别负责什么？
3. 为什么默认 LoRA 第一次 A 的梯度可能为零，不能简单按“所有 adapter 梯度都非零”判合格？
4. 一份 loss 下降的日志还缺哪些证据，才能说明真实更新、重载正确和 Agent 改善？
5. 离线 SFT 不在每步执行工具，为什么仍可以训练真实 tool-using Agent？评测时又必须做什么？

## 12. 来源与检查范围

官方资料访问日期：2026-09-10。LoRA/API 示例参考 PEFT quicktour、配置文档与 v0.20.0 LoRA 说明；这不代表已选择 PEFT 0.20.0 作为项目训练版本。自动微分参考 PyTorch 官方教程。Qwen3/CE 行为核验到 Transformers **v4.56.2 tag**，不是声称跟随最新版。正式训练仍需登记所安装版本及解析后的源码身份。

本地项目依据：`docs/TRAINING_FEASIBILITY.md`、`configs/tokenizer.json`、`evidence/day3/serialization_alignment_note.json` 与既有 Day 3 原始记录。Qwen 模型 revision 为 `b968826d9c46dd6066d109eabc6255188de91218`。43,646,976 是本地固定结构与示例 rank 的理论参数数；本文没有实测参数、loss、梯度、显存或训练速度。

阅读顺序从“LoRA 改哪里”开始，接到一次真实 update 应有的证据，再进入数据和正式对照。需要基础查阅时才回看 [复习合订本](2026-09-08-return-to-project.md)。
