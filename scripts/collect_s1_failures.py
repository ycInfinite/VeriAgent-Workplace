"""Fixed25 current-S1 training-pool acquisition;no optimizer or teacher API."""
import argparse,gzip,importlib.metadata,json,os,threading,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from run_day3 import ROOT,write,append,Monitor,inference_trajectory,summarize,weight_sample
from veriagent.environment import WorkplaceEnv
from veriagent.sft_stage import read,sha,require,validate_deployment,verify_weights


def load_eval():
    from copy import deepcopy
    from veriagent.sft_data import content_sha256
    cfg=read(ROOT/'configs/s1_failure_acquisition.json');path=ROOT/cfg['data_path']
    require(sha(path)==cfg['data_sha256'],'Frozentraininginputs changed')
    with gzip.open(path,'rt',encoding='utf-8') as f:rows=[json.loads(l) for l in f]
    require(len(rows)==cfg['max_tasks']==25 and [r['task_uid'] for r in rows]==cfg['task_uids'],'Cohortchanged')
    selection=read(ROOT/cfg['selection_manifest']);checks={x['task_id']:x for x in selection['student_initial_checks']}
    require(all(r['source_pool']=='training_candidate' for r in rows),'Nontraininginput')
    for r in rows:
        messages=deepcopy(r['responses_create_params']['input']);messages[0]['content']+='\n\n'+cfg['B1_addition']
        require(content_sha256(messages)==checks[r['id']]['initial_messages_sha256'],'Initialpromptchanged')
        require(content_sha256(r['responses_create_params']['tools'])==checks[r['id']]['tool_schemas_sha256'],'Toolschanged')
    return cfg,cfg,rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--condition',choices=['S1'],default='S1')
    p.add_argument('--training-run');p.add_argument('--execute',action='store_true');p.add_argument('--run-id')
    p.add_argument('--hourly-rmb',type=float);args=p.parse_args()
    cfg,ev,rows=load_eval()
    if not args.execute:
        print(json.dumps({'status':'CPU_TRAIN25_INPUT_CHECK_PASSED_NO_MODEL_LOAD','condition':args.condition,
            'tasks':25,'planned_rollouts':25,'adapter_runtime_validation':'frozen_S1_SHA_required_before_acquisition'}));return
    require(os.name=='posix' and args.run_id and Path(args.run_id).name==args.run_id
            and args.run_id==cfg['run_id'],'Explicit bounded Linux eval run ID required')
    if args.hourly_rmb is not None:require(0<args.hourly_rmb<float('inf'),'Invalid price')
    build=validate_deployment(cfg['deployment_files'])
    require(args.training_run is None,'Use exact frozen S1 only')
    adapter=ROOT/cfg['initial_adapter_path'];hashes=cfg['initial_adapter_sha256'];training_run='SFT-S1-20261010-001'
    policy={'condition':'S1','base_revision':cfg['model_revision']}
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
        require(torch.cuda.device_count()==1 and torch.cuda.is_bf16_supported(),'Single BF16 GPU required')
        require(torch.cuda.get_device_properties(0).total_memory>=cfg['min_gpu_memory_gib']*2**30,'Qualified96GB class required')
        path=ROOT/cfg['weights_path'];tok=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        for row in rows:
            from copy import deepcopy
            messages=deepcopy(row['responses_create_params']['input']);messages[0]['content']+='\n\n'+cfg['B1_addition']
            prompt=tok.apply_chat_template(messages,tools=row['responses_create_params']['tools'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
            require(len(tok(prompt,add_special_tokens=False)['input_ids'])+ev['max_output_tokens_per_model_call']<=cfg['max_context_tokens'],'InitialHFcontextcannotfit')
        write(out/'tokenizer_preflight.json',{'actual_HF_initial_contexts_passed':len(rows),'context_limit':cfg['max_context_tokens']})
        model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,
            device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
        if adapter is not None:model=PeftModel.from_pretrained(model,adapter,is_trainable=False)
        model.eval();model.requires_grad_(False);before=weight_sample(model)
        identity.update({'gpu':torch.cuda.get_device_name(0),'packages':packages,'parameter_sample_before':before,'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad)})
        require(identity['trainable_parameters']==0,'Eval model unexpectedly trainable');write(out/'identity.json',identity)
        for seed in ev['seeds']:
            for row in rows:
                if time.perf_counter()-started+180>ev['max_wall_seconds']:raise TimeoutError('Insufficient room for next bounded trajectory')
                r=inference_trajectory(model,tok,row,run_cfg,seed,'B1',source_pool='training_candidate')
                r.update({'experiment_id':args.run_id,'acquisition_condition':'S1_TRAIN25','policy_identity':policy})
                records.append(r);append(out/'trajectories.jsonl',r);write(out/'progress.json',summarize(records))
                if r['infra_invalid']:raise RuntimeError('Invalid infrastructure rollout; no retry')
        require(len(records)==25 and weight_sample(model)==before,'Incomplete eval or changed parameter sample')
        wall=time.perf_counter()-started
        result={**summarize(records),'status':'S1_TRAINING_COLLECTION_COMPLETE','condition':args.condition,
            'gpu_hours':wall/3600,'wall_seconds':wall,'cost_estimate_rmb':wall/3600*args.hourly_rmb if args.hourly_rmb is not None else None,
            'semantic_failure_metrics':'PENDING_MANUAL_REVIEW_DO_NOT_REUSE_OLD_ANNOTATIONS','parameter_updates':0,
            'scope':'25trainingtasks only;new data candidates,not dev/test metric', 'DPO_data_admitted':False,'parameter_samples_unchanged':True,
            'cost_scope':'Execution record creation through inference completion; earlier input checks/instance uptime/storage excluded'}
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'completed'})
        print(json.dumps(result),flush=True)
    except Exception as exc:
        write(out/'invalid_run.json',{'error_type':type(exc).__name__,'traceback':traceback.format_exc(),'completed_rollouts':len(records),
            'wall_seconds':time.perf_counter()-started,'retain_valid_trajectories_and_all_costs':True})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':args.run_id,'event':'invalid_or_incomplete'});raise
    finally:timer.cancel();monitor.stop()


if __name__=='__main__':main()
