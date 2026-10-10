"""Actual installed-tokenizer/GPU admission for S100; never constructs an LLM."""
import argparse,importlib.metadata,json,time
from pathlib import Path
from run_sft_scale import validate_actual_tokenizer
from veriagent.sft_scale import load_inputs
from veriagent.sft_stage import ROOT,validate_deployment,verify_weights,require,read


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    require(a.run_id.startswith('SFT-SCALE-REMOTE-PREP-') and Path(a.run_id).name==a.run_id,'Invalid run ID')
    out=ROOT/'experiments'/a.run_id;out.mkdir(exist_ok=False);start=time.perf_counter()
    try:
        cfg,selection,examples,order=load_inputs('S100')
        build=validate_deployment(['configs/sft_scale_plan_v2.json','veriagent/sft_scale.py','scripts/run_sft_scale.py','scripts/evaluate_sft_scale.py','scripts/validate_sft_scale_host.py'])
        packages={n:importlib.metadata.version(n) for n in cfg['required_packages']}
        require(packages==cfg['required_packages'],'Package mismatch')
        weights=verify_weights(cfg);validate_actual_tokenizer(cfg,examples)
        import torch
        require(torch.cuda.device_count()==1 and torch.cuda.is_bf16_supported(),'Single BF16 GPU required')
        baseline=read(ROOT/'experiments/SFT-EVAL-BASE-20261010-001/identity.json')
        require(torch.cuda.get_device_name(0)==baseline['gpu'],'Different GPU would confound latency comparison')
        value={'status':'S100_HOST_PREFLIGHT_PASSED','code_commit':build['code_commit'],'tasks':100,'examples':len(examples),
            'updates_planned':len(order),'weights':weights,'packages':packages,'GPU':torch.cuda.get_device_name(0),
            'seconds':time.perf_counter()-start,'model_loaded':False,'parameter_updates':0}
        (out/'config.json').write_text(json.dumps(cfg,indent=2));(out/'result.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
    except Exception as exc:
        (out/'invalid_run.json').write_text(json.dumps({'error_type':type(exc).__name__,'error':str(exc),'seconds':time.perf_counter()-start,'parameter_updates':0},indent=2));raise


if __name__=='__main__':main()
