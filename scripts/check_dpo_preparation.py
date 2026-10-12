"""CPU data/math/negative controls; no model load or parameter update."""
import argparse, ast, copy, hashlib, importlib.util, json, math
import numpy as np
from common import ROOT
from veriagent.dpo import load_pairs, scalar_loss_and_coefficient, cache_key
from veriagent.sft_stage import validate_example, read, sha
import github_file_sync as sync


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);a=ap.parse_args()
    assert a.run_id.startswith('DPO-CONTROLS-') and '/' not in a.run_id and '\\' not in a.run_id
    out=ROOT/'experiments'/a.run_id;out.mkdir(exist_ok=False)
    cfg,pairs=load_pairs();checks={}
    (out/'config.json').write_text(json.dumps(read(ROOT/'configs/dpo_preparation.json'),indent=2),encoding='utf-8')
    (out/'identity.json').write_text(json.dumps({'parent_commit':'8890b985b504358610478d382ebe9f17b875e4fb','script_sha256':sha(__import__('pathlib').Path(__file__)),'kind':'CPU_DATA_MATH_CONTROLS'},indent=2),encoding='utf-8')
    try:
        checks['12_unique_completed_pairs']=len(pairs)==12 and all(p[s]['termination']=='assistant_final' for p in pairs for s in ['chosen','rejected'])
        checks['five_domains']=len({p['category'] for p in pairs})==5
        checks['censored271_held']=271 not in {p['task_id'] for p in pairs}
        checks['eight_probe_unique_tasks']=len(set(cfg['probe_task_ids']))==cfg['optimizer_updates']==8
        checks['initial_equal_ln2']=abs(scalar_loss_and_coefficient(-7,-3,-7,-3,.1)[0]-math.log(2))<1e-12
        checks['margin_direction']=scalar_loss_and_coefficient(-6,-3,-7,-3,.1)[0]<math.log(2)<scalar_loss_and_coefficient(-8,-3,-7,-3,.1)[0]
        checks['extreme_margin_stable']=all(math.isfinite(scalar_loss_and_coefficient(x,0,0,0,.1)[0]) for x in [-1e6,1e6])
        pc,pr,rc,rr=-21.,-9.,-20.,-10.;h=1e-5;loss,coefficient=scalar_loss_and_coefficient(pc,pr,rc,rr,.1)
        derivative=(scalar_loss_and_coefficient(pc+h,pr,rc,rr,.1)[0]-scalar_loss_and_coefficient(pc-h,pr,rc,rr,.1)[0])/(2*h)
        checks['chosen_coefficient_finite_difference']=abs(derivative-coefficient)<1e-9
        derivative=(scalar_loss_and_coefficient(pc,pr+h,rc,rr,.1)[0]-scalar_loss_and_coefficient(pc,pr-h,rc,rr,.1)[0])/(2*h)
        checks['rejected_opposite_gradient']=abs(derivative+coefficient)<1e-9
        # Multi-turn recomputation chain rule versus direct finite differences.
        features_c=np.array([[1.,2.],[-1.,.5]]);features_r=np.array([[.2,-.7]])
        theta=np.array([.3,-.4])
        def score(t,features):return float((-np.logaddexp(0,-features@t)).sum())
        def objective(t):return scalar_loss_and_coefficient(score(t,features_c),score(t,features_r),-3,-2,.1)[0]
        _,coeff=scalar_loss_and_coefficient(score(theta,features_c),score(theta,features_r),-3,-2,.1)
        grad=coeff*((features_c/(1+np.exp(features_c@theta))[:,None]).sum(0)-(features_r/(1+np.exp(features_r@theta))[:,None]).sum(0))
        direct=np.array([(objective(theta+np.eye(2)[i]*h)-objective(theta-np.eye(2)[i]*h))/(2*h) for i in range(2)])
        checks['stream_chain_rule_finite_difference']=np.allclose(grad,direct,atol=1e-9)
        ex=pairs[0]['chosen']['encoded_turns'][0]
        mutations={'context_loss':lambda e:e['labels'].__setitem__(0,e['input_ids'][0]),
            'partial_assistant_mask':lambda e:e['labels'].__setitem__(e['prefix_tokens'],-100),
            'nontraining_pool':lambda e:e.update(source_pool='development'),
            'truncated_target':lambda e:e['input_ids'].pop(),
            'bad_token_count':lambda e:e.update(supervised_tokens=0)}
        for name,fn in mutations.items():
            bad=copy.deepcopy(ex);fn(bad)
            try:validate_example(bad);checks['reject_'+name]=False
            except ValueError:checks['reject_'+name]=True
        changed=copy.deepcopy(cfg);changed['initial_adapter_sha256']['adapter_model.safetensors']='wrong'
        checks['reference_key_binds_S1']=cache_key(cfg,pairs[0])!=cache_key(changed,pairs[0])
        changed_pair=copy.deepcopy(pairs[0]);changed_pair['chosen']['encoded_turns'][0]['input_ids'][0]+=1
        checks['reference_key_binds_actual_tokens']=cache_key(cfg,pairs[0])!=cache_key(cfg,changed_pair)
        checks['S1_adapter_local_hashes']=all(sha(ROOT/'checkpoints/SFT-S1-20261010-001/adapter'/n)==v for n,v in cfg['initial_adapter_sha256'].items())
        # Parse the exact remote authorization expression without executing network code.
        tree=ast.parse(sync.REMOTE_CODE);scope={}
        for n in ast.walk(tree):
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_files'):
                scope[n.targets[0].id]=ast.literal_eval(n.value)
        checks['DPO_local_remote_whitelist_equal']=set(sync.DPO_FILES)==scope['dpo_files']==set(cfg['deployment_files'])
        gate=next(n.test for n in ast.walk(tree) if isinstance(n,ast.Assert) and 'not additions' in ast.unparse(n.test))
        expr=compile(ast.Expression(gate),'<allowlist>','eval')
        base=set();branches=[set()]
        for k in ['teacher_files','teacher_probe_files','interactive_files','deepseek_files','window_files','sft_stage_files','sft_scale_files','sft_mixed_files']:
            base=base|scope[k];branches.append(base)
        dpo=set.union(*(scope[k] for k in ['teacher_files','teacher_probe_files','interactive_files','deepseek_files','window_files','sft_stage_files','sft_scale_files','sft_mixed_files','dpo_files']))
        checks['legacy_sync_branches_preserved']=all(eval(expr,{'__builtins__':{}},{**scope,'additions':v}) for v in branches)
        checks['DPO_sync_branch_allowed']=eval(expr,{'__builtins__':{}},{**scope,'additions':dpo})
        checks['unknown_sync_path_rejected']=not eval(expr,{'__builtins__':{}},{**scope,'additions':dpo|{'secrets.txt'}})
        checks['all_deployment_files_exist']=all((ROOT/p).is_file() for p in cfg['deployment_files'])
        checks['no_weights_in_GitHub_payload']=not any(p.endswith('.safetensors') or p.startswith('checkpoints/') for p in cfg['deployment_files'])
        for p in ['veriagent/dpo.py','scripts/prepare_dpo.py','scripts/run_dpo_probe.py','scripts/check_dpo_torch.py','scripts/github_file_sync.py']:ast.parse((ROOT/p).read_text(encoding='utf-8'))
        checks['syntax_passed']=True
        assert all(checks.values()),checks
        torch_result={'status':'UNAVAILABLE_LOCAL_TORCH_NOT_INSTALLED','required_before_LLM_load':True}
        if importlib.util.find_spec('torch'):
            from check_dpo_torch import run_controls
            torch_result=run_controls()
        result={'status':'CPU_DATA_AND_MATH_CONTROLS_PASSED','checks':checks,'torch_control':torch_result,
            'source_sha256':{p:sha(ROOT/p) for p in cfg['deployment_files']},'transport_script_sha256':sha(ROOT/'scripts/github_file_sync.py'),'GPU_hours':0,'API_calls':0,'parameter_updates':0,
            'not_yet_verified':['actual Transformers on target host','real Torch autograd if unavailable above','8B reference scores','GPU memory and step time','LoRA update/reload','Agent efficacy']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':result['status'],'checks':len(checks),'torch':torch_result['status']}))
    except Exception:
        import traceback
        (out/'invalid_run.json').write_text(json.dumps({'traceback':traceback.format_exc(),'checks':checks,'model_run':False},indent=2),encoding='utf-8');raise


if __name__=='__main__':main()
