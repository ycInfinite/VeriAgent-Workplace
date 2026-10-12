# 2026-10-12 学习交接：SFT规模与不操作数据对照已完成

今晚只需掌握三个问题：100条为什么不一定比50条好？不操作数据改变了什么？为什么reward=1仍可能错？下面代码直接来自项目，手机里读这份即可，不用开电脑。

## 1. 开始前与实际进度

开始前：S1/S2完成；S100与MIX100只有CPU准备，缺GPU。你提供新克隆PRO6000后，部署固定GitHub版本、检查实际Tokenizer和显卡、分别新建LoRA训练310步、各评估dev24×两个seed，回收两组adapter/原始记录，执行官方关机。620次真实参数更新、96条有效评估、0模型infra-invalid；没采新teacher、没做DPO/RL。

项目处于“SFT对照已完成，进入结果分析和下一阶段选择”，不是还在搭训练框架。DPO、严格组合泛化、sealed final/BFCL仍未完成。

## 2. 唯一变量、控制变量与原始结果

S100：原S1的50条加50条已审任务，100×1epoch；历史S1是50×2epoch。都310步、约143万processed tokens，但覆盖和重复次数一起变。还换了克隆主机/驱动，因此不是绝对纯净的单因素历史比较。

MIX100：S100中20条换为20条已审不修改任务，仍100题、五域各20题、310步。同一新主机，同Base/LoRA/学习率/训练seed、同dev24×42/43，processed和target比S100分别多1.3869%和1.3707%。它也移除了20条原行动任务，这个取舍要记住。

| 模型 | 总体成功 | 非空reference | 空reference |
|---|---:|---:|---:|
| BASE_B1（历史） | 15/48 | 9/40 | 6/8 |
| S1（历史） | 35/48 | 30/40 | 5/8 |
| S2（历史） | 33/48 | 31/40 | 2/8 |
| S100（今天） | 32/48 | 27/40 | 5/8 |
| MIX100（今天） | 40/48 | 32/40 | 8/8 |

不能说“多一倍数据一定更好”。同预算时100×1是更多题、更少重复；这次没有观察到S100优于S1。MIX总体比S100多8次成功，但非空也有3条退步。配对任务簇95%区间：总体+16.67pp [0,33.33]、非空+12.5pp [-5,27.5]、空+37.5pp [0,75]。空只有4个任务、两seed不能当8个独立任务。不能宣布显著优越或泛化。

## 3. 代表性轨迹：分清状态、证据、解释

正向task709：查询特定未来会议→Observation无会议→明确说没有需要删除的会议。MIX两seed都通过“有依据地不修改”。它仍然调用查询工具，所以不操作不是零tool call，而是不做不符合条件的写操作。

反例task385：用户要六周social总量高于direct时画图。MIX查询11月1–30日（只有一个月），seed42把结果求和说成28和101，真实观察总和69和182；seed43把总量比较偷换成哪边胜出的天数，天数还算错。它没有画图，官方reward=1；但关键推理错误。

反例task122：把周二错定位成2023-11-27，实际周二是11-28。不画图最终状态正确，不能证明查对了条件。

动作退步task684 seed42：用户要重新分配Nadia客户给Akira，MIX查了一些记录后却调用add_customer，编造Akira邮箱/电话，最后声称完成。工具schema合法不代表任务做对。

动作改善task918 seed43：S100无负责人筛选、生成未完成；MIX先查Carlos邮箱，再按负责人+In Progress查到00000086，更新为Backlog，真实回应完成。

Codex本轮新鲜审核16条空轨迹，无独立人工复核。两组官方5/8→8/8，但“完成且关键不修改判断有正确证据”都是4/8，“整条无观察到的错误/冗余”都是2/8。这是事后诊断，不替换官方reward，不把dev轨迹用于训练。

## 4. 五处真实代码：输入、输出、pipeline作用

### A. veriagent/teacher_data.py → CanonicalTeacherEncoder.encode

输入：过去的messages、tool schemas、当前完整teacher assistant消息。输出：学生Tokenizer下的input_ids/labels/attention_mask及长度、哈希。教师是另一个模型，所以目标必须按学生的chat template重新编码；不把教师token IDs当学生IDs。

```python
    def encode(self,prefix_messages,tools,assistant_message):
        if assistant_message.get('role')!='assistant':
            raise ValueError('Only a visible assistant turn can be a target')
        if set(assistant_message)-{'role','content','tool_calls'}:
            raise ValueError('Unspecified assistant fields require an explicit normalization policy')
        prefix=self.inspector.render(prefix_messages,tools,generate=True)
        complete=self.inspector.render(prefix_messages+[assistant_message],tools,generate=False)
        if not complete.startswith(prefix):
            raise ValueError('Canonical assistant prefix is not a continuation of the input')
        suffix=complete[len(prefix):]
        if not suffix.endswith('<|im_end|>\n'):
            raise ValueError('Unexpected canonical assistant termination')
        # The renderer adds a separator newline after EOS; it is not a policy target.
        target_text=suffix[:-1]
        prefix_ids=self.inspector.tokenizer.encode(prefix,add_special_tokens=False).ids
        target_ids=self.inspector.tokenizer.encode(target_text,add_special_tokens=False).ids
        if not target_ids or target_ids[-1] not in self.checked.eos_ids:
            raise ValueError('Canonical target lacks EOS')
        if len(prefix_ids)+len(target_ids)>self.max_context_tokens:
            raise ValueError('Canonical sequence exceeds bound; no truncation')
        if self.inspector.tokenizer.decode(prefix_ids+target_ids,skip_special_tokens=False)!=prefix+target_text:
            raise ValueError('Canonical encoding roundtrip mismatch')
        return {'input_ids':prefix_ids+target_ids,'labels':[-100]*len(prefix_ids)+target_ids,
            'attention_mask':[1]*(len(prefix_ids)+len(target_ids)),
            'prefix_tokens':len(prefix_ids),'supervised_tokens':len(target_ids),
            'processed_tokens':len(prefix_ids)+len(target_ids),
            'prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),
            'canonical_target_sha256':hashlib.sha256(target_text.encode()).hexdigest(),
            'student_model_revision':self.checked.model_revision,
            'format':'canonical_qwen_non_thinking_complete_visible_assistant_turn_v1',
            'teacher_token_ids_used':False,'training_eligible':False}
```

prefix包括系统/用户/以前assistant/tool observations，供本轮预测参考；当前完整assistant输出才作为target。所有前缀labels=-100，但input_ids仍包含它们，因此模型能读观察，观察本身不计CE。每个assistant轮次各自成为样本，保证一条合格轨迹所有完整assistant轮都被监督，而非只挑正确片段。processed包含重复历史上下文，target才是直接贡献loss的tokens；今天约145万processed不等于145万监督标签。

### B. veriagent/sft_stage.py → validate_example

输入：上一步的单轮example；输出True或抛异常。它在训练前拒绝mask、长度、pool或token计数错误。

```python
def validate_example(e,limit=8192):
    ids=e['input_ids'];labels=e['labels'];prefix=e['prefix_tokens']
    require(0<prefix<len(ids)<=limit,'Empty target,invalid prefix or over-context example')
    require(all(type(x)is int and x>=0 for x in ids),'Invalid token IDs')
    require(all(type(x)is int for x in labels),'Invalid label types')
    require(len(ids)==len(labels)==len(e['attention_mask']),'Unequal tensor lengths')
    require(labels[:prefix]==[-100]*prefix,'Context tokens must have labels=-100')
    require(labels[prefix:]==ids[prefix:],'Assistant targets changed or selectively masked')
    require(e['attention_mask']==[1]*len(ids),'Unspecified packing/padding mask')
    require(e['supervised_tokens']==len(ids)-prefix and e['processed_tokens']==len(ids),'Token counters mismatch')
    require(e['training_eligible'] is True and e['source_pool']=='training_candidate','Nontraining input')
    return True
```

attention_mask=1表示这些token都参与注意力，不代表都要算loss；labels=-100才控制监督。这两种mask不要混淆。开发集可以做诊断编码，但training_eligible不通过就不能进入训练。

### C. scripts/run_sft_mixed.py → main中的训练循环

输入：冻结cfg、example列表、310步order以及Base+LoRA。输出：adapter、每步loss/梯度/token/耗时证据。以下是实际循环片段，省略的是前面的加载和后面的文件写入。

```python
        write(out/'identity.json',identity);torch.cuda.reset_peak_memory_stats();model.train()
        for number,item in enumerate(order,1):
            ex=examples[item['example_index']]
            batch={k:torch.tensor([ex[k]],dtype=torch.long,device='cuda') for k in ['input_ids','labels','attention_mask']}
            optimizer.zero_grad(set_to_none=True);torch.cuda.synchronize();tick=time.perf_counter()
            output=model(**batch,use_cache=False);loss=output.loss
            require(loss.requires_grad and torch.isfinite(loss).item(),'Invalid loss/graph')
            delta=None
            if number==1:
                labels=batch['labels'][:,1:];mask=labels!=-100
                manual=F.cross_entropy(output.logits[:,:-1,:].detach()[mask].float(),labels[mask])
                delta=abs(manual.item()-loss.item())
                require(torch.allclose(manual,loss.detach(),atol=1e-4,rtol=1e-4),'Manual/model shifted CE disagree')
                del manual,labels,mask
            loss.backward();grads=[p.grad for p in trainable.values() if p.grad is not None]
            require(grads and all(torch.isfinite(g).all().item() for g in grads),'Nonfinite/missing gradients')
            nonzero=sum(g.count_nonzero().item()>0 for g in grads);require(nonzero>0,'Zero adapter gradient')
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),cfg['max_grad_norm'],error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize()
```

因果语言模型当前位置logits预测下一个token，所以logits去末位、labels去首位。mask排除-100，手算CE和模型loss相等才说明监督位置一致。backward算梯度，optimizer.step真正更新参数。310步loss下降也不能代替环境评估：loss回答模仿教师有多接近，task success回答模型自己行动是否完成任务。

本轮每组可训练43,646,976参数，504个LoRA tensor变化，冻结参数抽样不变；首步CE差0，每步梯度有限且非零。不是只写配置或保存空adapter。

### D. scripts/run_sft_mixed.py → main中的readout与重载

输入：更新后的policy和固定prefix；输出logits/greedy IDs，保存adapter后重新加载再比较。以下为原始代码，base()复用固定模型权重。

```python
        write(out/'adapter_changes.json',changes)
        model.gradient_checkpointing_disable();model.eval();ex=examples[0];prefix=ex['input_ids'][:ex['prefix_tokens']]
        fixed={'input_ids':torch.tensor([prefix],device='cuda'),'attention_mask':torch.ones((1,len(prefix)),dtype=torch.long,device='cuda')}
        def readout(policy):
            with torch.inference_mode():
                logits=policy(**fixed,use_cache=False,logits_to_keep=1).logits[0,-1].float().cpu()
                ids=policy.generate(**fixed,max_new_tokens=min(64,8192-len(prefix)),do_sample=False,use_cache=True,
                    pad_token_id=tokenizer.pad_token_id)[0,len(prefix):].tolist()
            return logits,ids
        expected,expected_ids=readout(model);adapter=out/'adapter';model.save_pretrained(adapter,safe_serialization=True)
        hashes={f.name:sha(f) for f in adapter.iterdir() if f.is_file()};write(out/'adapter_manifest.json',hashes)
        del optimizer,trainable,before,model;gc.collect();torch.cuda.empty_cache()
        reloaded=PeftModel.from_pretrained(base(),adapter,is_trainable=False);reloaded.eval()
        actual,actual_ids=readout(reloaded)
        reload_ok=torch.allclose(expected,actual,atol=cfg['reload_atol'],rtol=cfg['reload_rtol']) and expected_ids==actual_ids
        write(out/'reload_check.json',{'passed':reload_ok,'max_logit_abs_diff':(expected-actual).abs().max().item(),
            'expected_ids':expected_ids,'reloaded_ids':actual_ids,'interpretation':'Identity only,not Agent evaluation'})
```

两组max logit差都为0、greedy IDs一致，只证明这条固定读出下保存重载正确。之后仍要让重载policy真实生成tool call、执行工具、改变状态并过verifier。今天每组48条评估是这一步，不能省略。

### E. scripts/compare_mixed100_evaluations.py → main中的task-cluster统计

输入：两组完成后的同task_uid/seed原始轨迹；输出分层均值、配对差值、bootstrap区间。前面的代码还检查模型配置/数据/执行代码是否一致。

```python
    for label,ids in [('all',uids),('nonempty',[u for u in uids if groups['S100'][(u,42)]['reference']]),('empty',[u for u in uids if not groups['S100'][(u,42)]['reference']])]:
        scores={arm:np.array([sum(rows[(u,s)]['verifier']['official_reward']==1 for s in [42,43])/2 for u in ids]) for arm,rows in groups.items()}
        delta=scores['MIX100']-scores['S100'];ix=np.random.default_rng(20260917).integers(0,len(ids),(10000,len(ids)))
        report['strata'][label]={'taskclusters':len(ids),'rates':{k:float(v.mean()) for k,v in scores.items()},
            'MIX100_minus_S100':float(delta.mean()),'taskcluster95CI':np.quantile(delta[ix].mean(axis=1),[.025,.975]).tolist()}
```

先把同一任务两个seed平均，再抽任务下标ix，这样保持任务内相关性。只有4个空任务时，区间很宽很正常；不要为了让区间变窄把两个seed当独立任务。两个模型还必须配对相同题目，不能一个模型换更容易的题。

## 5. 已支持结论与尚未支持推测

支持：两组真实更新/重载/环境评估完整；MIX这批开发题官方状态结果优于S100；减少了部分不该发生的修改，task385是例子。

未支持：100条一定足够或已经饱和；MIX比例最优；可靠条件推理改善；完全没有“该做却不做”的伤害；S2稳胜S1；未见工具组合或BFCL泛化。dev使用次数增加，也会产生研究者适配，最终sealed结果仍不能提前声称。

## 6. 资源、故障与证据导航

本轮GPU脚本0.638604小时；容器启动估计到关机请求1.015973小时，差额包含部署、等待、回收。时价未知，RMB unavailable，不填0。S100/MIX平均step1.408/1.432秒；allocated峰值32.136/33.381GiB，reserved88.209/90.998GiB，设备采样used88.896/91.685GiB。不能用allocated数字断言A80080GB必定可跑。

GitHub部署两次临时链接404、一次审批超时重试、一次base Python缺依赖都留档；不是模型能力失败，仍计实例占用。96条模型评估infra-invalid为0。原始权重/数据/代码没因分析被修改。adapter已本地SHA核对。官方关机已执行、SSH不可用；平台账单未独立确认，旧监控暂停。

执行commit：64d6610b4412a556609f51294725c3c3bb921dc9；四个run保留Oct10登记ID、实际Oct12执行：

- experiments/SFT-S100-20261010-001/：config.json、identity.json、steps.jsonl、result.json、reload_check.json、adapter_manifest.json。
- experiments/SFT-EVAL-S100-20261010-001/：config.json、identity.json、trajectories.jsonl、result.json。
- experiments/SFT-MIX100-20261010-001/与experiments/SFT-EVAL-MIX100-20261010-001/：对应同类证据。
- configs/sft_scale_plan_v2.json、configs/sft_mixed100_plan.json：冻结计划。
- reports/sft-extensions-20261012/：配对统计、空reference语义复核、MIX失败复核。
- evidence/sft-extension-20261012/：原始archive、hash校验、远端operations日志archive和shutdown_receipt.json。
- docs/SFT_EXTENSIONS_20261012.md：完整结果与分母/成本边界。

## 7. 今晚三个知识点

1. task数、assistant样本数、processed tokens、target tokens和optimizer updates是五种不同预算。
2. labels mask与attention mask不同；CE/梯度/重载门槛与Agent行为评估不同。
3. verifier只覆盖可检验的目标；成功轨迹也要审证据，尤其no-op会让“碰巧保持状态”拿高分。

## 8. 五个面试追问（不给答案）

1. 同样310updates，50条两遍和100条一遍分别控制了什么、没控制什么？
2. 为什么Tool Observation作为输入可见，却常常labels=-100？多轮历史assistant呢？
3. 空reference的官方8/8，为什么不能说模型已经掌握什么时候不操作？
4. 你如何证明LoRA真实更新、保存重载正确，为什么这些仍不能证明任务能力提高？
5. 24任务两个seed为什么要按任务簇比较？你能从当前区间和开发集性质得出多强的结论？

## 9. 明天的路线分叉

建议停止盲目加SFT样本，转入现有training数据的DPO pair审核与有界cost probe设计；历史13对只是候选，不代表训练资格。也可先做更完整的现有dev语义分析；不需要GPU。新独立评估/组合泛化需先冻结定义，不能借机打开sealed题调模型。由你决定下一阶段，本轮未自动开始。学完可回答上面5问再考核，尚未作答不标记通过。
