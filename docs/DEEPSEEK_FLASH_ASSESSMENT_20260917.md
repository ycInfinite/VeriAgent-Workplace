# DeepSeek Flash 教师API性价比评估

核验日期：2026-09-17。用户改回普通API；以下按 **DeepSeek官方平台** 计算，不套用到百炼或其他转售平台。本轮没有模型调用、开机或训练。

## 判断

值得作为下一轮教师资格测试的优先候选。官方支持工具调用、多轮对话和显式非思考模式；价格足够低，适合本项目有限预算下的数据采集。Workplace完整轨迹合格率尚未测，不能先认定质量等于或超过此前qwen3.8-max。学生仍是Qwen3-8B，不需要为了教师另租GPU。

## 官方事实

当前调用名为`deepseek-flash`，文档对应DeepSeek-V4.1-Flash。旧`deepseek-v4-flash`名称会路由到新版本，不能把旧别名当成固定权重revision。Base URL为`https://api.deepseek.com`。来源：[当前中文价目表](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、[更新日志](https://api-docs.deepseek.com/zh-cn/updates/)。

单位均为人民币/百万tokens：

| 项目 | 空闲时段 | 高峰时段 |
|---|---:|---:|
| 输入，缓存未命中 | 1 | 2 |
| 输入，缓存命中 | 0.02 | 0.04 |
| 输出 | 4 | 8 |

高峰为北京时间周一至周五09:00–12:00、14:00–18:00，其余为空闲时段。价格以执行时官方页与账单为准。本次直开中文页面，不使用仍显示旧V4费率的英文搜索缓存。

[官方工具调用指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)给出程序化多轮调用方式；环境函数由调用方真实执行。[思考模式指南](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)说明默认开启thinking，Chat Completions需要显式传`thinking.type=disabled`，OpenAI SDK中放入`extra_body`。不能直接照搬百炼的`enable_thinking`字段，也不能以配置存在代替响应验证。

[缓存指南](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)说明前缀缓存自动启用、尽力而为；记录`prompt_cache_hit_tokens`和`prompt_cache_miss_tokens`，不预设某个命中率。

## 用本项目真实历史规模估算

历史`TEACHER-ACQUIRE-20260916-001`：20次尝试，跨80请求累计387,839输入/9,023输出tokens，15条完整质量批准。它们是Qwen教师的实际用量和产出，不是DeepSeek实测。

不计缓存，沿用同等token量：

- 20次尝试：空闲0.423931元，高峰0.847862元。
- 再假设同样75%完整合格率：300条合格数据约8.48–16.96元；1,000条约28.26–56.52元。
- 如果缓存token数恰好也与旧实验相同，20次约0.084–0.168元；仅作为缓存敏感性算例，不是预算保证。

旧Qwen实验按未折扣标价估算4.978896元。Flash在相同token量、均不计缓存时约低6–12倍；两者实际tokenizer、轨迹长度、缓存、成功率和账单不同，不能称作已实测的成本优势倍数。旧Qwen的实际缓存单价未核验。

这些估算不含CPU宿主、存储、审核工时和未知失败请求费用。研究成本应为全部采集支出除以完整质量批准数；不能只除以reward=1的条数。平台名义context1M不会改变本项目8K学生编码上限。

可复核计算：`evidence/teacher-acquisition/deepseek_flash_cost_20260917.json`。

## 下一步建议（未执行）

复用固定training20与B1，单独登记一次DeepSeek教师资格测试。首轮显式non-thinking，保留原六轮、8192学生上下文和单轨迹累计2048输出预算；分别记录provider与student tokens，不混用两种tokenizer。核验实际请求参数、响应模式、工具/状态、完整质量与费用，再决定扩大。按上次长度推算首轮模型费用不到1元，实际准备预算可留5元余量，但仍需先做接入和token覆盖检查。

如果完整合格率低，先分析失败类型；不自动加context、换大模型或连续调prompt。保留此前15条合格轨迹与交互示范，不为换教师而重做已完成的SFT完整性probe。没有在此次价格咨询中启用新采集器、请求Key或启动训练。
