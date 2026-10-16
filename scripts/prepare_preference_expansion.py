"""Freeze the complete remaining91 reviewed teacher tasks, without model-score selection."""
import ast
import copy
import gzip
import hashlib
import json
import traceback
from collections import Counter
from common import ROOT
from veriagent.sft_data import content_sha256
from veriagent.token_mask import TokenMaskInspector
from veriagent.sft_stage import read, sha


def main():
    out = ROOT/'experiments/S1-EXPAND-PREP-20261016-001'; out.mkdir(exist_ok=False)
    def save(n, x):
        with (out/n).open('x', encoding='utf-8', newline='\n') as f: json.dump(x, f, ensure_ascii=False, indent=2)
    def packed(n, values):
        (out/n).write_bytes(gzip.compress(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in values).encode(), mtime=0))
    try:
        c = read(ROOT/'configs/s1_failure_acquisition.json')
        c.update(run_id='S1-EXPAND-ACQUIRE-20261016-001', max_tasks=91, max_wall_seconds=3600,
            status='FROZEN91_TRAINING_ACQUISITION_NO_UPDATES', scope='Complete remaining reviewed teacher cohort91;not representative evaluation',
            instance_shutdown_authorized=False, GPU_inference_authorized=True)
        c.update({'Research Question':'Can the remaining reviewed teacher pool broaden currentS1 preference coverage beyond the first six reward-gap pairs?',
            'Hypothesis':'Additional tasks across five domains and empty-reference conditions may yield useful currentS1 negatives;pair yield and quality are unknown.',
            'Independent Variable':'Expand the fixed training cohort from prior25 to91 previously uncollected tasks;no policy update.',
            'Controlled Variables':'Exact originalS1/B1/tools/state/modelrevision;seed42,8192context,6rounds,768percall/2048totaloutput;oneattempt/task.',
            'Metrics':'Valid/success counts bydomain/reference;tool validity/tokens/latency/VRAM/GPUh;pair yield and failure/tool-signature coverage.',
            'Evidence Gate':'Existing teacher approvalhashes;excludeS1training50 andprior25;officialtrain pool;actualHF fit;realtools/replay;fresh full pair review before admission.',
            'Cost Bound':'One already-running userPRO6000;91rollouts;3600sprocesslimit;estimated0.35-0.70scriptGPUh based on25-task probe;hourlypriceunknown;KEEP_INSTANCE_ON.',
            'Failure Branch':'Stop andpreserve infrastructure failure;holdcensored/ambiguous/badchosen;no resampling/newteacherAPI/DPOupdates/RL/test.'})
        s1 = {x['task_uid'] for x in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}
        prior = read(ROOT/'experiments/S1-FAILURE-PREP-20261012-002/selection.json')['tasks']
        seen = {x['task_uid'] for x in prior}
        sources = ['experiments/SFT-READY-20260917-001/quality_approvals.json', 'experiments/NOOP-REVIEW-20261010-001/quality_approvals.json']
        approvals = [x for path in sources for x in read(ROOT/path)['approved']]
        pools = {x['task_uid']:x for x in read(ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json')['records']}
        teachers = {x['task_uid']:x for x in map(json.loads,(ROOT/'experiments/DEEPSEEK-SFTDATA-20260917-001/trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        raw = {x['task_uid']:x for x in map(json.loads,(ROOT/'experiments/DEEPSEEK-POOL-PREP-20260917-001/tasks.jsonl').read_text(encoding='utf-8').splitlines())}
        bank = read(ROOT/'experiments/DEEPSEEK-POOL-PREP-20260917-001/tool_schemas.json')
        eligible = [x for x in approvals if x['task_uid'] not in s1|seen]
        rank = lambda x: hashlib.sha256(('S1-EXPAND91-v1:'+x['task_uid']).encode()).hexdigest()
        eligible.sort(key=lambda x:(pools[x['task_uid']]['category'], bool(not teachers[x['task_uid']]['reference']), rank(x)))
        assert len(eligible) == len({x['task_uid'] for x in eligible}) == 91
        ins = TokenMaskInspector(); selected=[]; initial=[]; payload=[]; packed_teacher=[]
        for approval in eligible:
            uid=approval['task_uid']; t=teachers[uid]; pool=pools[uid]; row=copy.deepcopy(raw[uid])
            assert pool['pool']=='training_candidate' and pool['source_split']=='train'
            assert content_sha256(t)==approval['trajectory_sha256'] and t['verifier']['official_reward']==1 and not t['infra_invalid']
            row['responses_create_params']['tools']=bank[row.pop('tool_schema_ref')]
            messages=copy.deepcopy(row['responses_create_params']['input']);messages[0]['content']+='\n\n'+c['B1_addition']
            assert messages==t['initial_messages'] and row['responses_create_params']['tools']==t['tool_schemas']
            count=len(ins.tokenizer.encode(ins.render(messages,t['tool_schemas'],generate=True),add_special_tokens=False).ids)
            assert count+c['max_output_tokens_per_model_call']<=c['max_context_tokens']
            selected.append({**approval,'category':pool['category'],'empty_reference':not t['reference'],'selection_rank':rank(approval),
                'teacher_tool_sequence':[e['tool_call']['name'] for e in t['events']], 'teacher_rounds_proxy':len(t['rounds'])})
            initial.append({'task_id':t['task_id'],'initial_tokens':count,'initial_messages_sha256':content_sha256(messages),'tool_schemas_sha256':content_sha256(t['tool_schemas']),'initial_state_sha256':t['initial_state_sha256']})
            payload.append(row);packed_teacher.append(t)
        assert sum(x['empty_reference'] for x in selected)==24
        packed('tasks.jsonl.gz',payload);packed('teacher_records.jsonl.gz',packed_teacher)
        coverage = Counter((x['category'],x['empty_reference']) for x in selected)
        save('selection.json',{'tasks':selected,'student_initial_checks':initial,'selector':'All91remaining eligible;domain/reference-kind andSHA256 S1-EXPAND91-v1order;no modelscore input',
            'excluded_S1_training':sorted(s1),'excluded_prior25':sorted(seen),
            'coverage':[{'category':d,'empty_reference':e,'tasks':n} for (d,e),n in sorted(coverage.items())],
            'limits':'Teacher-approved subset,not wholetraining;no new emptycalendar/email available. Teacher rounds are observed trajectory length,not minimum dependencydepth.'})
        c.update(data_path=str((out/'tasks.jsonl.gz').relative_to(ROOT)).replace('\\','/'),data_sha256=sha(out/'tasks.jsonl.gz'),
            selection_manifest=str((out/'selection.json').relative_to(ROOT)).replace('\\','/'),task_uids=[x['task_uid'] for x in selected],
            teacher_artifact=str((out/'teacher_records.jsonl.gz').relative_to(ROOT)).replace('\\','/'),teacher_artifact_sha256=sha(out/'teacher_records.jsonl.gz'))
        c['deployment_files']=['configs/s1_preference_expansion.json','scripts/collect_s1_preference_expansion.py',c['data_path'],c['selection_manifest']]
        (ROOT/'configs/s1_preference_expansion.json').write_text(json.dumps(c,indent=2)+'\n',encoding='utf-8',newline='\n');save('config.json',c)
        import github_file_sync as sync
        tree=ast.parse(sync.REMOTE_CODE)
        remote=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='preference_expansion_files' for v in n.targets))
        from collect_s1_preference_expansion import load_eval
        _,_,checked_rows=load_eval()
        old=(ROOT/'scripts/collect_s1_failures.py').read_text(encoding='utf-8')
        expected=old.replace('configs/s1_failure_acquisition.json','configs/s1_preference_expansion.json')
        for a,b in [('Fixed25','Fixed91'),('==25','==91'),("'tasks':25","'tasks':91"),("'planned_rollouts':25","'planned_rollouts':91"),('TRAIN25','TRAIN91'),('25trainingtasks','91trainingtasks')]:expected=expected.replace(a,b)
        checks={'91unique_originalS1_unseen_prior25_disjoint':len(checked_rows)==91 and not set(c['task_uids'])&(s1|seen),
            '67action24empty':sum(not x['empty_reference'] for x in selected)==67,
            'all_available_eligible_used_once':len(eligible)==91,'five_domains':len({x['category'] for x in selected})==5,
            'initial_contexts_fit_without_truncation':all(x['initial_tokens']+768<=8192 for x in initial),
            'exact_originalS1':c['initial_adapter_sha256']==read(ROOT/'configs/s1_failure_acquisition.json')['initial_adapter_sha256'],
            'generation_bounds_unchanged':all(c[k]==read(ROOT/'configs/s1_failure_acquisition.json')[k] for k in ['seeds','temperature','top_p','max_model_rounds','max_context_tokens','max_output_tokens_per_model_call','max_output_tokens_per_trajectory']),
            'collector_only_cohort_and_label_changes':(ROOT/'scripts/collect_s1_preference_expansion.py').read_text(encoding='utf-8')==expected,
            'four_file_GitHub_whitelist':set(c['deployment_files'])==set(sync.PREFERENCE_EXPANSION_FILES)==remote,
            'teacher_not_in_new_collector_payload':c['teacher_artifact'] not in remote,'no_shutdown':not c['instance_shutdown_authorized']}
        assert all(checks.values()),checks
        save('identity.json',{'parent_commit':'f894915c7a5f0f2c518e3b648f7f081181e6a199','script_sha256':sha(__import__('pathlib').Path(__file__)),
            'sources':{n:sha(ROOT/n) for n in sources+['experiments/SFT-READY-20260917-001/selection.json','experiments/S1-FAILURE-PREP-20261012-002/selection.json','experiments/Q0-SPLIT-20260904-003/split_manifest.json']},
            'execution_files':{n:sha(ROOT/n) for n in c['deployment_files']}})
        result={'status':'COHORT91_FROZEN_CPU_CHECKS_PASSED','checks':checks,'tasks':91,'nonempty':67,'empty':24,'max_initial_tokens':max(x['initial_tokens'] for x in initial),
            'GPU_hours':0,'API_calls':0,'parameter_updates':0,'new_pairs_admitted':0,'pair_yield':'UNMEASURED'}
        save('result.json',result);print(json.dumps(result))
    except Exception:
        save('invalid_run.json',{'traceback':traceback.format_exc(),'model_run':False});raise


if __name__=='__main__':main()
