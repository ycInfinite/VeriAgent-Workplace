# CPU 复现与证据查看

日常学习优先查看已保存结果，不需要重新运行全部实验。

```powershell
.venv\Scripts\python.exe scripts/learning_lab.py --view trace
.venv\Scripts\python.exe scripts/learning_lab.py --view mask
.venv\Scripts\python.exe scripts/learning_lab.py --view rewards
```

全新机器复现时，先阅读 AGENTS.md。使用独立 venv，安装 `requirements-cpu.pinned.txt` 中的 CPU 依赖，再运行 `fetch_official.py` 与 `fetch_tokenizer.py`。网络只用于公开小型文件。下载器优先使用已提交的 revision 与 SHA256；校验失败时停止，不改成另一个 main，也不覆盖旧证据。仅在没有 tokenizer 配置的首次建项时才解析远端 main。

本次 Windows Python 3.14.6，具体版本见 Q0-CONTRACT 的 runtime_versions.json。依赖表是直接依赖 pin，不是完整平台/传递依赖锁定。跨平台需重做轻量 smoke check。

重新执行实验必须使用新的 run_id，例如：

```powershell
.venv\Scripts\python.exe scripts/audit_dataset.py --run-id YOUR-NEW-DATA-ID
.venv\Scripts\python.exe scripts/audit_environment.py --run-id YOUR-NEW-ENV-ID
.venv\Scripts\python.exe scripts/audit_tokens.py --run-id YOUR-NEW-TOKENS-ID
.venv\Scripts\python.exe scripts/audit_contracts.py --run-id YOUR-NEW-CONTRACT-ID
```

后续脚本默认引用本次已提交的 Q0-DATA 清单，目的是精确复查本次选择，不能假装自动跟随新的数据实验。改变清单要明确传入/修改 config 并记录 code identity。模型阶段只使用 `configs/model_qualification_plan.json` 指定的 SPLIT-003，尚无执行授权。

目录说明：vendor=未改动官方源码（Git 忽略）；data/raw=原始公开数据（Git 忽略）；data/tokenizer=无权重 tokenizer（Git 忽略）；experiments=本项目原始审计证据；docs/learning=学习与考核。不要将有脚本生产或 dev 标记的 fixture 当成训练集。

每个 Run 目录拒绝覆盖；registry 只追加事件。复现时检查 source manifest SHA、experiment identity 的 commit 和 script SHA、config、runtime，然后查看 raw JSONL，而不只看 result.json。
