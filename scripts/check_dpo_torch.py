"""Actual torch CPU gradient gate, required before loading the 8B policy."""
import copy, math
from veriagent.dpo import turn_logp, pair_backward


def run_controls():
    import torch
    import torch.nn.functional as F
    from types import SimpleNamespace
    torch.manual_seed(19)
    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__();self.table=torch.nn.Parameter(torch.randn(7,7))
        def forward(self,input_ids,attention_mask=None,use_cache=False):
            return SimpleNamespace(logits=self.table[input_ids])
    e={'input_ids':[1,2,3,4], 'labels':[-100,-100,3,4]}
    r={'input_ids':[1,5,6], 'labels':[-100,-100,6]}
    pair={'chosen':{'encoded_turns':[e,e]},'rejected':{'encoded_turns':[r]}}
    ref={'chosen':-6.,'rejected':-2.};full=Tiny();stream=copy.deepcopy(full)
    pc=2*turn_logp(full,e);pr=turn_logp(full,r)
    loss=-F.logsigmoid(.1*((pc-pr)-(ref['chosen']-ref['rejected'])))
    loss.backward();got=pair_backward(stream,pair,ref,.1)
    manual=F.log_softmax(full.table,dim=-1)[2,3]+F.log_softmax(full.table,dim=-1)[3,4]
    require=lambda ok,msg: None if ok else (_ for _ in ()).throw(AssertionError(msg))
    checks={'shifted_target_only_score':torch.allclose(turn_logp(full,e),manual),
        'stream_loss_matches_full_graph':abs(got['loss']-float(loss.detach()))<1e-6,
        'stream_gradient_matches_full_graph':torch.allclose(full.table.grad,stream.table.grad,atol=1e-6,rtol=1e-5),
        'context_row_has_no_direct_loss':bool((full.table.grad[1]==0).all()),
        'gradient_finite_nonzero':bool(torch.isfinite(stream.table.grad).all() and stream.table.grad.abs().sum()>0)}
    for k,v in checks.items():require(bool(v),k)
    return {'status':'TORCH_CPU_CONTROLS_PASSED','checks':{k:bool(v) for k,v in checks.items()},'gradient_max_abs_diff':float((full.table.grad-stream.table.grad).abs().max()),'policy_model_loaded':False,'optimizer_updates':0}


if __name__=='__main__':
    import json
    print(json.dumps(run_controls()))
