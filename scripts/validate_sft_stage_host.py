"""Existing-host no-card preflight. Never constructs an LLM or performs an update."""
import importlib.metadata,json,os,time,traceback
from datetime import datetime,timezone
from run_day3 import ROOT,write,append
from run_sft_comparison import validate_actual_tokenizer
from veriagent.sft_stage import load_inputs,validate_deployment,verify_weights,require

RUN='SFT-REMOTE-PREP-20260917-001'


def main():
    require(os.name=='posix','This receipt is for the existing Linux no-card host')
    out=ROOT/'experiments'/RUN;out.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    protocol={'experiment_id':RUN,'kind':'CPU_HOST_PREFLIGHT_NO_MODEL_CONSTRUCTION',
        'Research Question':'Does the actual existing no-card host match frozen SFT data,weights,packages and Transformers tokenizer?',
        'Hypothesis':'The existing qualified runtime can admit both new whole-trajectory datasets without installing frameworks or loading a model.',
        'Independent Variable':'Local preparation versus existing-host actual runtime validation',
        'Controlled Variables':['fixed GitHub commit','frozen reviewed S1/S2 datasets','existing weights and venv','no GPU mode/no model construction'],
        'Metrics':['deployment hashes','weight/tokenizer hashes','package identities','actual template/IDs/targets','CUDA uninitialized'],
        'Evidence Gate':'Botharms pass admission and actual installedtokenizer;9pinned weight/aux files match;noGPUdevice/model/update.',
        'Cost Bound':'Existing904 no-card0.10RMB/h,at most30min platform window;no new rental/API/GPU/parameterupdates.',
        'Failure Branch':'Keepfailedreceiptandstop;noinstall,modeldownload,GPUstartup,automaticretryortraining.'}
    write(out/'config.json',protocol);append(ROOT/'experiments/registry.jsonl',{'experiment_id':RUN,'event':'started'})
    try:
        build=validate_deployment(['scripts/validate_sft_stage_host.py','configs/sft_comparison_plan.json','veriagent/sft_stage.py'])
        import torch
        require(not list(__import__('pathlib').Path('/dev').glob('nvidia[0-9]*')),'Expected no-card mode')
        require(not torch.cuda.is_initialized(),'Unexpected initialized CUDA')
        checks={};weight_receipt=None;packages=None
        for arm in ['S1','S2']:
            cfg,selection,examples,order=load_inputs(arm,reencode=True)
            if weight_receipt is None:
                packages={n:importlib.metadata.version(n) for n in cfg['required_packages']}
                require(packages==cfg['required_packages'],'Unqualified installed packages')
                weight_receipt=verify_weights(cfg);write(out/'weight_revalidation.json',weight_receipt)
            validate_actual_tokenizer(cfg,examples)
            checks[arm]={'tasks':len(selection['tasks']),'full_turns':len(examples),'planned_steps':len(order),
                        'actual_transformers_template_ids_target_matches':len(examples)}
        require(not torch.cuda.is_initialized(),'CUDA initialized during CPU validation')
        result={'status':'HOST_NO_CARD_PREFLIGHT_PASSED','code_commit':build['code_commit'],'checked_at':datetime.now(timezone.utc).isoformat(),
            'deployment_files':len(build['files']),'arms':checks,'packages':packages,'weights':weight_receipt,
            'wall_seconds':time.perf_counter()-start,'model_loaded':False,'gpu_hours':0,'model_requests':0,'parameter_updates':0,
            'limitations':'New310stepGPUruntime/VRAM/CE/updates/reload andAgentbehavior not executed'}
        write(out/'result.json',result);append(ROOT/'experiments/registry.jsonl',{'experiment_id':RUN,'event':'completed'});print(json.dumps(result),flush=True)
    except Exception as exc:
        write(out/'invalid_run.json',{'status':'HOST_PREFLIGHT_INVALID','error_type':type(exc).__name__,'traceback':traceback.format_exc(),
                                    'wall_seconds':time.perf_counter()-start,'model_loaded':False})
        append(ROOT/'experiments/registry.jsonl',{'experiment_id':RUN,'event':'invalid'});raise


if __name__=='__main__':main()
