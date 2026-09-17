"""Network-forbidden CPU controls using an old training707 response fixture."""
from copy import deepcopy
import json
import urllib.request
from unittest.mock import patch
from common import ROOT,Run,card,write_json
from collect_deepseek_probe import preflight,summarize
from veriagent.teacher_data import teacher_request
from veriagent.teacher_rollout import teacher_trajectory,APIError,request_body as old_body
from veriagent.deepseek_teacher import endpoint,request_body,usage,validate_response,estimated_cost


def main():
    cfg=json.loads((ROOT/'configs/deepseek_acquisition_plan.json').read_text())
    run=Run('DEEPSEEK-CPU-20260917-001',card(
        'Does the new provider adapter preserve fixed training data and enforce request/usage boundaries?',
        'Provider changes need no environment/reward changes and must not enable reasoning/retries.',
        'DeepSeek request envelope and usage accounting',
        ['schema identity','credential endpoint restriction','mode/usage checks','real fixture replay'],
        'All offline controls pass before any real provider call',
        experiment_kind='CPU_FORMAT_FIXTURE_NOT_MODEL_EVAL',seed=None))
    checks=[]
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)})
        assert value,name
    def reject(name,fn):
        try:fn()
        except (ValueError,APIError):check(name,True)
        else:check(name,False)
    _,cohort,rows,tasks,coverage=preflight(cfg,False)
    for row in rows:
        req=teacher_request(row,tasks[row['task_uid']],cohort['B1_addition'])
        body=request_body(req['messages'],req['tools'],cfg,768)
        check('schema_'+str(row['id']),[{'type':t['type'],**t['function']} for t in body['tools']]==req['tools'])
        check('mode_'+str(row['id']),body['thinking']=={'type':'disabled'} and 'seed' not in body and 'enable_thinking' not in body)
    for value in ['http://api.deepseek.com','https://api.deepseek.com.evil.test',
                  'https://secret@api.deepseek.com','https://api.deepseek.com?key=x',
                  'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1']:
        reject('endpoint_'+value,lambda value=value:endpoint(value))
    check('endpoint_exact',endpoint('https://api.deepseek.com')=='https://api.deepseek.com/chat/completions')
    original=next(json.loads(l) for l in (ROOT/'experiments/TEACHER-ACQUIRE-20260916-001/trajectories.jsonl')
                  .read_text(encoding='utf-8').splitlines() if json.loads(l)['task_id']==707)
    fixtures=[]
    for t in original['rounds']:
        r=deepcopy(t['raw_response']);r['model']='CPU_FIXTURE_NOT_REAL_DEEPSEEK'
        r['usage']['prompt_cache_hit_tokens']=0
        r['usage']['prompt_cache_miss_tokens']=r['usage']['prompt_tokens']
        r['usage']['completion_tokens_details']={'reasoning_tokens':0}
        fixtures.append(r)
    row=next(r for r in rows if r['id']==707)
    def rollout(values):
        pending=iter(deepcopy(values))
        return teacher_trajectory(row,tasks[row['task_uid']],cohort,cfg,lambda body,timeout:next(pending),
                                  lambda:100,producer='CPU_FIXTURE_NOT_TRAINING',
                                  body_builder=request_body,response_validator=validate_response)
    with patch.object(urllib.request.OpenerDirector,'open',side_effect=AssertionError('Network forbidden')):
        record=rollout(fixtures)
        check('replay_success',not record['infra_invalid'] and record['verifier']['official_reward']==1 and record['online_replay_equal'])
        check('state_identity',record['final_state_sha256']==original['final_state_sha256'])
        check('not_approved',record['training_eligible'] is False)
        thinking=deepcopy(fixtures);thinking[0]['choices'][0]['message']['reasoning_content']='fixture'
        check('thinking_stops',rollout(thinking)['infra_invalid'])
        truncated=deepcopy(fixtures);truncated[0]['choices'][0]['finish_reason']='length'
        check('truncated_no_action',not rollout(truncated)['events'])
        bad=deepcopy(fixtures[0]);bad['usage']['prompt_cache_miss_tokens']+=1
        reject('cache_sum_mismatch',lambda:usage(bad))
        bad=deepcopy(fixtures[0]);bad['usage']['completion_tokens_details']['reasoning_tokens']=1
        reject('reasoning_usage_rejected',lambda:validate_response(bad))
        check('invalid_reasoning_still_costed',estimated_cost(bad,'2026-09-17T04:00:00+00:00')['estimated_rmb']>0)
        peak=estimated_cost(fixtures[0],'2026-09-17T01:00:00+00:00')['estimated_rmb']
        off=estimated_cost(fixtures[0],'2026-09-17T04:00:00+00:00')['estimated_rmb']
        check('tariff_boundary',peak==2*off)
        oldcfg=json.loads((ROOT/'configs/teacher_acquisition_plan.json').read_text())
        old=old_body(original['initial_messages'],original['tool_schemas'],oldcfg,768)
        check('old_provider_unchanged',old['enable_thinking'] is False and old['seed']==42 and 'thinking' not in old)
    write_json(run.path/'checks.json',checks);write_json(run.path/'fixture_replay.json',record)
    write_json(run.path/'coverage.json',coverage)
    run.finish({'status':'PASSED','checks':len(checks),'external_requests':0,'new_model_rollouts':0,
                'parameter_updates':0,'gpu_hours':0})
    print(json.dumps({'status':'PASSED','checks':len(checks),'covered':len(coverage)}))


if __name__=='__main__':main()
