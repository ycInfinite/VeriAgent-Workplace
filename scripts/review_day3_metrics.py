"""Post-hoc, cohort-specific Codex semantic review of frozen DEV trajectories.

Labels below were assigned by Codex after reading complete B0/B1 action/observation
sequences. They are evaluation annotations, never policy instructions or training data.
Raw automatic candidate metrics are retained unchanged in each experiment.
"""
import csv
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
import re
import statistics

ROOT=Path(__file__).resolve().parents[1]
DOMAINS=['customer_relationship_manager','project_management','company_directory','analytics','calendar','email']

BAD_B0={184:[1],356:[2],414:[1,2],669:[3],1:[1],684:[1],0:[1],314:[1],
        220:[1],1112:[2,3],918:[1],561:[3,4],1063:[2,3,4,5,6],12:[1],385:[1,2]}
BAD_B1={184:[1],356:[4],414:[1,2],669:[3],1:[1],684:[1],0:[1],314:[4,5,6],
        363:[5],1219:[4,5,6,7,8,9],220:[1],1112:[2],918:[1,2],561:[3,4],
        18:[1],1063:[2,3,4,5,6],12:[1,2],385:[1,2]}
REASONS={184:'Display name substituted for customer_id; no such record ID',
356:'Invented recipient addresses; recipient resolution was not performed',
414:'Unsupported pagination kwargs and an unresolved assignee name in an email field',
669:'Unsupported metric name rejected by create_plot',
1:'Searches the desired new event name rather than locating the existing event',
684:'Comma-joined status values are not a supported OR filter in this tool',
0:'Nonexistent placeholder/numeric email ID used before successful lookup',
314:'B0 uses an invented assignee email; B1 later modifies tasks owned by other people',
363:'Plot interval covers fewer than the requested four weeks',
1219:'B1 deletes past events although the request is limited to upcoming meetings',
220:'B0 invents contact/assignee attributes; B1 supplies the name Nadia as an email address',
1112:'Invented recipient; B0 also forwards an email from a different sender',
918:'Invented assignee email',561:'Unsupported metric identifiers and incorrect plot type for the reference goal',
18:'Search uses desired new name as an existing-name filter',
1063:'Deletes customers belonging to people other than Sofia',
12:'Invented assignee email; official no-op reward nevertheless equals one',
385:'Plot interval is not six weeks; acts without establishing the required condition'}
ROOT_CAUSES={510:'capability_denial_no_action',184:'identifier_type_confusion',356:'ungrounded_recipient',
414:'schema_argument_error',669:'metric_argument_error_then_context_limit',1:'target_value_used_as_lookup_filter',
684:'filter_composition_error',0:'missing_lookup_and_nonexistent_id',314:'ungrounded_assignee',
363:'temporal_argument_error',1219:'capability_denial_no_action',220:'unsupported_attribute_completion',
1112:'ungrounded_recipient_and_target_scope',918:'ungrounded_assignee',561:'metric_and_plot_type_error',
18:'target_value_used_as_lookup_filter',1063:'target_constraint_omission',952:'unbounded_read_context_limit',
385:'unverified_condition_and_temporal_error'}

def key(v):return json.dumps(v,sort_keys=True,ensure_ascii=False)

def identifier_review(r,initial):
    tables=deepcopy(initial);findings={}
    for c,event in zip(r['call_diagnostics'],r['events']):
        args=c['arguments'];name=c['name'];domain=next((d for d in DOMAINS if name.startswith(d+'_')),None)
        msgs=r['rounds'][c['turn']-1]['input_messages']
        visible=json.dumps([m for m in msgs if m['role'] in ('user','tool')],ensure_ascii=False)
        fields=[]
        for field,value in args.items():
            if not isinstance(value,str) or not value:continue
            if field.endswith('_id'):
                possible=set()
                for table,frame in tables.items():
                    if table.startswith(str(domain)+'.') and field in frame['columns']:
                        ix=frame['columns'].index(field);possible.update(str(row[ix]) for row in frame['data'])
                observed=bool(re.search(r'(?<![\w])'+re.escape(value)+r'(?![\w])',visible,re.I))
                fields.append({'field':field,'kind':'record_id','value':value,'exists_in_current_typed_column':value in possible,
                               'observed_in_user_or_tool_context':observed,'confirmed_error':value not in possible or not observed})
            email_field=field in ('recipient','assigned_to_email','participant_email','customer_email') or (
                         field=='new_value' and str(args.get('field','')).endswith('_email'))
            # CRM search explicitly supports substring filters; bare names there are textual filters.
            if email_field and not(name=='customer_relationship_manager_search_customers' and '@' not in value):
                parts=[x.strip() for x in value.split(',')]
                valid_type=all(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',x) for x in parts)
                observed=all(bool(re.search(r'(?<![\w])'+re.escape(x)+r'(?![\w])',visible,re.I)) for x in parts)
                fields.append({'field':field,'kind':'email_slot','value':value,'valid_email_shape':bool(valid_type),
                               'observed_in_user_or_tool_context':observed,'confirmed_error':not valid_type or not observed})
        findings[c['step']]=fields
        for table,delta in event['state_changes'].items():
            frame=tables[table]
            for removed in delta['removed_rows']:
                ix=next(i for i,row in enumerate(frame['data']) if key(row)==key(removed));frame['data'].pop(ix)
            frame['data'].extend(delta['added_rows']);frame['columns']=delta['columns_after']
    return findings

def gpu_samples(path):
    rows=[]
    for line in path.read_text().splitlines():
        r=json.loads(line)
        try:
            fields=next(csv.reader([r['sample']]))
            rows.append({'memory_mib':float(fields[2]),'utilization':float(fields[3]),'power_w':float(fields[4])})
        except (KeyError,ValueError,IndexError,StopIteration):pass
    return {'sample_count':len(rows),'mean_utilization_pct':statistics.mean(x['utilization'] for x in rows) if rows else None,
            'max_sampled_used_gib':max((x['memory_mib'] for x in rows),default=0)/1024,
            'scope':'Approximate one-second polling sample mean; includes loading and CPU/tool gaps'}

def review_run(run_id,condition):
    path=ROOT/'experiments'/run_id
    records=[json.loads(x) for x in (path/'trajectories.jsonl').read_text().splitlines() if x.strip()]
    initial=json.loads((path/'initial_state.json').read_text())
    annotations=[]
    for r in records:
        task=r['task_id'];seed=r['seed'];bad=deepcopy(BAD_B0 if condition=='B0' else BAD_B1)
        if condition=='B0':
            bad[363]=[2] if seed==42 else [5];bad[18]=[2] if seed==42 else [1]
            redundant={414:[2],122:[2],18:[3] if seed==43 else []}
            premature=task in [510,184,414,1,684,0,314,1219,918,561] or(task==18 and seed==42)
        else:
            redundant={356:[2,3],414:[2],1:[3],18:[3],918:[2],12:[2]}
            premature=task in [510,184,414,684,918,561]
        ids=identifier_review(r,initial)
        calls=[]
        for c in r['call_diagnostics']:
            step=c['step'];arg_error=step in bad.get(task,[])
            calls.append({'step':step,'name':c['name'],'wrong_argument_confirmed':arg_error,
                          'argument_reason':REASONS.get(task) if arg_error else None,
                          'wrong_tool_confirmed':False,
                          'wrong_tool_scope':'Unknown or functionally incompatible tool; premature use of a relevant tool is classified as missing prerequisite instead',
                          'redundant_confirmed':step in redundant.get(task,[]),
                          'redundancy_scope':'Exact ineffective retry or re-reading unchanged facts already present; broader useful queries are not penalized merely for differing from reference',
                          'identifier_fields':ids[step]})
        for step in bad.get(task,[]):assert 1<=step<=len(calls),(task,seed,step)
        reward=r['verifier']['official_reward']
        primary=ROOT_CAUSES.get(task) if reward==0 else None
        if condition=='B1' and task in (314,1219):primary='target_constraint_omission_after_partial_progress'
        if condition=='B1' and task==220:primary='identifier_type_confusion_name_as_email'
        if condition=='B1' and task==1112:primary='ungrounded_recipient'
        annotations.append({'run_id':run_id,'task_id':task,'seed':seed,'official_reward':reward,
                            'source_pool':'development','training_eligible':False,'calls':calls,
                            'primary_failure':primary,'premature_termination_confirmed':bool(premature and reward==0),
                            'premature_scope':'Voluntary abandonment after errors/failed lookup or unnecessary capability denial; caps and completed-but-wrong mutations separately reported',
                            'successful_recovery':reward==1 and any(c['wrong_argument_confirmed'] for c in calls) and task!=12,
                            'unsound_noop_success':reward==1 and task==12,
                            'confirmed_complete_subaction_before_failure':reward==0 and (task==669 or(condition=='B1' and task in (314,1219)))})
    return records,annotations

def metrics(records,anns):
    calls=[c for a in anns for c in a['calls']]
    record_calls=[c for c in calls if any(x['kind']=='record_id' for x in c['identifier_fields'])]
    email_calls=[c for c in calls if any(x['kind']=='email_slot' for x in c['identifier_fields'])]
    identity_calls=[c for c in calls if c['identifier_fields']]
    field_errors=lambda c,kind:any(x['confirmed_error'] for x in c['identifier_fields'] if x['kind']==kind)
    def ratio(num,den):return {'numerator':num,'denominator':den,'rate':num/den if den else None}
    n=len(records)
    return {'rollouts':n,'success':ratio(sum(a['official_reward']==1 for a in anns),n),
        'wrong_tool':ratio(sum(c['wrong_tool_confirmed'] for c in calls),len(calls)),
        'wrong_argument_semantic_review':ratio(sum(c['wrong_argument_confirmed'] for c in calls),len(calls)),
        'record_id_grounding_error':ratio(sum(field_errors(c,'record_id') for c in record_calls),len(record_calls)),
        'nonexistent_record_id':ratio(sum(any(x['kind']=='record_id' and not x['exists_in_current_typed_column'] for x in c['identifier_fields']) for c in record_calls),len(record_calls)),
        'email_slot_grounding_error':ratio(sum(field_errors(c,'email_slot') for c in email_calls),len(email_calls)),
        'combined_identifier_grounding_error':ratio(sum(any(x['confirmed_error'] for x in c['identifier_fields']) for c in identity_calls),len(identity_calls)),
        'grounding_affected_trajectories':ratio(sum(any(any(x['confirmed_error'] for x in c['identifier_fields']) for c in a['calls']) for a in anns),n),
        'redundant_action':ratio(sum(c['redundant_confirmed'] for c in calls),len(calls)),
        'retry_loop':ratio(sum(any(c['three_call_loop'] for c in r['call_diagnostics']) for r in records),n),
        'premature_termination_reviewed':ratio(sum(a['premature_termination_confirmed'] for a in anns),n),
        'successful_recoveries':sum(a['successful_recovery'] for a in anns),
        'unsound_noop_successes':sum(a['unsound_noop_success'] for a in anns),
        'primary_failure_counts':dict(Counter(a['primary_failure'] for a in anns if a['primary_failure'])),
        'avg_tool_steps':statistics.mean(r['tool_steps'] for r in records),
        'input_tokens':sum(r['input_tokens'] for r in records),'output_tokens':sum(r['output_tokens'] for r in records),
        'avg_latency_seconds':statistics.mean(r['trajectory_latency_seconds'] for r in records)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/day3-reviewed-v2');args=p.parse_args()
    out=(ROOT/args.out).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output outside workspace')
    out.mkdir(parents=True,exist_ok=False)
    b0,a0=review_run('Q0-B0-20260904-001','B0');b1,a1=review_run('Q0-B1-20260904-001','B1')
    def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    save('annotations.json',{'method':'Post-hoc Codex case-by-case review of all 161 calls and 72 trajectories, plus typed-ID/state checks; development only',
        'reviewer':'Codex','independent_human_review_completed':False,
        'supersedes':'reports/day3-reviewed (reviewer attribution wording and two B1 primary labels corrected; raw trajectories and metric counts unchanged)',
        'limitations':['One AI reviewer; no independent human adjudication or inter-annotator reliability estimate','Cohort-specific semantic labels, not a universal oracle',
                       'Grounded ID can still identify the wrong target; this is counted as a semantic argument/scope error',
                       'Partial progress is diagnostic; official success remains binary'],'B0':a0,'B1':a1})
    m={'B0_all':metrics(b0,a0),'B0_seed42':metrics([r for r in b0 if r['seed']==42],[a for a in a0 if a['seed']==42]),
       'B1_seed42':metrics(b1,a1)}
    for name,rid in [('B0_all','Q0-B0-20260904-001'),('B1_seed42','Q0-B1-20260904-001')]:
        m[name]['gpu_samples']=gpu_samples(ROOT/'experiments'/rid/'gpu_samples.jsonl')
    # Exact paired sign/McNemar test is exploratory, not a preregistered significance claim.
    old={r['task_id']:r for r in b0 if r['seed']==42}
    improved=sum(r['verifier']['official_reward']>old[r['task_id']]['verifier']['official_reward'] for r in b1)
    regressed=sum(r['verifier']['official_reward']<old[r['task_id']]['verifier']['official_reward'] for r in b1)
    d=improved+regressed
    p=min(1.0,2*sum(math.comb(d,k) for k in range(min(improved,regressed)+1))/2**d) if d else 1.0
    m['paired_exploratory']={'improved':improved,'regressed':regressed,'n':24,'exact_two_sided_p':p,
                              'interpretation':'Small selected development cohort; do not claim a general or significant gain'}
    save('metrics.json',m)
    print(json.dumps(m,indent=2))

if __name__=='__main__':main()
