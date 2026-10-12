"""Read completed S100/MIX100 results; no model calls or implicit semantic labels."""
import argparse,hashlib,json,statistics
from pathlib import Path
from run_day3 import ROOT,write
from review_day3_metrics import gpu_samples


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=(ROOT/a.out).resolve();assert out.is_relative_to(ROOT);out.mkdir(parents=True,exist_ok=False)
    report={'scope':'Development24 only;notsealedgeneralization','arms':{},
        'historical_S1_confound':'Newclone/driver595.58.03 vs original580.142;historicalcomparison notsolely data effect',
        'current_comparison':'S100 andMIX100 run on sameOct12clone/driver',
        'price_rmb_per_hour':None,'semantic_rates':'Freshreview required;oldlabels notused'}
    empty=[]
    for arm in ['S100','MIX100']:
        train=ROOT/'experiments'/f'SFT-{arm}-20261010-001';ev=ROOT/'experiments'/f'SFT-EVAL-{arm}-20261010-001'
        tr=read(train/'result.json');er=read(ev/'result.json')
        assert tr['status']=='SFT_TRAINING_COMPLETE_RELOAD_PASSED' and tr['optimizer_updates']==310
        assert er['status']=='MATCHED_DEV_EVAL_COMPLETE' and er['valid_rollouts']==48 and er['infra_invalid_rollouts']==0
        rows=[json.loads(x) for x in (ev/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(rows)==48 and all(r['online_replay_equal'] and not r['infra_invalid'] for r in rows)
        steps=[json.loads(x) for x in (train/'steps.jsonl').read_text().splitlines()]
        for r in rows:
            if not r['reference']:
                empty.append({'arm':arm,'task_id':r['task_id'],'task_uid':r['task_uid'],'seed':r['seed'],
                    'training_eligible':False,'request':r['initial_messages'][-1],'messages':r['messages'][len(r['initial_messages']):],
                    'events':r['events'],'official_reward':r['verifier']['official_reward'],'termination':r['termination'],
                    'initial_state_sha256':r['initial_state_sha256'],'final_state_sha256':r['final_state_sha256']})
        report['arms'][arm]={'training':tr,'evaluation':er,'training_gpu_polling':gpu_samples(train/'gpu_samples.jsonl'),
            'eval_gpu_polling':gpu_samples(ev/'gpu_samples.jsonl'),'steps_sha256':sha(train/'steps.jsonl'),
            'trajectories_sha256':sha(ev/'trajectories.jsonl'),'mean_sample_CE':statistics.mean(s['loss'] for s in steps),
            'CE_scope':'Per-example average,nottokenweighted;differentdatasets cannotrankpolicies byloss',
            'inference_GPUhours_per_official_success':er['gpu_hours']/er['verified_successes'] if er['verified_successes'] else None,
            'latency_scope':'UnmergedLoRA,endtoend trajectory includesCPU tools;exclude deployment/idle fromscript timings'}
    assert len(empty)==16
    report['total_script_GPUhours']=sum(x[k]['gpu_hours'] for x in report['arms'].values() for k in ['training','evaluation'])
    report['source_script_sha256']=sha(Path(__file__))
    write(out/'resources_and_results.json',report);write(out/'empty_reference_review_pack.json',empty)
    print(json.dumps({'status':'SUMMARY_WRITTEN_FRESH_SEMANTIC_REVIEW_PENDING','out':str(out),'empty_trajectories':16,'GPUhours':report['total_script_GPUhours']}))


if __name__=='__main__':main()
