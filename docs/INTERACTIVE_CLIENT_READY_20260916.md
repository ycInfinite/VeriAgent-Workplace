# Qwen Code 交互接入：实际完成情况

日期：2026-09-16。远端执行文件固定为 `318e23376f5f8358e52fa3dead81227021597fb1`，32个GitHub下载/复用文件哈希核验通过。

## 已完成

- 本地与904无卡实例安装官方 Qwen Code0.23.4、Node24.19.0及隔离MCP1.30.0；不改训练依赖、权重或旧采集器。
- 官方Node压缩包SHA256及Qwen npm完整性摘要已核验，安装记录在 `evidence/interactive-client/`。
- 实现单个固定training任务707的工具桥。只提供 `get_task`、`execute_workplace_tool`、`finish_task`；真实工具返回和状态变化会记录，参考答案不由接口返回。
- 程序回放通过18项CPU检查，包括真实观察一致、状态变更、官方verifier、训练池限制、六次工具调用上限及结束后禁止重开。
- Qwen Code管理命令和实际交互会话均显示 `workplace — connected`。
- 已在用户Edge浏览器的JupyterLab“Qwen - workspace”终端中打开真实交互界面。普通Codex侧栏终端未成功切换到受控SSH会话，因此改用可见网页终端交接。
- API Key仅由隐藏提示进入远端进程环境。此前SSH验收会话退出摘要显示0工具调用、API时间0秒；其11个配置/事件JSON文件未发现凭据模式，网页终端启动后的15个JSON/事件/日志文件也未发现凭据模式。没有把Key写入配置、Git或启动命令。

## 用户最后一步

已在 **JupyterLab → Qwen - workspace** 输入框填好下方草稿，尚未发送；你审阅后按回车即可亲自发起：

> 请完成当前这一个 Workplace 训练任务。先调用 get_task，依据任务和真实 observation 选择工具；完成后调用 finish_task 并停止。不要处理其他任务。

客户端可能要求批准MCP工具，请在交互界面中审阅。此过程由用户发起；Codex没有使用headless、SDK、PTY提示词队列或浏览器自动提交模型任务。

如果界面已过期，在904无卡实例终端运行：

```bash
/root/autodl-tmp/veriagent-workplace-sft-20260910/.venv/bin/python \
  /root/autodl-tmp/veriagent-workplace-sft-20260910/scripts/launch_interactive_client.py
```

凭据继续只在隐藏提示中输入，不贴聊天或shell命令。

## 边界与证据

配置请求8192上下文、non-thinking、单次输出256、网络重试0；客户端最多6轮、8次总工具调用（包含开始/结束），桥内最多6次Workplace动作。启动器30分钟后结束子进程。客户端自身可能存在附加提示、恢复或压缩机制，未做真实模型payload/token预算审计；若出现压缩/截断或额外调用，记录并停止，该轨迹不能直接用于本项目SFT。不能把这些设置当作已经实测的完整预算保证。

`.cache/interactive-client/client-events-*.jsonl` 保存客户端事件；`.cache/interactive-sessions/` 保存task、真实工具调用、观察、状态差异、终止和verifier。桥日志不包含全部模型内部上下文，因此始终保持 `training_eligible=false`。后续需要同时检查完整客户端记录、来源、grounding和学生编码，不能按reward=1直接入库。

本轮新增模型任务、已完成模型rollout、训练批准数据、参数更新均为0。尚未用实际推理请求验证套餐Key有效性、剩余额度或SFT数据质量。单任务交互开发准备已经完成；批量自动采集仍未接入Token Plan。

## 失败保留与修复

- CPU001：本地没有远端bundle中的training20文件；从既有bundle恢复精确文件并校验SHA256，没有读取validation/final内容。
- CPU002：MCP对象参数直接传给官方replay导致reward错误；在项目边界转成JSON字符串，未修改上游语义。原始reward与日志保留，不计模型失败。
- CPU003：18项通过。最初复制证据时session/audit文件同名，原session身份文件保留；原始audit身份从追加式registry恢复到 `audit_identity_from_registry.json`，完整工具结果另存 `session_result.json`。未删除或改写旧文件。
- 两次GitHub原始文件传输失败保留为operation事件；有限重试完成。未切换到直接SFTP传项目代码。
- Qwen Code首次读取配置增加 `$version`，触发安装器保护。只在核验原业务配置不变后应用新的、GitHub已登记的生成限制，保留CLI元数据和旧配置副本。

## 无卡费用与收尾

904无卡配置为0.5CPU/2GB，0.10元/小时，最低0.01元。AutoDL已确认 **2026-09-16北京时间17:15自动关机**。按约16:09启动到该时点估算约0.11元，非实际账单，不含存储；自动关机完成尚未观察。两台旧实例保持关机，GPU监控保持暂停。浏览器交互客户端留给用户，操作用SSH连接收尾后关闭。
