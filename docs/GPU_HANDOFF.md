# 下一步单卡准备（尚未租用）

历史准备计划：用户后来提供实例并授权 Day 3，现已完成。实际结果和关机状态见 DAY3_REPORT.md、PROJECT_STATE.md；下文保留选型与准备时的判断，不代表当前还在等待实例。

用户已明确平台为 AutoDL，本轮严格限定 Day 3 的纯推理资格实验。继续本地准备与报价核验，学习/考核保留。尚未提供实例、单价或镜像，未启动任何远端付费操作，也没有运行模型。

## 建议选型

| 项目 | 建议 |
|---|---|
| GPU | Day 3 首选 1×RTX 4090 24GB；若实际显存 probe 不通过，再讨论 48GB 实例 |
| 分配 | 单张卡、推理并发 1；48 条 rollout 串行执行，模型只加载一份 |
| 系统 | Linux；优先平台提供、能明确固定版本的 PyTorch/vLLM 镜像 |
| CPU/RAM | 正常 GPU 模式约 8–16 vCPU，32GB RAM 起、64GB 更宽裕 |
| 存储 | 可用空间建议至少 100GB，用于权重、依赖、缓存和实验记录 |
| 计费 | 按量短租，明确小时价、存储/停机费用与释放方式 |

这些 CPU/RAM/disk 数字是本项目工程规划，不是实测最低配置。此前 80GB 选型偏向后续训练；针对用户再次明确的纯推理范围，改为 24GB 优先。使用原始 Qwen3-8B BF16，不为节省显存自动换成量化权重。固定 8192 context、max_num_seqs=1，优先 eager 模式做第一次显存 probe；不并行加载两个 policy，也不常驻训练/reference 模型。初次显存测量未通过时先停并诊断，不自动量化、扩大预算或改卡。

由固定模型 config 估算，BF16 参数约 16.4GB，单序列 8192 tokens 的 BF16 KV cache 约 1.2GB；还需 runtime/activation/workspace。此估算支持尝试 24GB 单并发，不是 24GB 已运行通过的证据。见 evidence/planning/q0_gpu_memory_estimate.json。

硬件来源（2026-09-04 核验）：[NVIDIA RTX 4090 24GB](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/)。后续 SFT/DPO 仍按单卡 80GB 设计，不将本轮推理可行性推导成 24GB 训练可行性。

## AutoDL 无卡模式准备

2026-09-04 官方文档说明：无卡模式为 0.5 核、2GB RAM、无 GPU，0.1 元/小时；切换模式保留实例数据，但无卡模式会释放 GPU，不保证之后有空闲卡。[官方说明](https://www.autodl.com/docs/save_money/)

1. 先核对候选 4090 实例价格、镜像和可用磁盘。尽量使用平台可直接无卡启动的流程；若创建时需要正常启动，完成后及时切换，不假定创建过程零 GPU 费用。
2. 在无卡模式传项目、固定 dev 清单与官方工具源码；不传本地 Windows .venv，不把 BFCL/最终验证数据送进开发流程。
3. 权重下载在取得远端准备授权和访问方式后进行，只下载固定 revision 的分片并流式校验；控制下载并发，不在 2GB RAM 中拼接/加载模型。
4. 优先现成兼容镜像和预编译 wheel。无卡模式可做轻量安装/检查；CUDA 验证、源码编译及大内存步骤不能承诺在此模式完成。
5. 文件/配置准备好后，再批准切换 GPU 模式，做显存及工具协议 smoke check，再审核 48 条 B0；B1 仍只按预登记条件触发。

无卡模式不是免费。扩容存储可能另外计费，以实例页面为准。它也不是 GPU 预留服务。实际镜像/驱动信息尚未提供，所以暂不指定一个声称已经兼容的 vLLM/CUDA 安装组合。

## 实际付费前还需要的外部信息

平台已确定为 AutoDL。还需候选实例的完整 GPU 型号/显存、单价、CPU/RAM/disk、镜像列表。可提供截图或公开页面。不要把账号密码、API key 或 SSH 私钥发到聊天；后续连接方式单独配置。

现在没有平台报价，不能把早先的 p=10 元/小时占位当成现价。预计超过 RMB 30 的单次实验仍须明确确认，完整 pilot 的 RMB 80 只是候选额度，不是租用授权。

## 首次上卡分为两个证据阶段

第一步是三个 development tasks 的加载/工具协议 smoke check，验证模型真的生成调用、工具真的执行、观察能传回以及日志/计量可靠。它只判断管线能否运行，不据此估计成功率。通过后才提交 24-task B0 正式资格实验；不自动执行 B1 或训练。

| 实验字段 | 首次 smoke check 草案 |
|---|---|
| Research Question | 固定 Qwen policy 能否通过当前接口完成真实 tool call/observation 循环并记录使用量？ |
| Hypothesis | 在有限 context 下，模型加载、解析、执行和记录链路可用 |
| Independent Variable | 当前固定模型端点；无模型/框架 sweep |
| Controlled Variables | 固定 revision、三个 dev IDs（0、1、205）、schema、初始状态与官方时钟 |
| Metrics | 加载时间、tool-call 解析/执行、observation 回传、tokens、latency、VRAM、费用 |
| Evidence Gate | 有真实模型调用证据，基础设施错误与 policy 错误可区分；随后审核是否进入 B0 |
| Cost Bound | 待实际平台价格计算；首轮以不超过 RMB 30 为设计目标，超出先获批 |
| Failure Branch | 保存失败日志并定位，不自动扩大 context/模型/卡数；不启动完整 pilot |

这不是把一个昂贵实验拆单规避审批：smoke 的问题是链路可用性，B0 的问题是 policy operating regime，二者分别提交完整 cost bound。

24-task 计划见 `configs/model_qualification_plan.json`，使用 SPLIT-003。严格 composition generalization 仍未合格，模型资格测试不能被宣传为该门槛已通过。

## 可直接交给远端机器的只读检查

```bash
python scripts/gpu_preflight.py
```

该脚本只读取设备、版本和可用磁盘，不下载权重、不加载模型、不跑 GPU workload、不读取环境密钥。输出用于检查配置，不能替代实际模型 smoke check。

不要把本地 Windows 的整套 venv 拷贝成 Linux GPU 环境。收到镜像/驱动信息后再固定 serving 依赖，避免照搬 CPU 的 Python/NumPy 版本或在租卡时临时试多个框架。
