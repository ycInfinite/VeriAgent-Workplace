# 2026-10-12 DPO 首次真实8步探针结果

DPO-PROBE-20261012-001完成8次真实LoRA更新并通过保存重载。这支持“轨迹级偏好训练链路可用”，不支持“Agent能力已经提高”：本轮没有新rollout、没有开发集任务评测，也没有online RL。

执行commit：`24fe95f5273955e153929e1d89318d8904a98b92`。用户提供新克隆实例并要求继续，授权证据单独存于 `experiments/DPO-RESUME-20261012-001/config.json`；旧probe配置里的 `GPU_training_authorized=false` 是准备阶段历史状态，原文件保持未改，不以改配置伪造授权。

## 问题、控制与实际执行

| 预登记字段 | 本轮 |
|---|---|
| Research Question | 固定S1 reference下，轨迹DPO能否正确更新/重载，并适配单卡成本？ |
| Hypothesis | 完整assistant目标、分支各自观察、同S1初始reference可产生正确偏好梯度。 |
| Independent Variable | 固定8对各1次DPO更新。 |
| Controlled Variables | Qwen3-8B b968826、S1 adapter、seed42、beta.1、lr5e-6、LoRA原配置、8K上限、dropout0。 |
| Metrics | 梯度等价、HF mask、reference分数、loss/margin、参数变化/冻结检查、重载、显存/耗时/GPUh。 |
| Evidence Gate | 实际Torch/HF/权重门槛通过后才更新；每步有限非零梯度、两遍logp一致；完成后保存重载。 |
| Cost Bound | 用户单96GB卡，8updates，脚本30min上限；额外2h资源保护，时价未知。 |
| Failure Branch | 失败永久保留并停止，不自动重复、扩大context/任务/模型或进正式矩阵。 |

实际顺序：克隆主机/S1资产核验→GitHub固定提交78文件同步、93项manifest→9个Base/Tokenizer SHA→真实Torch CPU梯度对照→全部12对75轮实际HF模板/ID/mask检查→加载S1→8对reference预计算→8次更新→保存adapter→重新加载比对。未安装新依赖，未下载新模型，未采集teacher。

主机 `autodl-container-hfpnyex2hv-0b57ffeb`，一张PRO6000 Blackwell Server Edition 97887MiB，driver595.71.05。Torch2.8.0+cu128/Transformers4.56.2/PEFT0.17.1/Accelerate1.10.1，与预登记一致。SSH指纹为首次连接观察值，未独立控制台认证。

## 原始结果

| 检查/指标 | 实测 |
|---|---:|
| 真实Torch CPU整图vs逐轮重算梯度max差 | 0 |
| 实际HF完整轮次检查 | 75/75 |
| 首对policy−reference相对margin | 0 |
| 首对DPO loss | 0.6931471805599453（log2） |
| 真实optimizer updates | 8/8 |
| 各轮无梯度评分vs反传重算logp max差 | 0 |
| 发生变化的LoRA tensor数 | 504 |
| 保存重载固定logit max差 | 0 |
| 保存前后固定greedy token IDs | 完全相同 |
| reference计算时间 | 17.9496秒 |
| 平均pair update时间 | 9.6444秒 |
| 脚本总wall time（含预检/reference/保存重载） | 131.1996秒 |
| 脚本GPU-hours | 0.03644435 |
| allocated峰值 | 20.7389GiB |
| reserved峰值 | 31.2793GiB |
| 设备采样used峰值 | 31.9658GiB |
| 121次GPU利用率采样均值 | 87.8926% |

训练时可训练参数门槛为43,646,976且仅LoRA；执行代码中的冻结参数抽样不变和原S1文件SHA不变门槛均通过。不是全Base逐元素差分审计。保存重载只在一个固定prefix上比对，不是全输入输出等价证明。

8步loss依次：0.693147、0.668270、0.661867、0.586796、0.531012、0.557798、0.454871、0.482744。**每步是不同任务**，不能把这些点画成同一题的学习曲线。第8对chosen logp从reference −102.4820到当前−103.0443（更低），rejected从−54.0354到−59.3698（降得更多），相对margin仍+4.7721。不能用margin正值宣称chosen绝对概率或任务正确率全面提高。

固定重载readout两次各生成64token，输出被长度上限截住，不是完整轨迹，没有真实执行其tool call，没有verifier成绩；它仅作相同输入下的adapter身份检查。

## Tokens和成本口径

固定8对共45个assistant轮次（chosen24/rejected21），单次完整经过processed204089、assistant targets3376。reference无梯度评分一次、当前policy评分一次、反传重算一次，共135个数据forward、processed612267/target曝光10128；不含HF CPU编码检查、固定重载prefill与2×64 greedy输出。无新Agent rollout或API token费用。

9.64秒是一个完整pair update，每对有多个assistant轮次；不能直接除以之前SFT单轮1.4秒就说DPO贵了固定倍数。当前仅验证8对、最长不超过已审5431的这一运行范围；显存约32GiB不构成80GB型号或8K全长资格证明。

脚本0.03644GPUh小于事前0.05–0.15估计。完整实例占用包括部署、验证、等待、权重回收，见shutdown收据；不能只报脚本成本。本机实际时价未知，人民币null，不复用历史单价。DPO的Cost per Verified Success仍未定义，因为没有Agent成功评估。

## 有效性、故障与保全

模型运行无invalid_run，8步一次完成，无重试。两项操作问题保留在 `evidence/dpo-execution-20261012/operational_events.json`：裸python不在PATH，改显式解释器；本地解包目录安全检查因Path.resolve异常停止，改用实际AGENTS.md所在目录重新锚定，19成员逐一hash验证后解包。均非模型能力失败，计入实例占用。

原始run目录含config/identity/weights/torch_cpu_controls/host_preflight/reference_scores/steps/adapter_changes/adapter_manifest/reload_check/result/gpu_samples。全部原始记录archive SHA：`7afdf59dbcd8caaac0e5c25f0809fb357e1c47d3cd230f83e3eaed5aa2189e15`。不在原始result中补写未记录的测量；事后分析单独在 `reports/dpo-probe-20261012/analysis.json`。

新adapter本地保存于 `checkpoints/DPO-PROBE-20261012-001/adapter/`（忽略目录，不进Git）。旧S1及所有SFT结果不覆盖。

## 路线结论

Hypothesis在本次完整性/成本范围内得到支持；Agent效果和DPO相对chosen-only SFT的额外价值尚未测。8步不是正式方法效果实验，不自动进入12对正式对照。

下一路线可选：固定同一S1起点，按现有12对准备chosen-only SFT与DPO的正式对照及dev24×42/43评估。两臂同任务/相同chosen曝光/同更新数，但DPO额外处理rejected/reference，需明确不是严格等GPU预算。还需完成正式对照runner与预登记，再由用户决定执行。若希望先采当前SFT的training失败，则是新增采集路线，不能用dev失败直接替代。

12对仍受teacher来源/长度与旧Base负样本偏差限制；没有专门正确no-op偏好对。sealed final/BFCL/composition未打开。新增工程框架没有带来证据，真正的下一问题是方法对比与行为变化。

## 最终生命周期收据

新adapter三文件SHA与远端manifest一致，19个原始archive成员全部校验。已执行官方关机、取消本次2h保护；旧SSH报SSHException并关闭，新连接无SSH banner。平台控制台/最终账单未独立核验。容器启动估计至关机请求0.31416227小时（约18.85分钟），项目首次观察至请求0.24397338小时。脚本只占0.03644435小时，其余含启动、部署、等待和回收；不能把网络慢产生的占用隐去。金额因时价未知保持null。旧监控未恢复，无活动SSH或本轮后台任务。
