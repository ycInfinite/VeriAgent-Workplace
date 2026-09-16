# 首次真实 LoRA SFT 完整性与成本探针

## 结论

`SFT-PROBE-20260916-001` 完成8次真实LoRA参数更新，CE/梯度/参数变化/冻结参数抽样/保存重载检查全部通过。首次建立了“完整真实教师轨迹 → 学生chat template/labels → CE → LoRA update → adapter保存重载”的实测证据。

这不是正式S1/S2实验，也未进行训练后的可执行Agent评测。固定输入的贪心读出仍出现无依据ID，因此不能声称学生已学会grounding或任务成功率提高。

## 执行与身份

- 用户因旧A800/PRO6000均无库存，明确要求另找有卡实例。暂停旧库存heartbeat后，选北京B904 `kl7wef5luq-6927b33c`，RTX PRO6000 Blackwell Server Edition单卡，实际可用显存94.97296GiB，单价6.98元/小时。
- 通过AutoDL克隆原PRO6000的系统盘和数据盘；源实例与旧A800保留，不付费扩容。42个部署文件和5个模型分片哈希核对通过，BF16测试正常。
- 通过GitHub部署固定提交 `0a7eba87b1d2fe04320ee67803951e4af6169295`，27个执行白名单文件身份一致。GitHub网络失败保留为部署记录，未重复教师采样或训练。改进本地同步器：复用与GitHub目标blob及SHA完全一致的文件，只下载差异；不降低校验。
- 学生 `Qwen/Qwen3-8B`，revision `b968826d9c46dd6066d109eabc6255188de91218`。
- 数据 `nvidia/Nemotron-RL-agent-workplace_assistant` revision `c86a908379e0a361a573c395e175d3c1aa128e6c`；Gym commit `83b3980b9c04379d72bbf59592d7846630f706bf`。
- Torch2.8.0+cu128、Transformers4.56.2、PEFT0.17.1、Accelerate1.10.1；单卡BF16、SDPA、non-reentrant gradient checkpointing。
- 运行开始身份时间 `2026-09-16T06:25:06.175441+00:00`；实际optimizer更新8次，成功run1个，训练invalid run0个。

## 八字段登记

| 字段 | 本次内容 |
|---|---|
| Research Question | 单卡能否对已批准完整轨迹完成8步可信LoRA更新并一致重载？ |
| Hypothesis | CE一致、梯度有限非零、adapter实际变化、冻结参数抽样不变、重载一致 |
| Independent Variable | 8次更新前后权重；没有与不同数据选择法对照 |
| Controlled Variables | 固定学生/数据/模板、707和965整轨迹、seed42、rank16/alpha32、lr5e-5、microbatch1、8K上限 |
| Metrics | CE差值、梯度、trainable count、adapter变化、reload、步时、显存、GPU-hours、费用 |
| Evidence Gate | 8步有效，来源/mask门槛通过，权重更新与重载证据完整 |
| Cost Bound | 1卡、8步、1800秒进程；按6.98元/小时最多3.49元进程费，迁移等待另记 |
| Failure Branch | 失败保留并停止，不增加步数/模型/context，不自动进入S1/S2、DPO或RL |

## 数据与监督完整性

选用真实教师采集 `TEACHER-ACQUIRE-20260916-001` 中707（CRM，3轮）与965（项目管理，5轮）两条完整质量批准轨迹。共8个per-turn样本，各用于一次更新；未从失败前缀里挑正确片段。审核由Codex完成，尚无独立人工复核。

processed tokens=35972，supervised tokens=582，最长单轮序列4741。每轮真实历史消息、工具观察及non-thinking prefill作为context，labels=-100；完整可见assistant动作/回答及EOS作为目标。教师输出使用固定学生tokenizer重新编码，不冒充教师或学生当时的采样token IDs。

实际Transformers模板/prefix IDs与CPU编码一致；canonical teacher target IDs也检查一致。16项负向准入检查在CPU阶段已通过。没有dev/final/BFCL样本进入训练。

## 原始训练结果

| 项目 | 实测 |
|---|---:|
| trainable参数 | 43,646,976 |
| optimizer更新 | 8 |
| 首步manual CE与model CE绝对差 | 0.0 |
| 首步非零梯度张量 | 252 |
| 后续各步非零梯度张量 | 504 |
| 发生变化的adapter张量 | 504 |
| 冻结基座参数抽样 | 前后一致 |
| adapter重载logits最大绝对差 | 0.0 |
| 重载greedy token IDs | 完全相同 |
| 8步时间总计 | 11.9063秒 |
| 平均step time | 1.4883秒 |
| 整个probe wall time，含加载/保存/重载 | 33.4939秒 |
| GPU-hours，进程范围 | 0.00930387 |
| 进程费用估算 | 0.064941元 |

| step | task/turn | supervised tokens | CE loss | 秒 |
|---:|---|---:|---:|---:|
| 1 | 707/1 | 47 | 1.480040 | 1.963516 |
| 2 | 707/2 | 79 | 0.508133 | 1.437087 |
| 3 | 707/3 | 44 | 1.387484 | 1.437385 |
| 4 | 965/1 | 73 | 0.690268 | 1.420588 |
| 5 | 965/2 | 80 | 0.384239 | 1.303647 |
| 6 | 965/3 | 111 | 0.507280 | 1.426505 |
| 7 | 965/4 | 81 | 0.668645 | 1.448174 |
| 8 | 965/5 | 67 | 0.754665 | 1.469367 |

这8个loss来自不同样本，不能把首尾差或排序当作同一任务的学习曲线。首步只有一半LoRA梯度张量非零与B零初始化相容，不代表A永远不学习；后续504个张量有非零梯度。

冻结检查只覆盖每个冻结参数的固定抽样，不能扩大表述成整份基座内存逐字节校验；基座磁盘模型5个分片在运行前做了完整SHA校验。

## 资源与费用口径

- peak training allocated：26.5315GiB。
- peak training reserved：58.0918GiB。
- nvidia-smi sampled used峰值：60175MiB，约58.76GiB。
- 30个采样点平均GPU utilization：47.7%，包括加载、训练、保存、重载等阶段，不是纯训练算子利用率。
- 本次实际硬件是PRO6000 96GB；不能据此声称A800已实测，或只凭allocated值断言小显存卡一定能运行。
- 0.064941元仅为33.4939秒probe进程费用，已包含在整机计费时间内，不能再与整机会话费相加。复制、SSH接入、GitHub重试和备份等待另包含在实例会话窗口；最终收尾见 `evidence/sft-probe/lifecycle_and_cost.json`，不是平台账单。
- 之前教师采集约4.978896元API费用属于前一实验，不是本次SFT模型API费；本次没有再次调用教师。

## 没有被支持的行为结论

保存/重载检查在同一个固定输入上生成了相同内容，但这不是Agent任务评测。该训练后读出的动作仍是：

```json
{
  "name": "customer_relationship_manager_update_customer",
  "arguments": {
    "customer_id": "12345678",
    "field": "status",
    "new_value": "Proposal"
  }
}
```

初始输入没有提供这个ID，也还未执行lookup。这是单次贪心读出的grounding问题信号：不能宣称8步已经修好该行为；也不能把它计作完整trajectory失败，因为本次没有继续执行工具、恢复或verifier。没有同设置的训练前greedy读出作为对照，因此不能给出行为改善/退化幅度。

## 修改、证据与下一步

本轮新增替代实例授权/迁移记录、完整训练原始证据、adapter校验清单与学习交接；本地GitHub传输器增加哈希一致文件复用和无密钥错误类型诊断。训练程序执行的是固定提交0a7eba8，后续报告提交不代表重跑。

实验目录 `experiments/SFT-PROBE-20260916-001` 保留config、identity、training_examples、steps、adapter_changes、reload_check、gpu_samples、result、run_stdout、launch及verified_summary。证据包SHA256：`929b108499160b922a45007cd4e637512536153f6b717ba5f2abbe180c5b1b32`。原始结果没有改写。

adapter保留在远端实验目录的`adapter/`；本地Git排除目录 `checkpoints/SFT-PROBE-20260916-001/adapter/` 的3个文件、共174661796字节均已与远端SHA256匹配，见 `evidence/sft-probe/adapter_backup_receipt.json`。新904与旧两台全部确认关机，监控暂停。整机会话估算约4.58–5.04元至关机请求（完成延迟可能增加少量费用，非账单）；包含约0.065元probe进程费。权重不进入Git，Git仅保存校验元数据及不含权重的证据包。

下一阶段需要登记真实的小规模SFT学习实验及开发集Agent评测，再谈行为改善、S1/S2公平比较或DPO。此次8步完整性probe结束后停止，不自动增加训练轮数或追加评测数据。
