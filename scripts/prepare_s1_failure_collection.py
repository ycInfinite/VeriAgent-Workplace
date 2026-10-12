"""Freeze25 training tasks before current-S1 rollout; no model/API/selection by score."""
import copy,gzip,hashlib,json
from common import ROOT
from veriagent.sft_data import content_sha256
from veriagent.token_mask import TokenMaskInspector


def main():
    out=ROOT/'experiments/S1-FAILURE-PREP-20261012-002';out.mkdir(exist_ok=False)
    def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
    def write(n,v):(out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    def packed(n,v):(out/n).write_bytes(gzip.compress(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in v).encode(),mtime=0))
    base=read('configs/preference_comparison_plan.json')
    c={k:base[k] for k in ['model_id','model_revision','dataset_revision','weights_path','required_packages','weight_and_tokenizer_sha256','initial_adapter_path','initial_adapter_sha256','B1_addition','min_gpu_memory_gib']}
    c.update({k:v for k,v in base['evaluation'].items() if k not in ['task_uids','conditions','rollouts_per_condition','data_path','data_sha256']})
    c.update(run_id='S1-FAILURE-ACQUIRE-20261012-001',max_tasks=25,seeds=[42],max_wall_seconds=1800,status='FROZEN_TRAINING_ACQUISITION_NO_UPDATES',scope='25trainingtasks;oneS1rollout each;not representative evaluation')
    c.update({'Research Question':'Can currentS1 produce informative attributable failures on25 unseen-by-S1 training tasks with existing reviewed teachers?',
        'Hypothesis':'CurrentS1 failures may better match remaining behavior than oldBase negatives; usefulpair yield unknown.',
        'Independent Variable':'One new S1 rollout per fixed trainingtask; no policy update.',
        'Controlled Variables':'ExactS1,originalB1/tools/state,seed42,8192/6rounds/2048output,25fixedtasks;no retries/redraw.',
        'Metrics':'Officialsuccess/strata,toolvalidity,tokens/latency/VRAM/GPUh,failureattribution,reviewedpairyield.',
        'Evidence Gate':'Trainingpool andS1disjoint,teacher/context hashes,actualHF/weights,realtools/replay,fullpairreview beforeadmission.',
        'Cost Bound':'Oneexisting96GBGPU;25rollouts;1800sscript/2hlifecycle;estimate0.12-0.25GPUh plussetup;no newteacherAPI.',
        'Failure Branch':'Stop andpreserve infrastructure failure;hold incomplete/ambiguous/corruptpairs;no resampling/DPOupdates/RL.'})
    write('config.json',c)
    try:
        s1={x['task_uid'] for x in read('experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}
        pools={x['task_uid']:x for x in read('experiments/Q0-SPLIT-20260904-003/split_manifest.json')['records']}
        action=read('experiments/SFT-READY-20260917-001/quality_approvals.json')['approved']
        noop=read('experiments/NOOP-REVIEW-20261010-001/quality_approvals.json')['approved']
        teachers={x['task_uid']:x for x in map(json.loads,(ROOT/'experiments/DEEPSEEK-SFTDATA-20260917-001/trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        rows={x['task_uid']:x for x in map(json.loads,(ROOT/'experiments/DEEPSEEK-POOL-PREP-20260917-001/tasks.jsonl').read_text(encoding='utf-8').splitlines())}
        bank=read('experiments/DEEPSEEK-POOL-PREP-20260917-001/tool_schemas.json')
        rank=lambda x:hashlib.sha256(('S1-TRAIN25-v1:'+x['task_uid']).encode()).hexdigest()
        selected=[]
        for domain in sorted({pools[x['task_uid']]['category'] for x in action}):
            for group,n,empty in [(action,4,False),(noop,1,True)]:
                eligible=[x for x in group if x['task_uid'] not in s1 and pools[x['task_uid']]['category']==domain]
                assert len(eligible)>=n
                selected.extend({**x,'category':domain,'empty_reference':empty,'selection_rank':rank(x)} for x in sorted(eligible,key=rank)[:n])
        assert len(selected)==len({x['task_uid'] for x in selected})==25
        ins=TokenMaskInspector();checks=[];payload=[];ts=[]
        for x in selected:
            uid=x['task_uid'];t=teachers[uid];row=copy.deepcopy(rows[uid]);pool=pools[uid]
            row['responses_create_params']['tools']=bank[row.pop('tool_schema_ref')]
            assert pool['pool']=='training_candidate' and pool['source_split']=='train' and uid not in s1
            assert content_sha256(t)==x['trajectory_sha256'] and t['verifier']['official_reward']==1 and not t['infra_invalid']
            assert (not t['reference'])==x['empty_reference'] and t['termination']=='assistant_final'
            messages=copy.deepcopy(row['responses_create_params']['input']);messages[0]['content']+='\n\n'+base['B1_addition']
            assert messages==t['initial_messages'] and row['responses_create_params']['tools']==t['tool_schemas']
            prompt=ins.render(messages,t['tool_schemas'],generate=True);count=len(ins.tokenizer.encode(prompt,add_special_tokens=False).ids);assert count+1<=8192
            checks.append({'task_id':x['task_id'],'initial_tokens':count,'initial_messages_sha256':content_sha256(messages),'tool_schemas_sha256':content_sha256(t['tool_schemas']),'initial_state_sha256':t['initial_state_sha256']})
            payload.append(row);ts.append(t)
        packed('tasks.jsonl.gz',payload);packed('teacher_records.jsonl.gz',ts)
        write('selection.json',{'tasks':selected,'student_initial_checks':checks,'selector':'SHA256 S1-TRAIN25-v1;4action+1empty/domain;excludeS1training50;no modelscore input','eligible_counts':{'action':87,'noop':29},'limits':'S100/MIX may have used some selectedtasks,butcurrentS1 didnot;notgloballyunseen'})
        c.update(data_path=str((out/'tasks.jsonl.gz').relative_to(ROOT)).replace('\\','/'),data_sha256=hashlib.sha256((out/'tasks.jsonl.gz').read_bytes()).hexdigest(),task_uids=[x['task_uid'] for x in selected],selection_manifest=str((out/'selection.json').relative_to(ROOT)).replace('\\','/'),teacher_artifact=str((out/'teacher_records.jsonl.gz').relative_to(ROOT)).replace('\\','/'),teacher_artifact_sha256=hashlib.sha256((out/'teacher_records.jsonl.gz').read_bytes()).hexdigest())
        c['deployment_files']=['configs/s1_failure_acquisition.json','scripts/collect_s1_failures.py',c['data_path'],c['selection_manifest']]
        (ROOT/'configs/s1_failure_acquisition.json').write_text(json.dumps(c,indent=2)+'\n',encoding='utf-8',newline='\n')
        write('final_config.json',c)
        write('identity.json',{'parent_commit':'d4664b417e0b5e059f89d87c9bb1def4cf2d0086','script_sha256':hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest(),'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['experiments/SFT-READY-20260917-001/quality_approvals.json','experiments/NOOP-REVIEW-20261010-001/quality_approvals.json','experiments/SFT-READY-20260917-001/selection.json','experiments/Q0-SPLIT-20260904-003/split_manifest.json','experiments/DEEPSEEK-POOL-PREP-20260917-001/tool_schemas.json']}})
        result={'status':'COHORT25_INITIAL_TOKENIZATION_PASSED','tasks':25,'nonempty':20,'empty':5,'initial_fit':25,'max_initial_tokens':max(x['initial_tokens'] for x in checks),'GPU_hours':0,'API_calls':0,'parameter_updates':0,'pair_admission':False}
        write('result.json',result);print(json.dumps(result));print('tasks',[x['task_id'] for x in selected])
    except Exception:
        import traceback
        write('invalid_run.json',{'traceback':traceback.format_exc(),'model_run':False});raise


if __name__=='__main__':main()
