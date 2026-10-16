"""Prepared matched dev24 inference only. Never opens sealed cases or trains."""
import argparse,gzip,importlib.metadata,json,os,threading,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from run_day3 import ROOT,write,append,Monitor,inference_trajectory,summarize,weight_sample
from veriagent.environment import WorkplaceEnv
from veriagent.sft_stage import read,sha,require,validate_deployment,verify_weights


def load_eval():
    cfg=read(ROOT/'configs/preference29_plan.json');ev=cfg['evaluation'];path=ROOT/ev['data_path']
    require(sha(path)==ev['data_sha256'],'Frozen dev input changed')
    with gzip.open(path,'rt',encoding='utf-8') as f:rows=[json.loads(l) for l in f]
    require(len(rows)==24 and [r['task_uid'] for r in rows]==ev['task_uids'],'Dev cohort changed')
    require(all(r['source_pool']=='development' for r in rows),'Non-dev evaluation case')
    from veriagent.dpo import load_pairs
    _,pairs=load_pairs('configs/preference29_plan.json')
    training={p['task_uid'] for p in pairs}
    require(not training & set(ev['task_uids']),'Train/eval overlap')
    return cfg,ev,rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--condition',choices=['S1','CHOSEN_SFT','DPO'],required=True)
    p.add_argument('--training-run');p.add_argument('--execute',action='store_true');p.add_argument('--run-id')
    p.add_argument('--hourly-rmb',type=float);args=p.parse_args()
    cfg,ev,rows=load_eval()
    if not args.execute:
        print(json.dumps({'status':'CPU_DEV_INPUT_CHECK_PASSED_NO_MODEL_LOAD','condition':args.condition,
            'tasks':24,'planned_rollouts':48,'adapter_runtime_validation':'required_after_training' if args.condition!='BASE_B1' else 'base_only'}));return
    require(os.name=='posix' and args.run_id and Path(args.run_id).name==args.run_id
            and args.run_id==cfg['eval_run_ids'][args.condition],'Explicit bounded Linux eval run ID required')
    if args.hourly_rmb is not None:require(0<args.hourly_rmb<float('inf'),'Invalid price')
    build=validate_deployment(cfg['deployment_files'])
    policy={'condition':args.condition,'base_revision':cfg['model_revision']}
    if args.condition=='S1':
        require(args.training_run is None,'Baseline uses frozen S1 only')
        adapter=ROOT/cfg['initial_adapter_path'];hashes=cfg['initial_adapter_sha256'];training_run='SFT-S1-20261010-001'
    else:
        require(args.training_run==cfg['training_run_ids'][args.condition],'Wrong training run')
        train=ROOT/'experiments'/args.training_run;tr=read(train/'result.json');tc=read(train/'config.json');tid=read(train/'identity.json')
        require(tr['status']=='PREFERENCE_TRAINING_COMPLETE_RELOAD_PASSED' and tr['optimizer_updates']==29 and tr['condition']==args.condition,'Unqualified adapter')
        require(tc=={**cfg,'condition':args.condition},'Training configuration changed')
        require(tid['code_commit']==build['code_commit'],'Training/eval execution commit mismatch')
        adapter=train/'adapter';hashes=read(train/'adapter_manifest.json');training_run=args.training_run
    require({p.name for p in adapter.iterdir() if p.is_file()}==set(hashes),'Adapter file set changed')
    require(all(sha(adapter/n)==h for n,h in hashes.items()),'Wrong adapter identity')
    policy['adapter']={'training_run':training_run,'files':hashes}
    out=ROOT/'experiments'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    run_cfg={**cfg,**ev,'condition':args.condition,'hourly_rmb':args.hourly_rmb,'status':'RUNNING_INFERENCE_ONLY'}
    write(out/'config.json',run_cfg);write(out/'initial_state.json',WorkplaceEnv().initial_state)
    identity={'experiment_id':args.run_id,'code_commit':build['code_commit'],'policy_identity':policy,
        'started_at':datetime.now(timezone.utc).isoformat(),'seeds':ev['seeds'],'data_sha256':ev['data_sha256']}
    write(out/'identity.json',identity);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'started'})
    records=[];started=time.perf_counter()
    def deadline():
        write(out/'deadline.json',{'status':'EVAL_WALL_LIMIT','completed_rollouts':len(records)});os._exit(124)
    timer=threading.Timer(ev['max_wall_seconds'],deadline);timer.daemon=True;timer.start()
    monitor=Monitor(out/'gpu_samples.jsonl');monitor.start()
    try:
        packages={n:importlib.metadata.version(n) for n in cfg['required_packages']}
        require(packages==cfg['required_packages'],'Unqualified package versions')
        write(out/'weight_revalidation.json',verify_weights(cfg))
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        from peft import PeftModel
        require(torch.cuda.device_count()==1,'Single GPU required')
        path=ROOT/cfg['weights_path'];tok=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,
            device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        if adapter is not None:model=PeftModel.from_pretrained(model,adapter,is_trainable=False)
        model.eval();model.requires_grad_(False);before=weight_sample(model)
        identity.update({'gpu':torch.cuda.get_device_name(0),'packages':packages,'parameter_sample_before':before,'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad)})
        require(identity['trainable_parameters']==0,'Eval model unexpectedly trainable');write(out/'identity.json',identity)
        for seed in ev['seeds']:
            for row in rows:
                if time.perf_counter()-started+180>ev['max_wall_seconds']:raise TimeoutError('Insufficient room for next bounded trajectory')
                r=inference_trajectory(model,tok,row,run_cfg,seed,'B1',source_pool='development')
                r.update({'experiment_id':args.run_id,'comparison_condition':args.condition,'policy_identity':policy})
                records.append(r);append(out/'trajectories.jsonl',r);write(out/'progress.json',summarize(records))
                if r['infra_invalid']:raise RuntimeError('Invalid infrastructure rollout; no retry')
        require(len(records)==48 and weight_sample(model)==before,'Incomplete eval or changed parameter sample')
        wall=time.perf_counter()-started
        result={**summarize(records),'status':'MATCHED_DEV_EVAL_COMPLETE','condition':args.condition,
            'gpu_hours':wall/3600,'wall_seconds':wall,'cost_estimate_rmb':wall/3600*args.hourly_rmb if args.hourly_rmb is not None else None,
            'semantic_failure_metrics':'PENDING_MANUAL_REVIEW_DO_NOT_REUSE_OLD_ANNOTATIONS','parameter_updates':0,
            'scope':'development24 only,not held-out or composition-generalization evidence','parameter_samples_unchanged':True,
            'cost_scope':'Execution record creation through inference completion; earlier input checks/instance uptime/storage excluded'}
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps(result),flush=True)
    except Exception as exc:
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),'completed_rollouts':len(records),
            'wall_seconds':time.perf_counter()-started,'retain_valid_trajectories_and_all_costs':True})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete'});raise
    finally:timer.cancel();monitor.stop()


if __name__=='__main__':main()
