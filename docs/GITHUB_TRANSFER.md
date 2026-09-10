# GitHub 文件同步约定

2026-09-10 用户明确要求通过 GitHub 传文件。仓库为 `ycInfinite/VeriAgent-Workplace`，官方 GitHub 仓库接口核验 owner、读写权限与 private 可见性。

## 当前已完成

- 本地 `bc5aa55c3b97174822893c789b236cf5e43fcaf3` 已推送到 master。
- 执行主机直接从 GitHub 下载该 ref 的20个白名单文件，每个校验 SHA256 和 Git blob ID。
- `bundle_manifest.json` 更新 code_commit/transport；旧清单保存在远端 `logs/deployment_manifest_before_github.json`。
- 权重、虚拟环境、官方工具/CSV和已固定training20不变。没有下载dev/final案例到执行目录。
- 本次为文件同步，没有模型推理、参数更新或新模型评测。

## 私有仓库怎样同步

远端没有 GitHub 登录，首次匿名 clone 因不能读取用户名失败。没有改为公开仓库，也没有给远端存账号 token。

`scripts/github_file_sync.py` 使用本地已有 Git 凭据管理器，只向 `api.github.com` 的指定仓库 Contents API 请求固定ref文件信息；本地 Git blob 再次核对。GitHub 返回的短期 raw-file 链接通过无PTY、不回显的 SSH 标准输入交给远端进程；账号凭据不离开本地与 GitHub 的认证链路，链接只在内存/进程环境中短暂使用，不写命令行、文件、日志或回执。

远端直接从 `raw.githubusercontent.com` 下载文件，先在临时目录完整验哈希，再更新执行白名单。下载阶段失败时不会把未校验内容部署。执行目录已有文件必须符合上一次部署清单，否则停止，避免覆盖不明修改。回执只保留路径、ref和哈希。

## 后续操作

1. 本地实现、检查、commit，再 push 到指定仓库。
2. 使用完整 commit hash 调用同步 helper，不能将浮动 master 当作实验身份。
3. helper 通过隐藏提示获取用户已提供的 SSH 密码；密码不写脚本。SSH 主机指纹继续固定校验。
4. 检查新回执和执行清单，再启动已授权范围内的实验。

当前文件白名单取自已验证的 `evidence/sft-preparation/bundle-4e5f9102.json`；增加新的执行依赖时先更新可审查白名单，不能直接同步整个仓库到训练环境。

模型权重仍从固定官方模型源下载并在远端保留。公开个人项目的代码、配置、学习材料与已授权实验证据可以提交；凭据、缓存、权重以及未授权或封闭数据不进入 Git。

回执：[GitHub 同步证据](../evidence/sft-remote/github_sync_receipt.json)。首次 clone 失败：[准备尝试记录](../evidence/sft-remote/github_transfer_attempts.jsonl)。此失败是传输认证问题，不是模型 invalid run。
