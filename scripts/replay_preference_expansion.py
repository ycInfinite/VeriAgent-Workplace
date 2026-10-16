"""Mechanical audit of all182 frozen branches; does not grant semantic admission."""
import gzip,json,time,traceback
from collections import Counter
from common import ROOT
from veriagent.sft_stage import read,sha,require
from veriagent.sft_data import content_sha256
from veriagent.environment import WorkplaceEnv,digest


def main():
    out=ROOT/'experiments/S1-EXPAND-REPLAY-20261016-001';out.mkdir(exist_ok=False);start=time.perf_counter()
    def save(n,x):
        with (out/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2)
    cfg=read(ROOT/'configs/s1_preference_expansion.json');source=ROOT/'experiments'/cfg['run_id']/'trajectories.jsonl'
    save('identity.json',{'source_collection':cfg['run_id'],'source_sha256':sha(source),'teacher_sha256':sha(ROOT/cfg['teacher_artifact']),
        'script_sha256':sha(__import__('pathlib').Path(__file__)),'scope':'CPU_only_all182_replay_not_semantic_admission'})
    try:
        with gzip.open(ROOT/cfg['teacher_artifact'],'rt',encoding='utf-8') as f:teachers={x['task_id']:x for x in map(json.loads,f)}
        students={x['task_id']:x for x in map(json.loads,source.read_text(encoding='utf-8').splitlines())}
        selected=read(ROOT/cfg['selection_manifest'])['tasks'];sel={x['task_id']:x for x in selected}
        require(set(teachers)==set(students)==set(sel) and len(students)==91,'Cohort differs')
        require([x['task_uid'] for x in students.values()]==cfg['task_uids'],'Order differs')
        results=[];inventory=[]
        for tid,s in students.items():
            t=teachers[tid];require(content_sha256(t)==sel[tid]['trajectory_sha256'],'Teacher source changed')
            require(s['seed']==42 and s['policy_identity']['adapter']['files']==cfg['initial_adapter_sha256'],'Policy/seed changed')
            for k in ['task_uid','initial_messages','tool_schemas','initial_state_sha256','reference']:
                require(content_sha256(t[k])==content_sha256(s[k]),'Pair mismatch:'+k)
            for side,x in [('teacher',t),('S1',s)]:
                require(x['source_pool']=='training_candidate' and not x['infra_invalid'] and x['online_replay_equal'],'Invalid source')
                env=WorkplaceEnv();require(digest(env.initial_state)==x['initial_state_sha256'],'Initial state differs')
                for event in x['events']:
                    actual=env.step(event['tool_call'])
                    for k in ['observation','exception','state_before_sha256','state_after_sha256','state_changes']:
                        require(content_sha256(actual[k])==content_sha256(event[k]),'Event replay differs:'+k)
                reward=env.verify(x['reference'])['official_reward'];require(reward==x['verifier']['official_reward'],'Reward replay differs')
                results.append({'task_id':tid,'side':side,'events':len(x['events']),'reward':reward,'source_record_sha256':content_sha256(x)})
            complete=s['termination']=='assistant_final' and not s['parse_errors'] and all(x.get('eos_reached',True) for x in s['rounds'])
            inventory.append({'task_id':tid,'task_uid':s['task_uid'],'category':sel[tid]['category'],'empty_reference':not s['reference'],
                'teacher_reward':t['verifier']['official_reward'],'S1_reward':s['verifier']['official_reward'],'termination':s['termination'],
                'complete_candidate':complete,'teacher_source_sha256':content_sha256(t),'S1_source_sha256':content_sha256(s),
                'student_tool_sequence':[e['tool_call']['name'] for e in s['events']], 'teacher_tool_sequence':sel[tid]['teacher_tool_sequence'],
                'S1_input_tokens':s['input_tokens'],'S1_output_tokens':s['output_tokens'],'review_priority':
                'held_censored_or_corrupted' if not complete else ('full_reward_gap_pair_review' if s['verifier']['official_reward']==0 else ('empty_S1_semantic_review' if not s['reference'] else 'screened_no_reward_gap_not_admitted'))})
        save('replay.json',{'branches':results,'all_equal':True});save('inventory.json',{'tasks':inventory,'semantic_admission':False})
        result={'status':'ALL182_BRANCHES_REPLAY_EQUAL','tasks':91,'branches':182,'review_priorities':dict(Counter(x['review_priority'] for x in inventory)),
            'CPU_seconds':time.perf_counter()-start,'GPU_hours':0,'parameter_updates':0,'API_calls':0,'new_pairs_admitted':0}
        save('result.json',result);print(json.dumps(result))
    except Exception:
        save('invalid_run.json',{'traceback':traceback.format_exc(),'model_run':False,'CPU_seconds':time.perf_counter()-start});raise


if __name__=='__main__':main()
