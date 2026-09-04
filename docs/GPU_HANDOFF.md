# 下一步单卡准备（尚未租用）

用户允许继续推进。当前继续免费准备、平台选型和报价核验；学习/考核保留。尚未提供实例或平台，未授权任何付费租用，也没有运行模型。

## 建议选型

| 项目 | 建议 |
|---|---|
| GPU | 1×A800 80GB；A100 80GB 也可，比较实际单价和可用镜像 |
| 分配 | 单张完整 80GB，核对不是较小 MIG 分片，也不是两张 40GB 的总和 |
| 系统 | Linux；优先平台提供、能明确固定版本的 PyTorch/vLLM 镜像 |
| CPU/RAM | 约 8–16 vCPU、64GB RAM；更多 RAM 非当前硬要求 |
| 存储 | 可用空间建议至少 100GB，用于权重、依赖、缓存和实验记录 |
| 计费 | 按量短租，明确小时价、存储/停机费用与释放方式 |

这些 CPU/RAM/disk 数字是本项目工程规划，不是实测最低配置。首次只做 Qwen3-8B inference qualification；80GB 是沿用后续单卡训练目标，不代表 8B 推理必须有 80GB。当前不必为更贵卡型加价。

硬件来源（2026-09-04 核验）：[NVIDIA A800 PCIe 80GB 型号文档](https://docs.nvidia.com/ai-enterprise/release-8/latest/infra-software/vgpu/reference/ampere-a800.html)、[NVIDIA A100](https://www.nvidia.com/en-us/data-center/a100/)。A800 还有 40GB Active 型号，不能只看“A800”字样。

## 实际付费前还需要的外部信息

个人租赁平台名称、候选实例的完整 GPU 型号/显存、单价、CPU/RAM/disk、镜像列表。可提供截图或公开页面。不要把账号密码、API key 或 SSH 私钥发到聊天；后续连接方式单独配置。

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

## 可直接交给远端机器的免费检查

```bash
python scripts/gpu_preflight.py
```

该脚本只读取设备、版本和可用磁盘，不下载权重、不加载模型、不跑 GPU workload、不读取环境密钥。输出用于检查配置，不能替代实际模型 smoke check。

不要把本地 Windows 的整套 venv 拷贝成 Linux GPU 环境。收到镜像/驱动信息后再固定 serving 依赖，避免照搬 CPU 的 Python/NumPy 版本或在租卡时临时试多个框架。
