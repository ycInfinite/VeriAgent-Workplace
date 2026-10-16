"""CPU data isolation, masks, old-artifact preservation and label rejection gates."""
import gzip,hashlib,json
from common import ROOT
from veriagent.dpo import load_pairs
from veriagent.sft_data import content_sha256
from veriagent.sft_stage import read,sha


def main():
    out=ROOT/'experiments/S1-EXPAND-REVIEW-20261016-001';cfg,pairs=load_pairs('configs/preference_expanded_data.json')
    with gzip.open(ROOT/cfg['same_reward_artifact'],'rt',encoding='utf-8') as f:same=list(map(json.loads,f))
    allpairs=pairs+same;uids={p['task_uid'] for p in allpairs}
    s1={p['task_uid'] for p in read(ROOT/'experiments/SFT-READY-20260917-001/selection.json')['S1']['tasks']}
    dev=set(read(ROOT/'configs/current_s1_preference_plan.json')['evaluation']['task_uids'])
    pool={p['task_uid']:p['pool'] for p in read(ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json')['records']}
    held={50,1135,1036,811,329,416}
    checks={'29_rewardgap4_separate_same':len(pairs)==29 and len(same)==4,
        '33_unique_tasks':len(uids)==len(allpairs)==33,'training_only_no_S1train_or_dev':not uids&(s1|dev) and all(pool[u]=='training_candidate' for u in uids),
        'all_six_holds_excluded':not held&{p['task_id'] for p in allpairs},
        'all_complete_and_no_truncation':all(p[s]['termination']=='assistant_final' and p[s]['max_sequence_tokens']<=8192 for p in allpairs for s in ['chosen','rejected']),
        'all_context_masked':all(e['labels'][:e['prefix_tokens']]==[-100]*e['prefix_tokens'] for p in allpairs for s in ['chosen','rejected'] for e in p[s]['encoded_turns']),
        'whole_assistant_targets':all(e['labels'][e['prefix_tokens']:]==e['input_ids'][e['prefix_tokens']:] for p in allpairs for s in ['chosen','rejected'] for e in p[s]['encoded_turns']),
        'all182_replayed':read(ROOT/'experiments/S1-EXPAND-REPLAY-20261016-001/result.json')['branches']==182}
    original=ROOT/'experiments/S1-PAIR-REVIEW-20261016-001'
    checks['prior6plus1_unmodified']=all(sha(original/n)==h for n,h in read(out/'manifest.json')['prior_source_hashes'].items())
    fixture={**cfg,'pair_artifact':cfg['same_reward_artifact'],'pair_artifact_sha256':sha(ROOT/cfg['same_reward_artifact']),'approved_pairs':4}
    path=out/'same_reward_loader_rejection_fixture.json'
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(fixture,f,indent=2)
    try:load_pairs(str(path.relative_to(ROOT)));checks['old_loader_rejects_same_reward']=False
    except ValueError as e:checks['old_loader_rejects_same_reward']=str(e)=='Invalid preference labels'
    students={p['task_uid']:p for p in map(json.loads,(ROOT/'experiments/S1-EXPAND-ACQUIRE-20261016-001/trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
    snapshots=[]
    for p in (ROOT/'evidence/preference-expansion-20261016/snapshots').glob('*.jsonl'):
        meta=read(p.with_suffix('.json'));assert sha(p)==meta['sha256']
        rows=list(map(json.loads,p.read_text(encoding='utf-8').splitlines()))
        assert all(content_sha256(x)==content_sha256(students[x['task_uid']]) for x in rows)
        snapshots.append({'file':str(p.relative_to(ROOT)),'records':len(rows),'sha256':sha(p)})
    checks['review_snapshots_match_final_raw']=sum(x['records'] for x in snapshots)==85
    assert all(checks.values()),checks
    result={'checks':checks,'passed':len(checks),'snapshots':snapshots,'GPU_hours':0,'parameter_updates':0,'actual_HF_GPU_training_validation':False}
    with (out/'cpu_controls.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2)
    print(json.dumps({'passed':len(checks),'pairs':len(pairs),'same_reward':len(same)}))


if __name__=='__main__':main()
