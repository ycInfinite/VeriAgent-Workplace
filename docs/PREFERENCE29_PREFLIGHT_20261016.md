# 累计29对偏好数据：训练前资格检查

本轮范围：实际HF编码与mask、最长完整pair的SFT/DPO前反向计算、下一轮对照方案。没有optimizer更新，没有新rollout/API，没有打开sealed评测。实例按用户要求保持开机。

执行前八字段协议保存在 `configs/preference29_preflight.json`，run ID为 `PREF29-PREFLIGHT-20261016-001`。执行代码固定在GitHub提交 `a0a5e5e`。正式29对训练方案单独保存为 `configs/preference29_comparison_proposal.json`，状态为PROPOSED_NOT_EXECUTABLE。

## 检查为何必要

29对包含58条完整轨迹、179个assistant回合：chosen83、rejected96。训练输入是每个assistant回合连同其完整历史；system/user/tool观察的labels为−100，完整assistant输出为目标。chosen共9856目标tokens，rejected共11609，合计846778 processed tokens。这不是把179个回合截成179道独立任务。

最长chosen为6365tokens，最长rejected为8073tokens，均来自task358；按长度预先选择这一对，不看更新后的模型成绩。只需保留一个回合计算图，完成反向后释放，再进入下一回合。DPO先计算两个分支总log-probability与链式求导系数，再逐回合重算并反向。七项小模型Torch控制用于核验它与直接求导等价。

本轮不创建optimizer、不执行step、不保存新adapter。对504个LoRA张量逐一比较，冻结基座只做参数抽样；原始adapter文件另外校验完整SHA256。梯度经过clip也不等于参数更新。

## 后续对照的具体设计

- 两组都从原始S1开始，不接着旧6对DPO权重训练。
- 只用29个reward-gap pair；4个same-reward pair继续隔离。
- 一轮、每任务一次更新，共29次；固定SHA256任务顺序、seed42、lr5e−6、context8192。DPO beta0.1、参考策略固定原始S1。
- chosen-only组对完整chosen的目标token平均CE反向；DPO组使用两个完整分支的sum-logp差。相同chosen曝光和更新数，不能说等tokens、等FLOPs或等GPU时间。
- 若进入执行，先登记新的训练及评测ID，再做同主机S1/chosen-SFT/DPO固定dev24×两个seed，共144条。仅看最终29次更新，不用dev挑checkpoint或调参。
- 主指标为非空reference任务的DPO−chosen-SFT成功率，另报整体与空reference，并重新语义审核空reference。dev已多次使用，不能当作最终泛化成绩。

29对覆盖五域但不均衡：analytics15、calendar7、CRM2、email3、PM2；14空reference、15非空。1069/956的reference相同，属于相关样本。数据扩充之后仍是小样本探索，不预设DPO必定提升，也不因训练loss下降宣布有效。

## 边界

最长序列检查不证明所有29对更新过程稳定；本轮没有AdamW状态、实际step或新adapter重载。不能把本轮反向耗时标为DPO update time，也不能据96GB运行成功宣布80GB可用。后续执行仍须记录完整更新、资源峰值和保存重载检查。

本轮本地配置生成曾有一次Python括号语法错误，解析阶段即停止、没有生成配置或模型调用；修正后通过静态检查，原失败记在 `evidence/preference29-preflight-20261016/local_preparation_failure.json`。

## 实测结果

检查通过，假设得到本轮限定范围内的支持：179/179实际HF回合一致、7/7Torch控制通过，DPO与直接图梯度的最大差0、chosen-SFT梯度最大差0。98个GitHub执行文件哈希核验通过，原始9个模型/tokenizer文件和3个S1文件一致。

| 实测项目 | 结果 |
|---|---:|
| chosen完整分支反向 | 5.156秒 |
| 固定S1两分支reference打分 | 3.595秒 |
| DPO完整pair重算反向 | 15.723秒 |
| DPO初始margin / loss | 0 / 0.693147（ln2） |
| chosen/rejected重算logp差 | 0 / 0 |
| SFT / DPO原始梯度范数（clip前） | 0.5456 / 33.2957 |
| 峰值allocated / reserved | 22.515 / 27.730 GiB |
| 设备采样峰值 | 28.417 GiB |
| 全脚本墙钟 / GPU-hours | 51.072秒 / 0.01418664 |
| 设备利用率采样均值 | 46.52%，46个样本，包含准备/加载 |
| 参数更新 / 新rollout / 新API | 0 / 0 / 0 |
| 逐张量完全不变的LoRA张量 | 504 |

12个原始归档成员全部本地SHA256核验。进程已退出、GPU计算进程为空、SSH已关闭；没有关机或创建关机保护。小时价格未知，RMB为null。前阶段保存回执到本轮保存回执占用0.463731小时，含本地准备/GitHub等待；容器启动估计至本轮回执累计1.040917小时，包含前91题采集。它们与script时间是重叠窗口，不能相加；实例继续开机，后续占用继续累计。

正式模型检查无infra-invalid run。唯一新增无效操作为前述本地配置生成语法错误，发生在任何配置执行之前并已永久保留。

## 修改与证据

新增独立 `scripts/preflight_preference29.py`、两份preflight/proposal配置、显式GitHub三文件部署白名单，以及本轮原始实验目录和报告。旧6对/12对训练入口、已有adapter、29对数据内容均未修改。未来完整29对训练须使用新ID和新执行入口，不能重跑旧ID。

证据：`experiments/PREF29-PREFLIGHT-20261016-001/result.json`、`host_preflight.json`、`torch_controls.json`、`phases.jsonl`；`evidence/preference29-preflight-20261016/raw_manifest.json`、`local_integrity.json`、`resource_summary.json`。完整日志包含于SHA验证的raw.tar.gz。

下一步建议执行已保存的29对对照：原始S1 → chosen-SFT29步和DPO29步 → 同主机固定dev评测。工程估计全矩阵0.7–1.2 GPU小时加准备/回收，其中本轮无更新反向只是成本依据，不是正式step-time实测。是否收益仍未测。
