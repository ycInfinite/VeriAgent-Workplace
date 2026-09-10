# 2026-09-10：无卡准备已完成

发布状态：本地与远端准备产物已保存。GitHub 推送被自动权限审核拒绝，组合命令未创建进程；审核要求明确同意本次实验记录/元数据的披露范围。推送前已检查214个文件，未命中凭据模式，模型权重排除。此发布问题不影响切换GPU后的实验推进；未换渠道重试推送。

用户提供新的个人 AutoDL 无卡实例，并明确免除本轮金额审批门槛。当前单卡、固定 8B、20 条采集和 8 次 LoRA 更新范围不扩大；无卡准备期间未加载模型、初始化 CUDA 或更新参数。未知单价与费用记为 null，不写成免费。

## 远端已完成

工作目录：`/root/autodl-tmp/veriagent-workplace-sft-20260910`。SSH 入口和密码不存入仓库。实例初始资源为 0.5 CPU、2GB RAM、50GB 可用数据盘；结束时约 34.49GiB 可用。

| 项目 | 实测结果 |
|---|---|
| 固定 Qwen3-8B 权重 | 5 个分片，共 16,381,516,776 bytes |
| 权重完整性 | 对固定官方 Hub revision 的独立 SHA256，5/5 一致 |
| tokenizer/config 完整性 | 4/4 与既有固定哈希一致 |
| 训练候选任务 | 20 个，仅 training_candidate，五域各4 |
| 远端 Transformers 模板和 token IDs | 20/20 匹配本地固定清单 |
| CPU 工具 smoke | training task565 的脚本参考动作 reward=1，状态变化与 reset 检查通过 |
| 训练相关导入 | Torch、Transformers、PEFT、训练入口导入通过 |
| CUDA 初始化 / 模型实例化 / 参数更新 | false / false / 0 |

工具 smoke 是脚本环境检查，不是生成的训练轨迹或模型成绩。PEFT 导入通过也不代表 GPU backward、显存和 adapter 重载已验证。

独立 `.venv` 复用镜像的 `torch 2.8.0+cu128`，安装 `transformers 4.56.2`、`peft 0.17.1`、`accelerate 1.10.1`、`tokenizers 0.22.2`、`pandas 3.0.3` 等固定依赖；没有重装全局 PyTorch。候选 PEFT 依赖要求核验自其 [v0.17.1 官方 setup.py](https://github.com/huggingface/peft/blob/v0.17.1/setup.py)，访问日期 2026-09-10；GPU 组合兼容性仍需实测。

## 接下来的实际顺序

1. 用户在 AutoDL 将实例切回单 GPU 模式。准备阶段没有通过未核实接口切换实例或规避 no-card GPU 权限。
2. 核对实际卡型、显存与 CUDA。BF16 LoRA probe 按 80GB 级单卡准备；当前代码要求至少 70GiB 设备显存，避免误在 24GB 配置上启动。
3. 执行固定 training20 的 B1 候选采集：seed42，20条上限，1800秒进程上限，8K/6轮/2048累计输出保持不变。
4. 复核成功轨迹的 grounding、目标范围、完整性与所有监督轮次，生成明确署名的质量审核记录。至少两个、最多四个不同任务；不足时报告分叉，不改题或自动追加采样。
5. 运行 `run_sft_probe.py`：rank16、alpha32、七类投影、microbatch1、8次更新；核对第一步手工/模型 CE、有效梯度、adapter变化、冻结参数抽样与保存重载。只做完整性/cost probe，不自动进入 S1/S2。

固定输入 greedy 输出用于重载身份核对，不计 Agent success。冻结权重检查是每个冻结张量的抽样指纹，不声称是所有冻结元素逐一比较。原始训练数据、质量审核和配置随 probe 保存。

以下命令仅是 GPU 可用、数据与审核通过后的入口说明，不在无卡模式执行：

```bash
cd /root/autodl-tmp/veriagent-workplace-sft-20260910
# 先采集。首次实际执行时登记未使用过的 immutable run ID。
.venv/bin/python scripts/collect_training_probe.py --run-id <ACQUISITION_RUN_ID>

# 采集和明确质量审核完成后，先只验证数据准入：
.venv/bin/python scripts/run_sft_probe.py --run-id <SFT_PROBE_RUN_ID> \
  --trajectories experiments/<ACQUISITION_RUN_ID>/trajectories.jsonl \
  --reviews <QUALITY_REVIEW_JSON> --validate-only

# 通过后才以同一数据/审核路径执行实际 probe（去掉 --validate-only）。
```

命令中的尖括号是待登记值，不是已发生的实验 ID。按用户预算覆盖，小时单价可缺省；所有 token、wall time、GPU-hours 仍记录，费用缺数据时为 null。进程时限不会自动关闭 AutoDL 实例；GPU 工作结束后的实例生命周期另外处理。

## 代码、失败记录与证据

最终部署包代码 commit：`4e5f9102aadf01eb35d6f852e496e466442a75d3`。35 个载荷逐项哈希匹配。包 SHA256：`517db248550dcea9a7ee9bbfa5871fc7d0aa27fbe77456cb8b86d2187afd0e0e`。此前包与其回执全部保留，未发生模型 run。

初始环境探查遇到两次 Python 路径不存在，以及一次 no-card 下 nvidia-smi 权限错误；改用镜像已有的绝对 Python 路径并记录 GPU 不可访问，没有绕过权限。准备记录保存在 `evidence/sft-remote/setup_attempts.jsonl`，不计为模型失败。依赖安装、固定下载、权重校验和 CPU 检查主流程退出码为 0。

证据归档 SHA256：`9814b5a13147f1fb7972abb3b49c3d32d9f2bd4e34ad05e87d3815764ddb80d3`；17 个证据文件取回并逐项验证。日志没有包含 SSH 密码或 API key；模型权重只在远端保存，不上传 Git。

- [准备摘要](../evidence/sft-remote/preparation_summary.json)
- [权重校验](../evidence/sft-remote/remote/model_integrity.json)
- [远端 CPU 检查](../evidence/sft-remote/remote/logs/no_card_validation.json)
- [训练导入检查](../evidence/sft-remote/remote/logs/training_import_check.json)
- [首次 LoRA probe 配置](../configs/sft_probe_plan.json)

学习只需抓住：文件和依赖准备好 ≠ 模型训练完成；下一步先得到可信的 training 轨迹，再检查第一次真正的参数更新。
