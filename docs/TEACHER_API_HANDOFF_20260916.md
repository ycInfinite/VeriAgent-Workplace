# 百炼教师采集入口：已通过 CPU 检查，等待无卡实例

2026-09-16。用户确认普通按量API可用，并提供北京工作空间Base URL；实际URL保存在 `configs/teacher_acquisition_plan.json`，不是密钥。Token Plan不用作采集渠道。用户在聊天贴出的密钥没有复制进代码、文件或日志；已建议撤销换新，接入使用远端终端隐藏输入。

## 已完成

- 新采集器 `scripts/collect_teacher_probe.py`：只加载CPU环境和学生tokenizer，不加载8B权重，不启动训练。
- `veriagent/teacher_rollout.py`：普通API的HTTPS请求、真实工具执行、状态变化、官方verifier及独立replay、完整消息/usage/错误留证。密钥只用于Authorization header，不记录header/环境，不打印HTTP错误正文；拒绝跳转到其他端点，不自动重试。
- `configs/teacher_acquisition_plan.json`：八字段实验卡及固定边界。20题/B1/seed42、每题最多6轮、每次最多768输出tokens、每题最多2048输出tokens、学生8192序列上限、整个采集进程1800秒。供应商usage与学生重编码tokens单独统计，二者不能互换。
- `scripts/github_file_sync.py --include-teacher`：原执行白名单新增且只新增4个教师执行文件；权重、venv、dev/final均不传、不覆盖。仍从GitHub固定commit下载并核对哈希。
- 无网络CPU审计 `TEACHER-COLLECTOR-CPU-20260916-001`：代码commit `16a36e9`，55/55检查通过。仅重放旧training707作为fixture，真实执行官方工具并核对最终状态；不把它视作教师输出、不批准旧数据。

55项包含：20题wire schema逐项相等、20题请求字段白名单、普通workspace端点、拒绝套餐/外站/带凭据URL、usage缺失拒绝、真实状态/replay/动作一致、所有旧轮次保留、截断工具调用不执行、401只尝试一次且费用未知、错误JSON算policy失败而非infra、关闭thinking契约。

当前教师请求=0、新模型轨迹=0、质量批准=0、参数更新=0。API对本账号的真实响应格式/严格schema兼容性尚未测试；CPU通过不替代API试运行。此前已有的SFT准入没有被放宽；API教师数据审核通过后，还需显式接上canonical教师格式的训练准入，不会从采集器自动启动8步更新。

## 远端交接

本轮通过AutoDL页面重新确认：新PRO6000和旧A800均已关机。按AGENTS约定，不自动开机。下一步需要用户允许将**新PRO6000实例以无卡模式启动**，无需启动GPU。

开启后由Codex通过GitHub同步固定提交，保存新的sync receipt，先执行：

```bash
cd /root/autodl-tmp/veriagent-workplace-sft-20260910
.venv/bin/python scripts/collect_teacher_probe.py --preflight-only
```

通过后，用户在该实例的真实终端执行以下命令。命令不含Key，shell历史也不会包含Key；程序看到隐藏输入提示后再粘贴普通按量API Key并回车。不要使用 `echo Key`、命令参数、`.env`、shell配置文件或截图分享Key。

```bash
cd /root/autodl-tmp/veriagent-workplace-sft-20260910
.venv/bin/python scripts/collect_teacher_probe.py \
  --run-id TEACHER-ACQUIRE-20260916-001 --prompt-key
```

这是候选未使用ID；真实执行时先确认目录不存在并按当天日期登记，不能重用/覆盖。程序先完成无Key预检，随后隐藏输入；获取Key后才创建正式实验目录并开始有界采集。运行中保持终端连接，Codex可通过另一SSH连接读无密钥的progress/result。采集后撤除进程环境中的Key，完整轨迹进入审核，GPU仍无须启动。

首个请求是固定20题的第一题，不额外加一批smoke，不按成绩换题。发生API/网络/usage契约错误即停止，原始响应或安全错误类型永久保留；后续修复应新登记ID、说明重复任务的费用和曝光，不自动重试。

## 尚未建立的证据

普通API访问/余额/模型权限未实测；HTTP响应里的model标签也不等于开放权重commit。工具schema的strict字段被原样放入兼容API的function对象，不能为了跑通静默删改。若服务端拒绝现有schema，保留无效run，再说明并登记兼容性处理。实际费用按usage估算，未知失败请求费用为null，不冒充0；缓存/免费额度不预扣。

## 官方接口来源

2026-09-16核验：[Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)、[兼容Chat接口](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)、[计费渠道说明](https://help.aliyun.com/zh/model-studio/more-tools)。HTTP请求中的enable_thinking置于body顶层；保留工具结果和多轮历史。官方文档可变，无可固定的公开commit。
