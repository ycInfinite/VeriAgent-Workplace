"""CPU environment semantics tests; all trajectories are SCRIPTED, never model results."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import time
from common import ROOT, Run, card, load_rows, write_json
from veriagent.environment import WorkplaceEnv, snapshot, digest
from resources_servers.workplace_assistant.utils import execute_actions_and_reset_state

def evaluate(row, actions, variant):
    env=WorkplaceEnv()
    for action in actions:
        env.step(action)
    verified=env.verify(row['ground_truth'])
    capture=io.StringIO()
    with redirect_stdout(capture):
        replay=snapshot(execute_actions_and_reset_state(actions))
    return {'task_id':row['id'],'source_split':'train','variant':variant,
            'producer':'SCRIPTED_CPU_AUDIT_NOT_LLM','eligible_for_posttraining':False,
            'messages':row['responses_create_params']['input'],'tools':row['responses_create_params']['tools'],
            'reference':row['ground_truth'],'actions':actions,'events':env.events,
            'termination':'script_exhausted','verifier':verified,
            'initial_state_sha256':digest(env.initial_state),'final_state_sha256':digest(snapshot(env.tools)),
            'state_changed':snapshot(env.tools)!=env.initial_state,
            'online_replay_equal':snapshot(env.tools)==replay,
            'tokens':None,'gpu_hours':0,'policy_model':None}

def run(run_id, manifest):
    exp=Run(run_id,card('Do official tools mutate/reset/isolate state, and what does reward actually measure?',
        'Reference actions execute deterministically; state-matching ignores some process/answer defects',
        'Scripted action sequence: reference, omission, invalid prefix, unrelated mutation',
        ['reward by variant','state changes','reset/isolation','online/replay agreement','exceptions'],
        'Separate executable state properties from unverified semantic correctness',seed=20260904))
    start=time.perf_counter()
    try:
        rows=load_rows('train')
        indices=json.loads((ROOT/manifest).read_text())['indices']
        sample=[rows[i] for i in indices]
        base=WorkplaceEnv()
        write_json(exp.path/'initial_state.json',base.initial_state)
        counts=Counter(); failures=[]; reference_findings=[]; parity=[]
        for row in sample:
            ref=row['ground_truth']
            variants={'reference':deepcopy(ref),'reference_repeat':deepcopy(ref),'empty':[]}
            if ref:
                variants['omit_last']=deepcopy(ref[:-1])
            variants['unknown_then_reference']=[{'name':'nonexistent_tool_q0','arguments':'{}'}]+deepcopy(ref)
            variants['unrelated_extra_write']=deepcopy(ref)+[{'name':'email_send_email','arguments':json.dumps({
                'recipient':'q0-audit@example.invalid','subject':'UNRELATED Q0 MUTATION','body':'This deliberate test action is outside the task.'})}]
            rewards={}
            for name,actions in variants.items():
                try:
                    record=evaluate(row,actions,name)
                    exp.append('trajectories.jsonl',record)
                    r=record['verifier']['official_reward'];rewards[name]=r
                    counts[f'{name}:reward={int(r)}']+=1
                    parity.append(record['online_replay_equal'])
                    if name=='reference':
                        reference_findings.append({'task_id':row['id'],'reference_actions':len(ref),
                            'state_changed':record['state_changed'],'reward':r,
                            'tool_exceptions':sum(e['exception'] is not None for e in record['events']),
                            'observations':[e['observation'] for e in record['events']]})
                except Exception as exc:
                    failure={'task_id':row['id'],'variant':name,'error_type':type(exc).__name__,'error':str(exc),
                             'classification':'environment_or_audit_failure_NOT_policy_failure'}
                    failures.append(failure);exp.append('invalid_records.jsonl',failure)
            if rewards.get('reference') != rewards.get('reference_repeat'):
                failures.append({'task_id':row['id'],'type':'nondeterministic_reference_reward'})
        a,b=WorkplaceEnv(),WorkplaceEnv()
        b_before=digest(snapshot(b.tools))
        a.step({'name':'email_send_email','arguments':json.dumps({'recipient':'q0@example.invalid','subject':'Isolation','body':'Test'})})
        isolation=(b_before==digest(snapshot(b.tools)))
        a_changed=(digest(snapshot(a.tools))!=digest(a.initial_state))
        a.reset();reset_ok=digest(snapshot(a.tools))==b_before
        write_json(exp.path/'reference_findings_DEV_ONLY.json',reference_findings)
        result={'tasks':len(sample),'variant_counts':dict(counts),'invalid_record_count':len(failures),
                'reset_restores_state':reset_ok,'independent_instances_isolated':isolation,
                'write_actually_changes_state':a_changed,'online_replay_agreement_count':sum(parity),
                'online_replay_checked':len(parity),
                'reference_no_state_change_tasks':[x['task_id'] for x in reference_findings if not x['state_changed']],
                'reference_with_python_exceptions':[x['task_id'] for x in reference_findings if x['tool_exceptions']],
                'wall_seconds':time.perf_counter()-start,'gpu_hours':0,
                'claims_not_supported':['LLM task success','correct final natural language','identifier grounding','native NeMo service compatibility'],
                'failures':failures}
        exp.finish(result)
        print(json.dumps(result,indent=2))
    except Exception as exc:
        exp.finish({'error_type':type(exc).__name__,'error':str(exc)},'infrastructure_invalid');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True)
    p.add_argument('--manifest',default='experiments/Q0-DATA-20260904-001/pilot_dev24.json')
    args=p.parse_args();run(args.run_id,args.manifest)
