"""Admit only fresh full-pair judgments after replay; keep new/union and reward types separate."""
import gzip,json,time,traceback
from collections import Counter
from common import ROOT
from prepare_postsft_audit import branch
from veriagent.teacher_data import CanonicalTeacherEncoder
from veriagent.sft_data import content_sha256
from veriagent.sft_stage import read,sha,require


def main():
    out=ROOT/'experiments/S1-EXPAND-REVIEW-20261016-001';out.mkdir(exist_ok=False);start=time.perf_counter()
    def save(n,x):
        with (out/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2)
    def pack(n,rows):
        (out/n).write_bytes(gzip.compress(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows).encode(),mtime=0))
    cfg=read(ROOT/'configs/s1_preference_expansion.json');jpath=ROOT/'reports/preference-expansion-20261016/judgments.json'
    source=ROOT/'experiments'/cfg['run_id']/'trajectories.jsonl';replay=ROOT/'experiments/S1-EXPAND-REPLAY-20261016-001'
    save('identity.json',{'source_sha256':sha(source),'teacher_sha256':sha(ROOT/cfg['teacher_artifact']),'judgments_sha256':sha(jpath),
        'script_sha256':sha(__import__('pathlib').Path(__file__)),'execution_commit':read(ROOT/'experiments'/cfg['run_id']/'identity.json')['code_commit'],
        'review_protocol_sha256':sha(ROOT/'configs/s1_preference_expansion_review.json')})
    try:
        require(read(replay/'result.json')['branches']==182 and read(replay/'replay.json')['all_equal'],'Replay incomplete')
        require(read(replay/'identity.json')['source_sha256']==sha(source),'Replay source changed')
        with gzip.open(ROOT/cfg['teacher_artifact'],'rt',encoding='utf-8') as f:teachers={x['task_id']:x for x in map(json.loads,f)}
        students={x['task_id']:x for x in map(json.loads,source.read_text(encoding='utf-8').splitlines())}
        inventory=read(replay/'inventory.json')['tasks'];judgments=read(jpath);encoder=CanonicalTeacherEncoder(8192)
        reviews=[];pairs=[]
        for item in inventory:
            tid=item['task_id'];s=students[tid];t=teachers[tid];j=judgments.get(str(tid))
            if j is None:
                require(not item['empty_reference'] and item['S1_reward']==1 and item['complete_candidate'],'Required fresh review missing')
                j={'task_id':tid,'decision':'screened_no_reward_gap_not_admitted','reason':'Bothofficialreward1;wholepairsemanticsnotfreshlyreviewed;nottrainingadmitted.',
                    'teacher_full_review':False,'S1_full_review':False}
            else:
                require(j['S1_sha256']==content_sha256(s),'Reviewed S1 source changed')
                if j.get('teacher_full_review'):require(j['teacher_sha256']==content_sha256(t),'Reviewed teacher source changed')
            rec={**item,'review':j,'final_decision':j['decision']};reviews.append(rec)
            if not j['decision'].startswith('approved_'):continue
            require(j['teacher_full_review'] and j['S1_full_review'] and item['complete_candidate'],'Wholepair review/termination gate')
            require(t['termination']=='assistant_final' and not t['infra_invalid'] and not s['infra_invalid'],'Invalid branch')
            require(item['teacher_reward']==1 and item['S1_reward']==(0 if j['decision']=='approved_reward_gap_pair' else 1),'Preference label mismatch')
            for k in ['initial_messages','tool_schemas','initial_state_sha256','reference']:require(content_sha256(s[k])==content_sha256(t[k]),'Pair context mismatch')
            try:a,b=branch(t,encoder),branch(s,encoder)
            except (ValueError,AssertionError) as exc:
                rec.update(final_decision='held_encoding_integrity',encoding_error=type(exc).__name__+':'+str(exc));continue
            for obj in [a,b]:
                for ex in obj['encoded_turns']:ex.update(task_id=tid,task_uid=s['task_uid'],source_pool='training_candidate',training_eligible=True)
            pairs.append({'pair_id':f'CURRENT-S1-EXPAND-{tid}-20261016-v1','task_id':tid,'task_uid':s['task_uid'],'source_pool':'training_candidate',
                'category':item['category'],'empty_reference':item['empty_reference'],'prompt_context':t['initial_messages'],'tools':t['tool_schemas'],
                'initial_state_sha256':t['initial_state_sha256'],'chosen_run':'DEEPSEEK-SFTDATA-20260917-001','rejected_run':cfg['run_id'],
                'rejected_policy_identity':s['policy_identity'],'chosen':a,'rejected':b,'failure_category':j.get('failure_category'),
                'why_pair_valid':j['reason'],'fresh_review':j,'preference_type':j['decision'],'dpo_data_admitted':True,
                'status':'CPU_DATA_ADMITTED_GPU_UNQUALIFIED','GPU_training_authorized':False})
        old=ROOT/'experiments/S1-PAIR-REVIEW-20261016-001';union=[]
        for kind,filename in [('approved_reward_gap_pair','reward_gap_pairs.jsonl.gz'),('approved_same_reward_semantic_pair','same_reward_pairs.jsonl.gz')]:
            new=[p for p in pairs if p['preference_type']==kind]
            with gzip.open(old/filename,'rt',encoding='utf-8') as f:prior=list(map(json.loads,f))
            merged=prior+new;require(len({p['task_uid'] for p in merged})==len(merged),'Duplicate preference task')
            pack('new_'+filename,new);pack('cumulative_'+filename,merged);union+=merged
        save('review.json',{'tasks':reviews,'reviewer':'Codex','independent_human_review':False,'not_all182_semantically_reviewed':True,
            'dispositions':dict(Counter(x['final_decision'] for x in reviews))})
        metadata=lambda p:{k:v for k,v in p.items() if k not in ['chosen','rejected','prompt_context','tools']}|{side:{k:v for k,v in p[side].items() if k not in ['messages','encoded_turns']} for side in ['chosen','rejected']}
        save('manifest.json',{'new_pairs':[metadata(p) for p in pairs],'cumulative_pairs':[metadata(p) for p in union],
            'artifacts':{p.name:sha(p) for p in out.glob('*.jsonl.gz')},'prior_source_hashes':{n:sha(old/n) for n in ['reward_gap_pairs.jsonl.gz','same_reward_pairs.jsonl.gz']},
            'limits':['No oldBase12 negatives included','OriginalS1 policy shared;old25 vsnew91 hosts/drivers differ','Same-reward pairs remain separate;noautomatictraining','Teacher-approved source subset andsingle seed;notrepresentativeeval']})
        stats=lambda rows:{'pairs':len(rows),'domains':dict(Counter(p['category'] for p in rows)),
            'chosen_target_tokens':sum(p['chosen']['target_tokens'] for p in rows),'rejected_target_tokens':sum(p['rejected']['target_tokens'] for p in rows),
            'processed_tokens':sum(p[s]['processed_tokens'] for p in rows for s in ['chosen','rejected']),
            'max_sequence_tokens':max((p[s]['max_sequence_tokens'] for p in rows for s in ['chosen','rejected']),default=0)}
        result={'status':'PREFERENCE_EXPANSION_REVIEW_COMPLETE','tasks':91,'new':{k:stats([p for p in pairs if p['preference_type']==k]) for k in ['approved_reward_gap_pair','approved_same_reward_semantic_pair']},
            'cumulative':{k:stats([p for p in union if p['preference_type']==k]) for k in ['approved_reward_gap_pair','approved_same_reward_semantic_pair']},
            'dispositions':dict(Counter(x['final_decision'] for x in reviews)),'CPU_seconds':time.perf_counter()-start,'GPU_hours':0,'API_requests':0,'parameter_updates':0,'GPU_training_qualified':False}
        save('result.json',result);print(json.dumps(result))
    except Exception:
        save('invalid_run.json',{'traceback':traceback.format_exc(),'model_run':False,'CPU_seconds':time.perf_counter()-start});raise


if __name__=='__main__':main()
