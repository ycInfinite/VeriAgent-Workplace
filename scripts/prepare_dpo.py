"""Immutable local audit/export of 13 historical training pairs; no model/API."""
import argparse, copy, gzip, json, time, traceback
from datetime import datetime, timezone
from common import ROOT
from prepare_postsft_audit import branch, rows
from veriagent.sft_data import content_sha256
from veriagent.sft_stage import read, sha, require
from veriagent.teacher_data import CanonicalTeacherEncoder
from veriagent.environment import WorkplaceEnv, digest

# Fresh full visible-message review on 2026-10-12, not independent human review.
REVIEWS = {
    565: 'Chosen executes requested histogram, observes returned simulated path; rejected gives scalar then asks whether plot needed. No physical image attestation.',
    972: 'Chosen produces both requested distribution histograms/date range; rejected line charts mismatch distribution request.',
    247: 'Directory grounds Lena; exact title/15:00/30min. Final constraints remark scoped to stated business hours, not calendar conflict clearance. Rejected invents recipient and changes title.',
    859: 'Both pages checked; latest observed start15:00/end17:00 ID252 renamed. Rejected invents12345678 then delegates lookup to user.',
    123: 'Chosen earliest10:00 ID96 deleted within requested date. Rejected treats first meeting as literal name and repeatedly broadens dates.',
    770: 'Only requested name/Lead/grounded Lena email supplied. Rejected stores display name as email and needless empty fields.',
    271: 'Chosen deletes only observed Raj/Lost/Hardware ID24. Rejected deletes other owners too, a real policy error, but ends at round cap without final response; held to avoid censored-branch preference in first probe, not infra-invalid.',
    20: 'Grounded both owners; complete4customer list; only Qualified ID27 matches union, update correct. Rejected Qualified,Won literal misses owner and requested Proposal.',
    177: 'Complete5email list identifies latest ID17, both recipient lookups precede forwarding. Rejected invents both addresses.',
    76: 'Complete2email list identifies Sofia latest ID264, exact requested body. Rejected sends placeholder ID and stops.',
    965: 'Directory plus full13-item unpaginated In Progress list supports unique Dmitri ID9. Broad lookup is acceptable, not minimal. Rejected invents address, unsupported pagination, false no-op.',
    687: 'Resolved email and exact filter identify both267/214; both changed to In Review. Rejected name/email fabrication and unsupported page_size lead false no-op.',
    8: 'Resolved Chenwei, full filtered list ID137 updated. Rejected invents email and falsely concludes no work.'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);a=ap.parse_args()
    require(a.run_id.startswith('DPO-PREP-') and '/' not in a.run_id and '\\' not in a.run_id,'Invalid ID')
    out=ROOT/'experiments'/a.run_id;out.mkdir(exist_ok=False);start=time.perf_counter()
    def save(name,value):
        with (out/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    cfg=read(ROOT/'configs/dpo_preparation.json');save('config.json',cfg)
    save('identity.json',{'started_at':datetime.now(timezone.utc).isoformat(),'parent_commit':cfg['parent_commit'],
        'script_sha256':sha(__import__('pathlib').Path(__file__)),'kind':'CPU_ONLY','model_revision':cfg['model_revision'],
        'dataset_revision':cfg['dataset_revision']})
    try:
        source=ROOT/cfg['candidate_artifact'];require(sha(source)==cfg['candidate_sha256'],'Candidates changed')
        with gzip.open(source,'rt',encoding='utf-8') as f:candidates=[json.loads(l) for l in f]
        chosen={r['task_id']:r for r in rows('DEEPSEEK-QUAL-20260917-001')}
        rejected={r['task_id']:r for r in rows('SFT-ACQUIRE-20260916-001')}
        pools={r['task_uid']:r for r in read(ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json')['records']}
        encoder=CanonicalTeacherEncoder(8192);approved=[];reviews=[];replays=[]
        require(len(candidates)==13 and {p['task_id'] for p in candidates}==set(REVIEWS),'Unexpected cohort')
        for pair in candidates:
            p=copy.deepcopy(pair);tid=p['task_id'];pool=pools[p['task_uid']]
            require(pool['pool']=='training_candidate' and pool['source_split']=='train','Leakage')
            for side,record in [('chosen',chosen[tid]),('rejected',rejected[tid])]:
                require(content_sha256(record)==p[side]['source_record_sha256'],'Source changed')
                require(not record['infra_invalid'] and record['online_replay_equal'],'Infrastructure or replay failure')
                for k,v in [('initial_messages',p['prompt_context']),('tool_schemas',p['tools']),('initial_state_sha256',p['initial_state_sha256'])]:require(record[k]==v,'Pair context/state differs')
                env=WorkplaceEnv();require(digest(env.initial_state)==p['initial_state_sha256'],'Initial state changed')
                for event in record['events']:
                    actual=env.step(event['tool_call'])
                    for k in ['observation','exception','state_before_sha256','state_after_sha256','state_changes']:
                        require(content_sha256(actual[k])==content_sha256(event[k]),'Replay event mismatch: '+k)
                reward=env.verify(record['reference'])['official_reward']
                require(reward==record['verifier']['official_reward'],'Reward changed')
                b=branch(record,encoder);require(content_sha256(b)==content_sha256(p[side]),'Canonical branch changed')
                replays.append({'task_id':tid,'side':side,'events':len(record['events']),'reward':reward,'source_record_sha256':content_sha256(record)})
            keep=tid!=271
            reviews.append({'pair_id':p['pair_id'],'task_id':tid,'decision':'approved_data' if keep else 'held_censored_rejected',
                'reason':REVIEWS[tid],'reviewer':'Codex','independent_human_review':False,'all_visible_messages_reviewed':True,
                'chosen_sha256':p['chosen']['source_record_sha256'],'rejected_sha256':p['rejected']['source_record_sha256']})
            if not keep:continue
            for side in ['chosen','rejected']:
                require(p[side]['termination']=='assistant_final','Censored branch')
                for e in p[side]['encoded_turns']:e.update(task_uid=p['task_uid'],task_id=tid,source_pool='training_candidate',training_eligible=True)
            p.update(dpo_data_admitted=True,status='OFFLINE_DATA_ADMITTED_GPU_UNQUALIFIED',category=pool['category'],fresh_review=reviews[-1])
            approved.append(p)
        payload=''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in approved).encode()
        with (out/'pairs.jsonl.gz').open('xb') as f:f.write(gzip.compress(payload,mtime=0))
        save('review.json',{'reviewed':13,'approved':len(approved),'held':1,'pairs':reviews,'reason_not_length':'Preferences based on task correctness; no length reward; censored271 remains valid policy failure but excluded from pilot'})
        save('replay.json',{'branches':replays,'fresh_replays':len(replays),'all_equal':True})
        save('manifest.json',{'pair_artifact_sha256':sha(out/'pairs.jsonl.gz'),'pairs':[{k:v for k,v in p.items() if k not in ['tools','prompt_context','chosen','rejected']} |
            {s:{k:v for k,v in p[s].items() if k not in ['messages','encoded_turns']} for s in ['chosen','rejected']} for p in approved],
            'sources':{str(p.relative_to(ROOT)):sha(p) for p in [source,ROOT/'experiments/DEEPSEEK-QUAL-20260917-001/trajectories.jsonl',ROOT/'experiments/SFT-ACQUIRE-20260916-001/trajectories.jsonl',ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json']}})
        result={'status':'DPO_DATA_REVIEW_AND_CANONICAL_ENCODING_PASSED','approved_pairs':len(approved),'held_pairs':1,
            'chosen_target_tokens':sum(p['chosen']['target_tokens'] for p in approved),'rejected_target_tokens':sum(p['rejected']['target_tokens'] for p in approved),
            'branch_turns':{s:sum(p[s]['turn_count'] for p in approved) for s in ['chosen','rejected']},
            'processed_tokens':sum(p[s]['processed_tokens'] for p in approved for s in ['chosen','rejected']),
            'max_sequence':max(p[s]['max_sequence_tokens'] for p in approved for s in ['chosen','rejected']),
            'seconds':time.perf_counter()-start,'GPU_hours':0,'API_calls':0,'parameter_updates':0,'GPU_DPO_qualified':False}
        save('result.json',result);print(json.dumps(result))
    except Exception:
        save('invalid_run.json',{'traceback':traceback.format_exc(),'model_run':False,'seconds':time.perf_counter()-start});raise


if __name__=='__main__':main()
