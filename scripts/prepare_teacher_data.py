"""CPU teacher-input and canonical-target audit. No API requests or training."""
import argparse
from copy import deepcopy
import hashlib
import json
import time

from common import ROOT,Run,load_rows,write_json
from veriagent.teacher_data import teacher_request,validate_request,CanonicalTeacherEncoder
from veriagent.sft_data import content_sha256


def rejected(name,fn):
    try:fn()
    except ValueError as exc:return {'name':name,'passed':True,'reason':str(exc)}
    return {'name':name,'passed':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    cfg=json.loads((ROOT/'configs/teacher_preparation_audit.json').read_text())
    exp=Run(args.run_id,cfg);start=time.monotonic()
    try:
        cohort=json.loads((ROOT/cfg['cohort_manifest']).read_text())
        rows=load_rows('train');requests=[]
        for task in cohort['tasks']:
            request=teacher_request(rows[task['source_row_index']],task,cohort['B1_addition'])
            requests.append(request)
            exp.append('request_manifest.jsonl',{'task_uid':task['task_uid'],'task_id':task['source_id'],
                'source_pool':'training_candidate','prompt_sha256':content_sha256(request['messages']),
                'tools_sha256':content_sha256(request['tools']),'request_keys':sorted(request),
                'oracle_fields_in_request':False,'teacher_called':False})
        source_path=ROOT/cfg['format_stress_source']
        recorded=[json.loads(x) for x in source_path.read_text(encoding='utf-8').splitlines()]
        encoder=CanonicalTeacherEncoder(cfg['max_context_tokens'])
        count=0;processed=0;supervised=0;different=0;maximum=0
        for record in recorded:
            if record['source_pool']!='training_candidate':raise ValueError('Unexpected format stress-test pool')
            for turn in record['rounds']:
                if time.monotonic()-start>cfg['max_wall_seconds']:raise TimeoutError('CPU wall bound')
                prefix=turn['input_messages'];assistant=record['messages'][len(prefix)]
                if not turn['eos_reached']:raise ValueError('Incomplete source generation needs separate handling')
                ex=encoder.encode(prefix,record['tool_schemas'],assistant)
                n=ex['prefix_tokens'];target=ex['labels'][n:]
                if ex['labels'][:n]!=[-100]*n:raise ValueError('Unmasked context')
                changed=target!=turn['output_token_ids']
                count+=1;processed+=ex['processed_tokens'];supervised+=ex['supervised_tokens']
                different+=changed;maximum=max(maximum,ex['processed_tokens'])
                exp.append('format_audit.jsonl',{'task_id':record['task_id'],'turn':turn['turn'],
                    'source_trajectory_sha256':content_sha256(record),
                    **{k:ex[k] for k in ['prefix_tokens','supervised_tokens','processed_tokens','prefix_sha256','canonical_target_sha256','format','training_eligible']},
                    'canonical_targets_differ_from_source_generated_ids':changed,
                    'interpretation':'Existing unapproved trajectory used only as a format stress test, not new teacher data'})
        task=cohort['tasks'][0];request=requests[0]
        altered=deepcopy(request);altered['ground_truth']=rows[task['source_row_index']]['ground_truth']
        controls=[rejected('oracle_field',lambda:validate_request(altered,task))]
        altered=deepcopy(request);altered['messages'][1]['content']+=' changed'
        controls.append(rejected('changed_task_prompt',lambda:validate_request(altered,task)))
        wrong=deepcopy(task);wrong['pool']='development'
        controls.append(rejected('development_pool',lambda:validate_request(request,wrong)))
        controls.append(rejected('non_assistant_target',lambda:encoder.encode(request['messages'],request['tools'],{'role':'tool','content':'x'})))
        controls.append(rejected('template_boundary_injection',lambda:encoder.encode(request['messages'],request['tools'],{'role':'assistant','content':'<|im_start|>assistant'})))
        write_json(exp.path/'negative_controls.json',controls)
        success=len(requests)==20 and count==sum(len(r['rounds']) for r in recorded) and all(x['passed'] for x in controls)
        result={'status':'CPU_TEACHER_PREPARATION_PASSED_PROVIDER_PENDING' if success else 'GATE_FAILED',
            'fixed_training_requests':len(requests),'prompt_tool_identity_matches':len(requests),
            'recorded_trajectories_used_for_format_stress':len(recorded),'visible_assistant_turns_encoded':count,
            'turns_dropped':0,'processed_tokens':processed,'canonical_supervised_tokens':supervised,
            'canonical_targets_different_from_original':different,'max_sequence_tokens':maximum,
            'negative_controls_passed':sum(x['passed'] for x in controls),'negative_controls_total':len(controls),
            'teacher_api_calls':0,'new_model_rollouts':0,'new_training_approvals':0,'parameter_updates':0,
            'gpu_hours':0,'paid_cost_rmb':0,'elapsed_seconds':time.monotonic()-start,
            'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
            'limitations':['Teacher provider/model/access still needs user information',
                'Canonical student targets do not reproduce a different teachers sampled token IDs or likelihood',
                'Prior full-trajectory rejections remain unchanged; no selective-turn supervision']}
        exp.finish(result,'completed' if success else 'gate_failed');print(json.dumps(result,indent=2))
        if not success:raise SystemExit(1)
    except Exception as exc:
        exp.finish({'status':'PREPARATION_INVALID','error_type':type(exc).__name__,'error':str(exc),
            'teacher_api_calls':0,'parameter_updates':0},'invalid');raise


if __name__=='__main__':main()
