"""Admit reviewed whole no-op traces and propose one budget-matched mixed100 dataset."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip,hashlib,json,time,traceback
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from common import ROOT
from veriagent.sft_stage import read,sha,validate_example,schedule
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import CanonicalTeacherEncoder,export_teacher_turns

OUT=ROOT/'experiments/NOOP-REVIEW-20261010-001'
SOURCE=ROOT/'experiments/DEEPSEEK-SFTDATA-20260917-001'
BASE=ROOT/'experiments/SFT-SCALE-PREP-20261010-002'

def write(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def gzwrite(name,rows):
    with (OUT/name).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:
        for row in rows:f.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())


def main():
    assert not (OUT/'identity.json').exists(),'Immutable audit/export already executed'
    start=time.perf_counter();manifest=read(OUT/'manifest.json');judgments=read(OUT/'judgments.json')
    write('identity.json',{'started_at':datetime.now(timezone.utc).isoformat(),'repository_base':'18486681c862d445e40ab9c42945c6308fab8b8a',
        'working_tree_dirty':True,'script_sha256':sha(Path(__file__)),'config_sha256':sha(OUT/'config.json'),
        'manifest_sha256':sha(OUT/'manifest.json'),'judgments_sha256':sha(OUT/'judgments.json'),'kind':'CPU_ONLY'})
    try:
        for path,h in manifest['frozen_S100_sha256'].items():assert sha(ROOT/path)==h,'S100 changed'
        assert sha(SOURCE/'trajectories.jsonl')==manifest['source_sha256']
        records={x['task_uid']:x for x in map(json.loads,(SOURCE/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        assert {x['task_uid'] for x in manifest['tasks']}=={u for u,r in records.items() if not r['reference']}
        assert set(judgments)=={str(x['task_id']) for x in manifest['tasks']} and len(judgments)==83
        tc=read(SOURCE/'config.json');cohort={x['task_uid']:x for x in read(ROOT/tc['cohort_manifest'])['tasks']}
        enc=CanonicalTeacherEncoder(8192);approved=[];held=[];corpus=[];examples={}
        for task in manifest['tasks']:
            r=records[task['task_uid']];j=judgments[str(task['task_id'])]
            assert content_sha256(r)==task['trajectory_sha256'] and not r['reference']
            assert cohort[r['task_uid']]['pool']=='training_candidate' and cohort[r['task_uid']]['source_split']=='train'
            entry={**task,**j,'reviewer':'Codex','independent_human_review':False}
            if j['decision']!='approve':held.append(entry);continue
            assert j['review_scope'].startswith('full_visible_trace')
            assert r['verifier']['official_reward']==1 and r['termination']=='assistant_final' and not r['infra_invalid']
            assert r['online_replay_equal'] and r['events'] and all(not e['state_changes'] for e in r['events'])
            assert r['final_state_sha256']==r['initial_state_sha256']
            assert all(c['executable_gate'] for c in r['call_diagnostics'])
            review={'task_id':r['task_id'],'task_uid':r['task_uid'],'trajectory_sha256':task['trajectory_sha256'],
                'source_run':SOURCE.name,'source_pool':'training_candidate','reviewer':'Codex','independent_human_review':False,
                'whole_semantic_review_done':True,'decision':'approved_for_sft','rationale':j['rationale'],
                'grounding_checked':True,'target_scope_checked':True,'all_supervised_turns_acceptable':True,
                'review_protocol':'NOOP83_FULL_VISIBLE_AND_CONDITION_AUDIT_V1','empty_reference':True}
            flat=export_teacher_turns(r,review,cohort,enc,tc,source_provider='deepseek',required_decision='approved_for_sft')
            for e in flat:
                e.update(source_run=SOURCE.name,student_model_revision=enc.checked.model_revision);validate_example(e)
            examples[r['task_uid']]=flat;approved.append(review)
            corpus.append({'task_id':r['task_id'],'task_uid':r['task_uid'],'trajectory_sha256':task['trajectory_sha256'],
                'category':task['category'],'source_run':SOURCE.name,'source_pool':'training_candidate','empty_reference':True,
                'turns':len(flat),'processed_tokens':sum(e['processed_tokens'] for e in flat),
                'supervised_tokens':sum(e['supervised_tokens'] for e in flat),'max_sequence':max(e['processed_tokens'] for e in flat)})
        write('quality_approvals.json',{'approved':approved,'held':held,'all83_disposed':True,
            'full_semantic_review_approvals_only':True,'structural_holds_not_claimed_full_semantic_review':True})
        write('noop_corpus.json',{'tasks':corpus,'counts_by_domain':dict(Counter(x['category'] for x in corpus))})
        gzwrite('noop_examples.jsonl.gz',[e for x in corpus for e in examples[x['task_uid']]])
        original=read(BASE/'selection.json')['S100'];positive=[{**x,'empty_reference':False} for x in original['tasks']]
        with gzip.open(BASE/'s100_examples.jsonl.gz','rt',encoding='utf-8') as f:
            for e in map(json.loads,f):examples.setdefault(e['task_uid'],[]).append(e)
        items=positive+corpus;domains=sorted({x['category'] for x in positive});vectors=[];lower=[];upper=[]
        for d in domains:vectors.append([int(x['category']==d) for x in items]);lower.append(20);upper.append(20)
        for k in ['turns','processed_tokens','supervised_tokens']:
            vectors.append([x[k] for x in items]);tol=0 if k=='turns' else .02
            lower.append(original['totals'][k]*(1-tol));upper.append(original['totals'][k]*(1+tol))
        vectors.append([int(x['empty_reference']) for x in items]);lower.append(10);upper.append(20)
        objective=np.array([-int(x['empty_reference'])+int(hashlib.sha256(('mix100-v1:'+x['task_uid']).encode()).hexdigest()[:8],16)/2**32/10000 for x in items])
        result=milp(c=objective,integrality=np.ones(len(items)),bounds=Bounds(0,1),
            constraints=LinearConstraint(np.array(vectors),np.array(lower),np.array(upper)),options={'time_limit':60,'mip_rel_gap':0.0})
        mixed=None
        if result.x is not None:
            selected=sorted([x for x,z in zip(items,result.x) if z>.5],key=lambda x:x['task_id'])
            totals={k:sum(x[k] for x in selected) for k in ['turns','processed_tokens','supervised_tokens']}
            count=sum(x['empty_reference'] for x in selected)
            assert len(selected)==100 and 10<=count<=20 and totals['turns']==310
            assert Counter(x['category'] for x in selected)==Counter({d:20 for d in domains})
            assert all(abs(totals[k]/original['totals'][k]-1)<=.020001 for k in ['processed_tokens','supervised_tokens'])
            rows=[e for t in selected for e in examples[t['task_uid']]];assert len(rows)==310
            gzwrite('mixed100_examples.jsonl.gz',rows)
            mixed={'tasks':selected,'totals':totals,'noops':count,'retained_S100':100-count,
                'data_path':str((OUT/'mixed100_examples.jsonl.gz').relative_to(ROOT)).replace('\\','/'),
                'data_sha256':sha(OUT/'mixed100_examples.jsonl.gz'),'full_trajectory_targets':True}
            write('mixed100_selection.json',{'MIX100':mixed,'removed_S100_task_ids':sorted({x['task_id'] for x in positive}-{x['task_id'] for x in selected}),
                'solver_status':int(result.status),'mip_gap':float(result.mip_gap),
                'relative_tokens_vs_S100':{k:totals[k]/original['totals'][k]-1 for k in ['processed_tokens','supervised_tokens']}})
        else:write('mixed100_infeasible.json',{'status':int(result.status),'message':str(result.message),'constraints_not_relaxed':True})
        for path,h in manifest['frozen_S100_sha256'].items():assert sha(ROOT/path)==h,'S100 changed'
        summary={'status':'REVIEW_AND_ENCODING_COMPLETE','reviewed_candidates':83,'approved':len(approved),'held':len(held),
            'full_visible_semantic_dispositions':sum(j['review_scope'].startswith('full_visible_trace') for j in judgments.values()),
            'hold_categories':dict(Counter(x['category'] for x in held)),
            'approved_by_domain':dict(Counter(x['category'] for x in corpus)),
            'approved_total_turns':sum(x['turns'] for x in corpus),'mixed100_feasible':mixed is not None,
            'mixed_noops':mixed['noops'] if mixed else None,'S100_hashes_unchanged':True,
            'GPU_hours':0,'API_requests':0,'parameter_updates':0,'CPU_seconds':time.perf_counter()-start}
        write('result.json',summary);print(json.dumps(summary))
    except Exception:
        write('invalid_run.json',{'traceback':traceback.format_exc(),'GPU_hours':0,'parameter_updates':0});raise


if __name__=='__main__':main()
