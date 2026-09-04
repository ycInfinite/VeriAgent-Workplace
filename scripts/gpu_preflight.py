"""Read-only host inventory. No model, CUDA workload, rental, download or secret reads."""
import csv
import importlib.metadata
import io
import json
import platform
from pathlib import Path
import shutil
import subprocess


def inspect_host():
    disk=shutil.disk_usage(Path.cwd())
    result={'kind':'READ_ONLY_HOST_PREFLIGHT_NOT_MODEL_EXPERIMENT',
            'platform':platform.platform(),'python':platform.python_version(),
            'free_disk_gib':round(disk.free/2**30,1),'packages':{},'gpus':[],
            'gpu_workload_started':False,'model_loaded':False}
    for name in ('torch','transformers','vllm','tokenizers','pandas'):
        try:
            result['packages'][name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result['packages'][name]=None
    binary=shutil.which('nvidia-smi')
    if binary:
        try:
            p=subprocess.run([binary,'--query-gpu=name,memory.total,driver_version',
                              '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
            result['nvidia_smi_returncode']=p.returncode
            if p.returncode==0:
                for row in csv.reader(io.StringIO(p.stdout)):
                    if len(row)==3:
                        result['gpus'].append({'name':row[0].strip(),'memory_mib':int(row[1].strip()),
                                               'driver':row[2].strip()})
        except (subprocess.TimeoutExpired,ValueError,OSError) as exc:
            result['nvidia_smi_error_type']=type(exc).__name__
    else:
        result['nvidia_smi_returncode']=None
    result['requested_profile']={'phase':'Q0_INFERENCE_ONLY','visible_gpu_count':1,
                                 'full_gpu_memory_target_gb':24,'max_concurrent_sequences':1,
                                 'host_ram_gb_recommended':64,'free_disk_gib_recommended':100,
                                 'note':'No-card preparation intentionally has no GPU; 24GB fit remains unmeasured'}
    result['limitations']=['Does not verify GPU compute or package interoperability',
                          'Does not verify MIG allocation, billing, host RAM or model endpoint',
                          'No permission to rent/start an experiment is implied']
    return result


if __name__=='__main__':
    print(json.dumps(inspect_host(),ensure_ascii=False,indent=2))
