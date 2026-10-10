"""Offline next-stage audit; never loads a model or calls a provider/tool server."""
from collections import Counter
from datetime import datetime, timezone
import gzip, hashlib, json, math, time, traceback
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from common import ROOT
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import CanonicalTeacherEncoder

OUT = ROOT / 'experiments/POSTSFT-AUDIT-20261010-001'
READY = ROOT / 'experiments/SFT-READY-20260917-001'
CHOSEN = 'DEEPSEEK-QUAL-20260917-001'
REJECTED = 'SFT-ACQUIRE-20260916-001'

# Fresh Codex review of the complete rejected message/tool sequences on2026-10-10.
REASONS = {
    565: ('premature_termination', 'Returns scalar average and asks whether a plot is needed despite explicit plot request.'),
    972: ('plot_type', 'Uses line charts for requested distributions; reviewed teacher uses histograms and achieves reference state.'),
    247: ('ungrounded_recipient', 'Invents lena@example.com instead of resolving actual participant; changes requested event title.'),
    859: ('nonexistent_identifier', 'Uses12345678 without lookup,then asks user for ID instead of locating event.'),
    123: ('wrong_lookup_predicate', 'Treats first meeting as literal event text; repeatedly broadens dates instead of ordering the requested date.'),
    770: ('identifier_type_confusion', 'Stores display name Lena in assigned_to_email instead of resolving email.'),
    271: ('target_scope_violation', 'Deletes observed customers belonging to Nadia,Lena andAkira although user specifiedRaj; roundcap is policy-budget termination,not infrastructure timeout.'),
    20: ('filter_composition', 'Uses Qualified,Won string instead of Qualified-or-Proposal,omits owner constraint,then abandons reassignment.'),
    177: ('ungrounded_recipient', 'Invents raj@atlas.com andolga@atlas.com; correct message ID alone is insufficient.'),
    76: ('nonexistent_identifier', 'Passes literal placeholder as email_id without searching.'),
    965: ('ungrounded_recipient', 'Invents dmitri@example.com; adds unsupported pagination arguments and falsely concludes no tasks.'),
    687: ('identifier_type_confusion', 'Uses name then invented jinsoo@company.com; unsupported page_size and false empty-result conclusion.'),
    8: ('identifier_type_confusion', 'Uses name then invented chenwei@company.com and claims no tasks.'),
}


def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(name):
    return [json.loads(x) for x in (ROOT/'experiments'/name/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
def save(name, value):
    with (OUT/name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
def packed(name, values):
    with (OUT/name).open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as f:
        for value in values: f.write((json.dumps(value, ensure_ascii=False)+'\n').encode())


def branch(record, encoder):
    """Policy-generated tokens only; branch-specific environment observations are context."""
    assert record['source_pool']=='training_candidate' and not record['infra_invalid']
    assert record['online_replay_equal'] and not record['parse_errors']
    messages=record['messages'];cursor=len(record['initial_messages']);event_index=0;examples=[]
    assert messages[:cursor]==record['initial_messages']
    for turn in record['rounds']:
        assert turn['input_messages']==messages[:cursor]
        assistant=messages[cursor];assert assistant['role']=='assistant'
        if 'assistant_message' in turn: assert assistant==turn['assistant_message']
        if 'eos_reached' in turn: assert turn['eos_reached'] is True
        example=encoder.encode(messages[:cursor],record['tool_schemas'],assistant)
        prefix=example['prefix_tokens'];assert example['labels'][:prefix]==[-100]*prefix
        assert example['labels'][prefix:]==example['input_ids'][prefix:]
        examples.append(example);cursor+=1
        for call in assistant.get('tool_calls',[]):
            event=record['events'][event_index];event_index+=1
            assert event['tool_call']['name']==call['function']['name']
            assert json.loads(event['tool_call']['arguments'])==call['function']['arguments']
            expected={'role':'tool','tool_call_id':call['id'],'content':json.dumps(event['observation'],ensure_ascii=False,default=str)}
            assert messages[cursor]==expected;cursor+=1
    assert cursor==len(messages) and event_index==len(record['events'])
    return {'messages':messages,'source_record_sha256':content_sha256(record),'verifier':record['verifier'],
        'termination':record['termination'],'tool_steps':record['tool_steps'],'turn_count':len(examples),
        'processed_tokens':sum(x['processed_tokens'] for x in examples),
        'target_tokens':sum(x['supervised_tokens'] for x in examples),
        'max_sequence_tokens':max(len(x['input_ids']) for x in examples),'encoded_turns':examples}


def main():
    assert not (OUT/'identity.json').exists(),'Immutable audit already executed'
    start=time.perf_counter();cfg=read(OUT/'config.json')
    sources=[READY/'quality_approvals.json',READY/'corpus_manifest.json',READY/'selection.json',
        ROOT/f'experiments/{CHOSEN}/quality_review.json',ROOT/f'experiments/{CHOSEN}/trajectories.jsonl',
        ROOT/f'experiments/{REJECTED}/trajectories.jsonl']
    sources += [ROOT/f'experiments/SFT-EVAL-{a}-20261010-001/trajectories.jsonl' for a in ['BASE','S1','S2']]
    save('identity.json',{'started_at':datetime.now(timezone.utc).isoformat(),'config_sha256':sha(OUT/'config.json'),
        'script_sha256':sha(Path(__file__)),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'model_revision':cfg['model_revision'],'dataset_revision':cfg['dataset_revision'],'kind':'CPU_ONLY'})
    try:
        approved=read(READY/'quality_approvals.json');corpus=read(READY/'corpus_manifest.json')['tasks'];selection=read(READY/'selection.json')
        ids={a:{x['task_uid'] for x in selection[a]['tasks']} for a in ['S1','S2']}
        assert len(corpus)==len(approved['approved'])==137
        pool=rows('DEEPSEEK-SFTDATA-20260917-001');teacher=rows(CHOSEN);student=rows(REJECTED)
        assert len(pool)==723 and len(teacher)==len(student)==20
        assert not {x['task_uid'] for x in pool}&{x['task_uid'] for x in teacher}
        with gzip.open(READY/'eval_dev24.jsonl.gz','rt',encoding='utf-8') as f:dev=[json.loads(x) for x in f]
        dev_ids={x['task_uid'] for x in dev}
        save('inventory.json',{'teacher_unique_tasks':743,'main_batch':723,'main_reviewed':150,
            'main_approved':137,'main_held':13,'main_unreviewed':573,'S1_tasks':50,'S2_tasks':50,
            'S1_S2_overlap':len(ids['S1']&ids['S2']),'S1_S2_unique':len(ids['S1']|ids['S2']),
            'main_approved_unused_by_both':137-len(ids['S1']|ids['S2']),
            'old20_whole_review_pass':len(read(ROOT/f'experiments/{CHOSEN}/quality_review.json')['approved']),
            'old20_export_was_not_admitted':True,'basis':'Exact manifests,not counts inferred from reward'})
        # One feasible nested100 proposal. No optimizer/model-score input used by this selector.
        candidates=[x for x in corpus if x['task_uid'] not in ids['S1']];domains=sorted({x['category'] for x in corpus})
        vectors=[];lo=[];hi=[];target=selection['S1']['totals']
        for d in domains:vectors.append([int(x['category']==d) for x in candidates]);lo.append(10);hi.append(10)
        for k in ['turns','processed_tokens','supervised_tokens']:
            vectors.append([x[k] for x in candidates]);t=0 if k=='turns' else .02
            lo.append(target[k]*(1-t));hi.append(target[k]*(1+t))
        objective=[int(hashlib.sha256(('nested100-v1:'+x['task_uid']).encode()).hexdigest()[:8],16)/2**32 for x in candidates]
        result=milp(c=np.array(objective),integrality=np.ones(len(candidates)),bounds=Bounds(0,1),
            constraints=LinearConstraint(np.array(vectors),np.array(lo),np.array(hi)),options={'time_limit':30,'mip_rel_gap':0.0})
        if result.x is None:save('nested100_proposal.json',{'status':'NO_FEASIBLE_PROPOSAL','solver_status':int(result.status)})
        else:
            extra=[x for x,z in zip(candidates,result.x) if z>.5];all_tasks=selection['S1']['tasks']+extra
            totals={k:sum(x[k] for x in all_tasks) for k in ['turns','processed_tokens','supervised_tokens']}
            assert len(extra)==50 and totals['turns']==310 and not {x['task_uid'] for x in all_tasks}&dev_ids
            assert Counter(x['category'] for x in all_tasks)==Counter({d:20 for d in domains})
            assert all(abs(totals[k]-2*target[k])/(2*target[k])<=.010001 for k in ['processed_tokens','supervised_tokens'])
            save('nested100_proposal.json',{'status':'FEASIBLE_MANIFEST_ONLY_NOT_TRAINED','original_S1_50_included':True,
                'tasks':sorted(all_tasks,key=lambda x:x['task_id']),'totals_one_epoch':totals,
                'versus_S1_two_epoch_relative_tokens':{k:totals[k]/(2*target[k])-1 for k in ['processed_tokens','supervised_tokens']},
                'solver_status':int(result.status),'selection_is_uniform_random':False,
                'interpretation':'More unique tasks,fewer repetitions at near-fixedtokens/steps;not a pure compute-scaling curve'})
        # Same-task preference candidates; approval of teacher hash does not imply GPU qualification.
        reviews={x['task_id']:x for x in read(ROOT/f'experiments/{CHOSEN}/quality_review.json')['approved']}
        chosen={x['task_id']:x for x in teacher};rejected={x['task_id']:x for x in student};encoder=CanonicalTeacherEncoder(8192)
        pairs=[];held=[]
        for task_id,r in rejected.items():
            c=chosen[task_id]
            if task_id not in reviews or r['verifier']['official_reward']!=0:
                held.append({'task_id':task_id,'reason':'teacher_review_held' if task_id not in reviews else 'both_official_success_no_pair_admission'});continue
            review=reviews[task_id];assert content_sha256(c)==review['trajectory_sha256']
            assert review['decision']=='whole_trajectory_quality_pass' and review['all_turns_reviewed']
            assert task_id in REASONS and c['task_uid']==r['task_uid'] and c['task_uid'] not in dev_ids
            for k in ['initial_messages','tool_schemas','initial_state_sha256']:assert c[k]==r[k],k
            assert c['verifier']['official_reward']==1 and c['termination']=='assistant_final'
            a=branch(c,encoder);b=branch(r,encoder)
            pairs.append({'pair_id':f'TRAIN-{task_id}-DSQUAL-vs-BASE-v1','task_id':task_id,'task_uid':c['task_uid'],
                'source_pool':'training_candidate','prompt_context':c['initial_messages'],'tools':c['tool_schemas'],
                'initial_state_sha256':c['initial_state_sha256'],'chosen_run':CHOSEN,'rejected_run':REJECTED,
                'chosen':a,'rejected':b,'failure_category':REASONS[task_id][0],'why_pair_valid':REASONS[task_id][1],
                'chosen_review':review,'rejected_review':'Codex full visible-message review2026-10-10;notindependenthuman',
                'status':'CPU_VERIFIED_CANDIDATE_NOT_GPU_TRAINING_ADMISSION','rejected_policy':'original_preSFT_BASE_not_currentS1'})
        assert len(pairs)==13
        packed('preference_candidates.jsonl.gz',pairs)
        metadata=[{k:v for k,v in p.items() if k not in ['chosen','rejected','prompt_context','tools']} |
            {s:{k:v for k,v in p[s].items() if k not in ['messages','encoded_turns']} for s in ['chosen','rejected']} for p in pairs]
        save('pair_manifest.json',{'pairs':metadata,'held':held,'training_admitted':False,
            'pair_archive_sha256':sha(OUT/'preference_candidates.jsonl.gz'),
            'source_bias':'chosen allDeepSeek,rejected alloldBase;length/style/provider confounding;13tasks only',
            'matched_control_required':'S1+chosen-onlySFT on same13 tasks versusS1+DPO;bothstartidenticalS1,otherwise extra-data confound'})
        beta=.1;loss=lambda margin:float(np.logaddexp(0,-beta*margin))
        checks={'initial_reference_equal_loss_ln2':abs(loss(0)-math.log(2))<1e-12,
            'better_relative_margin_lowers_loss':loss(1)<loss(0)<loss(-1),
            'all_context_labels_ignored':all(all(e['labels'][i]==-100 for i in range(e['prefix_tokens'])) for p in pairs for s in ['chosen','rejected'] for e in p[s]['encoded_turns']),
            'no_dev_in_pairs':not {p['task_uid'] for p in pairs}&dev_ids}
        assert all(checks.values());save('cpu_checks.json',{'checks':checks,'scope':'Scalarloss/mask checks only;noTorch,gradient,referencecache orGPUvalidation'})
        save('result.json',{'status':'OFFLINE_DATA_AND_PREFERENCE_CANDIDATES_VERIFIED','pairs':len(pairs),
            'chosen_target_tokens':sum(p['chosen']['target_tokens'] for p in pairs),'rejected_target_tokens':sum(p['rejected']['target_tokens'] for p in pairs),
            'max_branch_sequence':max(p[s]['max_sequence_tokens'] for p in pairs for s in ['chosen','rejected']),
            'CPU_seconds':time.perf_counter()-start,'GPU_hours':0,'API_requests':0,'parameter_updates':0,
            'full_semantic_call_rates':'not established by this audit','GPU_DPO_ready':False})
        print(json.dumps(read(OUT/'result.json')))
    except Exception:
        save('invalid_run.json',{'traceback':traceback.format_exc(),'CPU_seconds':time.perf_counter()-start,'model_run':False});raise


if __name__=='__main__': main()
