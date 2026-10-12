"""Torch CPU gradient equivalence for both matched preference-training arms."""
from common import ROOT  # Establish project imports for direct script execution.
from check_dpo_torch import run_controls as dpo_controls


def run_controls():
    import copy
    import torch
    from types import SimpleNamespace
    from veriagent.dpo import turn_logp
    result=dpo_controls()
    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__();self.table=torch.nn.Parameter(torch.randn(8,8))
        def forward(self,input_ids,attention_mask=None,use_cache=False):
            return SimpleNamespace(logits=self.table[input_ids])
    torch.manual_seed(17);full=Tiny();stream=copy.deepcopy(full)
    examples=[{'input_ids':[1,2,3,4],'labels':[-100,-100,3,4]},
              {'input_ids':[1,5,6,7],'labels':[-100,-100,-100,7]}]
    targets=sum(sum(x!=-100 for x in e['labels']) for e in examples)
    loss=-sum(turn_logp(full,e) for e in examples)/targets;loss.backward()
    total=0.
    for e in examples:
        part=-turn_logp(stream,e)/targets;total+=float(part.detach());part.backward()
    result['checks']['chosen_task_mean_loss_equal']=abs(float(loss.detach())-total)<1e-6
    result['checks']['chosen_task_mean_gradient_equal']=torch.allclose(full.table.grad,stream.table.grad,atol=1e-6,rtol=1e-5)
    assert all(result['checks'].values()),result
    result['status']='BOTH_ARMS_TORCH_CPU_CONTROLS_PASSED'
    result['chosen_gradient_max_abs_diff']=float((full.table.grad-stream.table.grad).abs().max())
    return result


if __name__=='__main__':
    import json
    print(json.dumps(run_controls()))
