"""Freeze reviewed whole-trajectory S1/S2 inputs. CPU only, no training/API."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip,hashlib,importlib.metadata,json,random,re
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from common import ROOT,write_json
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import CanonicalTeacherEncoder,export_teacher_turns

RUN='SFT-READY-20260917-001'
SOURCE='DEEPSEEK-SFTDATA-20260917-001'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def features(record):
    calls=record['call_diagnostics'];names=[c['name'] for c in calls]
    writes=[c for c in calls if any(x in c['name'] for x in ('_update_','_delete_','_forward_','_reply_','_send_','_create_','_add_'))]
    ids={str(v) for c in writes for k,v in c['arguments'].items() if k.endswith('_id')}
    searches=[c for c in calls if '_search_' in c['name']]
    f={'directory_grounding':int('company_directory_find_email_address' in names),
       'entity_lookup_before_action':int(bool(searches) and bool(writes)),
       'multiple_target_entities':int(len(ids)>1),
       'composed_scope_predicate':int(any(len([v for v in c['arguments'].values() if v not in ('',None)])>=2 for c in searches)),
       'temporal_scope':int(any(any(k in c['arguments'] for k in ('time_min','date_min')) for c in searches)
                           or any('overdue' in m.get('content','').lower() for m in record['initial_messages'] if m['role']=='user'))}
    weights={'directory_grounding':4,'entity_lookup_before_action':2,'multiple_target_entities':3,
             'composed_scope_predicate':2,'temporal_scope':2}
    return f,sum(weights[k]*v for k,v in f.items())


def totals(items):
    return {key:sum(x[key] for x in items) for key in ['turns','processed_tokens','supervised_tokens','target_score']}


def gzwrite(path, rows):
    with path.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as stream:
        for row in rows:stream.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())


def main():
    out=ROOT/'experiments'/RUN;source=ROOT/'experiments'/SOURCE
    assert not (out/'corpus_manifest.json').exists(),'Immutable output already exists'
    cfg=json.loads((source/'config.json').read_text(encoding='utf-8'))
    cohort=json.loads((ROOT/cfg['cohort_manifest']).read_text(encoding='utf-8'))
    tasks={t['task_uid']:t for t in cohort['tasks']}
    records=[json.loads(l) for l in (source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id={r['task_id']:r for r in records}
    mechanical=json.loads((source/'mechanical_screen.json').read_text(encoding='utf-8'))['trajectories']
    ms={r['task_id']:r for r in mechanical}
    judgments=json.loads((out/'semantic_judgments.json').read_text(encoding='utf-8'))
    review_manifest=json.loads((out/'review_manifest.json').read_text(encoding='utf-8'))
    assert set(judgments)=={str(t['task_id']) for t in review_manifest['tasks']} and len(judgments)==150
    approved=[];held=[];encoder=CanonicalTeacherEncoder(8192);examples={};items=[]
    for record in records:
        n=record['task_id'];judge=judgments.get(str(n))
        common={'task_id':n,'task_uid':record['task_uid'],'trajectory_sha256':content_sha256(record),
                'source_run':SOURCE,'source_pool':'training_candidate','reviewer':'Codex',
                'independent_human_review':False,'whole_semantic_review_done':judge is not None}
        if judge and judge['decision']=='approve':
            assert not ms[n]['mechanical_flags'] and not ms[n]['empty_reference_requires_semantic_review']
            review={**common,'decision':'approved_for_sft','rationale':judge['rationale'],
                    'grounding_checked':True,'target_scope_checked':True,'all_supervised_turns_acceptable':True,
                    'review_protocol':'frozen150_full_visible_trace_review_v1'}
            ex=export_teacher_turns(record,review,tasks,encoder,cfg,
                source_provider='deepseek',required_decision='approved_for_sft')
            for e in ex:
                npre=e['prefix_tokens'];assert e['labels'][:npre]==[-100]*npre
                assert e['labels'][npre:]==e['input_ids'][npre:]
                assert len(e['input_ids'])<=8192 and e['input_ids'][-1] in encoder.checked.eos_ids
                assert len(e['input_ids'])==len(e['labels'])==len(e['attention_mask'])
                assert sum(v!=-100 for v in e['labels'])==e['supervised_tokens']
                e['source_run']=SOURCE
            approved.append(review);examples[n]=ex
            f,score=features(record)
            items.append({**common,'category':tasks[record['task_uid']]['category'],'turns':len(ex),
                'processed_tokens':sum(e['processed_tokens'] for e in ex),
                'supervised_tokens':sum(e['supervised_tokens'] for e in ex),
                'max_sequence':max(e['processed_tokens'] for e in ex),'failure_coverage_features':f,'target_score':score})
        else:
            reason=judge['rationale'] if judge else ('Mechanical gate flags: '+','.join(ms[n]['mechanical_flags']) if ms[n]['mechanical_flags']
                    else 'Empty-reference semantic protocol not yet qualified' if ms[n]['empty_reference_requires_semantic_review']
                    else 'Outside frozen150 first-stage manual review; not reviewed,not rejected as incorrect')
            held.append({**common,'decision':'hold','rationale':reason,
                'category':judge.get('category') if judge else 'not_admitted_this_stage'})
    assert len(items)==137 and len(held)==586
    domains=sorted({x['category'] for x in items});by_domain=defaultdict(list)
    for x in items:by_domain[x['category']].append(x)
    rng=random.Random(42)
    s1=[]
    for domain in domains:
        pool=sorted(by_domain[domain],key=lambda x:x['task_id'])
        s1.extend(rng.sample(pool,10))
    target=totals(s1);ids1={x['task_id'] for x in s1}
    policy={'status':'FROZEN_BEFORE_SELECTION_SOLVE','random_seed':42,'tasks_per_domain':10,
        'S1':'Uniform without-replacement draw per domain from the137 whole-approved first-stage pool; no resampling',
        'S2':'Maximize fixed failure-coverage heuristic with binary whole-task selection and equal domain quotas',
        'weights':{'directory_grounding':4,'entity_lookup_before_action':2,'multiple_target_entities':3,
                   'composed_scope_predicate':2,'temporal_scope':2},
        'basis':'Day3 reviewedB0/B1 evidence: missing/incorrect identifiers,email slots,target/filter/temporal constraints and premature completion. Heuristic weights,not statistically estimated causal effects.',
        'base_failure_source':'reports/day3-reviewed-v2/metrics.json','base_failure_sha256':sha(ROOT/'reports/day3-reviewed-v2/metrics.json'),
        'equal_turns_required':True,'processed_and_supervised_token_relative_tolerance':0.02,
        'max_overlap_tasks':35,'max_solver_seconds':30,'training_result_or_eval_used_for_selection':False,
        'scipy_version':importlib.metadata.version('scipy'),'S1_reference_totals':target}
    write_json(out/'selection_policy.json',policy)
    vectors=[];lo=[];hi=[]
    for domain in domains:
        vectors.append([int(x['category']==domain) for x in items]);lo.append(10);hi.append(10)
    for key in ['turns','processed_tokens','supervised_tokens']:
        vectors.append([x[key] for x in items])
        tolerance=0 if key=='turns' else .02
        lo.append(target[key]*(1-tolerance));hi.append(target[key]*(1+tolerance))
    vectors.append([int(x['task_id'] in ids1) for x in items]);lo.append(0);hi.append(35)
    # Tiny fixed tie-breaker cannot outweigh one point of the integer primary score.
    objective=np.array([-x['target_score']+int(hashlib.sha256(str(x['task_id']).encode()).hexdigest()[:6],16)/2**24/10000 for x in items])
    result=milp(c=objective,integrality=np.ones(len(items)),bounds=Bounds(0,1),
        constraints=LinearConstraint(np.array(vectors),np.array(lo),np.array(hi)),
        options={'time_limit':30,'mip_rel_gap':0.0})
    assert result.x is not None,'No feasible token-matched selection; no random-arm redraw'
    s2=[x for x,v in zip(items,result.x) if v>.5];other=totals(s2)
    assert Counter(x['category'] for x in s2)==Counter(x['category'] for x in s1)
    assert other['turns']==target['turns'] and len(s2)==50
    assert all(abs(other[k]-target[k])/target[k]<=.0200001 for k in ['processed_tokens','supervised_tokens'])
    assert other['target_score']>target['target_score'] and len(ids1 & {x['task_id'] for x in s2})<=35
    reviews={'approved':approved,'held':held,'review_scope':'150full-visible-traces; other573 retain explicit nonadmission','training_started':False}
    write_json(out/'quality_approvals.json',reviews)
    write_json(out/'corpus_manifest.json',{'tasks':items,'whole_approved':137,'held':586,
        'source_sha256':sha(source/'trajectories.jsonl'),'judgments_sha256':sha(out/'semantic_judgments.json'),
        'source_cohort_sha256':sha(ROOT/cfg['cohort_manifest']),'student_revision':cfg['student_revision']})
    selection={}
    for arm,selected in [('S1',s1),('S2',s2)]:
        selected=sorted(selected,key=lambda x:x['task_id'])
        flat=[e for x in selected for e in examples[x['task_id']]]
        path=out/f'{arm.lower()}_examples.jsonl.gz';gzwrite(path,flat)
        selection[arm]={'tasks':selected,'totals':totals(selected),'data_path':str(path.relative_to(ROOT)).replace('\\','/'),
            'data_sha256':sha(path),'data_bytes':path.stat().st_size,'full_trajectory_targets':True}
    selection.update({'overlap_task_count':len(ids1 & {x['task_id'] for x in s2}),
        'solver_status':int(result.status),'solver_message':str(result.message),
        'solver_mip_gap':float(result.mip_gap),'relative_token_differences':{
            k:(other[k]-target[k])/target[k] for k in ['processed_tokens','supervised_tokens']},
        'no_parameter_updates':True})
    write_json(out/'selection.json',selection)
    summary={'status':'REVIEW_AND_EXPORT_READY_TRAINING_NOT_RUN','whole_reviewed':150,'approved':137,'held_all723':586,
        'approved_by_domain':dict(Counter(x['category'] for x in items)),'S1':target,'S2':other,
        'overlap':selection['overlap_task_count'],'relative_token_differences':selection['relative_token_differences'],
        'max_sequence':max(x['max_sequence'] for x in s1+s2),'parameter_updates':0,'gpu_hours':0,
        'api_requests':0,'created_at':datetime.now(timezone.utc).isoformat()}
    write_json(out/'export_summary.json',summary);print(json.dumps(summary))


if __name__=='__main__':main()
