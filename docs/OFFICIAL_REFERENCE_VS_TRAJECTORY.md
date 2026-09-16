# 官方数据能否直接用于SFT？

2026-09-16澄清：**官方数据可以用于训练，SFT示范不要求一定由模型生成。** 当前已完成probe的producer白名单只覆盖已审计的本地8B/API教师两种来源，是该实现与登记实验的门槛，不是理论上禁止官方/人工/脚本示范。此前只比较API与部署，没有充分说明reference重建路线。

## 当前官方文件实际提供什么

锁定数据revision `c86a908379e0a361a573c395e175d3c1aa128e6c` 的train文件已重新核对SHA。1255条记录的input都是system+user，ground_truth为工具参考动作列表；没有随input提供assistant调用和tool观察交错的完整交互。agent_ref是Agent实现引用，不是采样轨迹。

官方Gym `utils.is_correct`在新环境分别执行predicted与ground_truth，并比较五个最终状态表。因此ground_truth可以直接给出数据库ID以定义目标状态，无需包含获取该ID的查询过程。README的Collect trajectories命令是让用户运行Agent生成输出文件，不表示该文件已作为完整专家轨迹随任务数据发布。

例：training707要求把Kerry Moore改为Proposal。官方参考只有：

```python
customer_relationship_manager_update_customer(
    customer_id="00000046", field="status", new_value="Proposal"
)
```

问题中没有00000046。符合本项目grounding目标的完整示范还需要根据姓名查询、得到真实观察中的ID，再更新并确认。只重放上面的update可以得到执行结果，但不会自动补出前置查询决策。

把训练集ground_truth作为监督标签本身不叫泄漏；问题是直接监督缺少依据的ID跳转，可能鼓励固定数据库记忆而不是基于观察决策。把答案送进评测/rollout的可见输入，或把dev/final用于训练，才是另一个泄漏问题，不能混为一谈。

## 可以采用的路线

| 数据类型 | 合理使用方式 |
|---|---|
| 已发布的完整专家交互，含真实/可重放观察 | 核对版本、许可、质量和训练切分后，可直接SFT |
| 参数能从用户问题/工具文档确定的官方reference | 真实执行补齐观察，封装并审核为reference-derived示范；例如565的日期/指标/图类型不需隐藏ID |
| reference省略查询、分页、范围判断等过程 | 由人工、通用脚本或teacher补齐并真实执行；必须核验每个动作依据 |
| 当前policy失败分布或onlineRL数据 | 仍需真实policy rollout；官方答案/脚本不能冒充当前policy采样 |

重建示范要显式标注来源，不编造工具返回，也不宣称“官方原始完整轨迹”。若纳入后续训练，需另登记来源和准入规则，不能绕过现有producer检查或改写已经完成的probe。只可使用项目training pool，官方train中已经分给dev/validation/held-out的部分也不能训练。

建议后续先审计官方数据可直接复用/重建的比例，teacher用于需要补齐的复杂过程或恢复示范；这个比例与工程成本尚未实测。正式S1/S2比较还需控制数据来源分布，避免把来源差异混成选择方法收益。本次说明没有启动新采样、构造新训练集或更新参数。

来源：[NVIDIA官方数据页](https://huggingface.co/datasets/nvidia/Nemotron-RL-agent-workplace_assistant)、固定Gym源码与README；本地核对证据：`evidence/teacher-acquisition/official_reference_structure_20260916.json`。上述结论只针对本项目锁定文件，不断言所有官方数据都没有完整trajectory。
