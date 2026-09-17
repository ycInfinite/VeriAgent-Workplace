"""Freeze ALL remaining training candidates; deduplicate schemas, never use held-out cases."""
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json

from common import ROOT,Run,card,load_rows,write_json
from veriagent.sft_data import content_sha256
from veriagent.teacher_data import teacher_request,CanonicalTeacherEncoder

RUN='DEEPSEEK-POOL-PREP-20260917-001'


def main():
    exp=Run(RUN,card('Can all remaining training candidates be frozen without split leakage?',
        'The743-member training pool minus the20 attempted tasks leaves723 new tasks.',
        'Expand acquisition coverage to all remaining training candidates',
        ['pool membership','deduplication','schema roundtrip','initial token coverage','domain counts'],
        'All selected cases are frozen training members,none overlap prior20,and every initial input fits8192.',
        experiment_kind='CPU_POOL_FREEZE_NOT_MODEL_EVAL',seed=20260917))
    split_path=ROOT/'experiments/Q0-SPLIT-20260904-003/split_manifest.json'
    split=json.loads(split_path.read_text(encoding='utf-8'))
    old=json.loads((ROOT/'experiments/SFT-PREP-20260910-001/acquisition_manifest.json').read_text(encoding='utf-8'))
    excluded={t['task_uid'] for t in old['tasks']}
    train=[m for m in split['records'] if m['pool']=='training_candidate']
    assert len(train)==743 and len(excluded)==20
    groups=defaultdict(list)
    for m in train:
        if m['task_uid'] not in excluded:groups[m['category']].append(m)
    for group in groups.values():
        group.sort(key=lambda m:hashlib.sha256(f"20260917:{m['task_uid']}".encode()).hexdigest())
    selected=[]
    for i in range(max(map(len,groups.values()))):
        for category in sorted(groups):
            if i<len(groups[category]):selected.append(groups[category][i])
    assert len(selected)==723 and len({m['task_uid'] for m in selected})==723
    raw=load_rows('train')
    encoder=CanonicalTeacherEncoder(8192)
    metadata=[];packed=[];schemas={}
    for m in selected:
        assert m['source_split']=='train' and m['pool']=='training_candidate'
        row=deepcopy(raw[m['source_row_index']]);assert row['id']==m['source_id']
        row.update({'task_uid':m['task_uid'],'source_pool':'training_candidate'})
        messages=deepcopy(row['responses_create_params']['input'])
        messages[0]['content']+='\n\n'+old['B1_addition']
        tools=row['responses_create_params']['tools']
        text=encoder.inspector.render(messages,tools,generate=True)
        n=len(encoder.inspector.tokenizer.encode(text,add_special_tokens=False).ids)
        entry={**m,'initial_messages_sha256':content_sha256(messages),'tool_schemas_sha256':content_sha256(tools),
               'initial_prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),
               'initial_input_tokens':n,'initial_context_fits':n<8192,
               'empty_reference_requires_semantic_review':m['reference_action_count']==0}
        teacher_request(row,entry,old['B1_addition'])
        metadata.append(entry)
        schema_id=content_sha256(tools)
        if schema_id in schemas:assert schemas[schema_id]==tools
        schemas[schema_id]=tools
        compressed=deepcopy(row)
        del compressed['responses_create_params']['tools']
        compressed['tool_schema_ref']=schema_id
        restored=deepcopy(compressed);restored['responses_create_params']['tools']=schemas[restored.pop('tool_schema_ref')]
        assert restored==row
        packed.append(compressed)
    cohort={'status':'FROZEN_REMAINING_TRAINING_POOL','selection_seed':20260917,'rollout_seed':None,
            'B1_addition':old['B1_addition'],'split_manifest_sha256':hashlib.sha256(split_path.read_bytes()).hexdigest(),
            'training_pool_total':743,'excluded_task_uids':sorted(excluded),'max_rollouts':723,
            'selection_rule':'All remaining training candidates; SHA order within domains,round-robin across domains; no score-based selection',
            'tasks':metadata}
    write_json(exp.path/'cohort.json',cohort)
    write_json(exp.path/'tool_schemas.json',schemas)
    (exp.path/'tasks.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in packed),encoding='utf-8')
    coverage={'total':723,'initial_fits':sum(m['initial_context_fits'] for m in metadata),
              'max_initial_student_tokens':max(m['initial_input_tokens'] for m in metadata),
              'by_domain':dict(Counter(m['category'] for m in metadata)),
              'empty_reference_tasks':sum(m['reference_action_count']==0 for m in metadata),
              'reference_action_count_histogram':dict(Counter(m['reference_action_count'] for m in metadata))}
    write_json(exp.path/'coverage.json',coverage)
    payloads={name:{'sha256':hashlib.sha256((exp.path/name).read_bytes()).hexdigest(),'bytes':(exp.path/name).stat().st_size}
              for name in ('cohort.json','tasks.jsonl','tool_schemas.json')}
    assert all(v['bytes']<=2_000_000 for v in payloads.values())
    assert coverage['initial_fits']==723,'Coverage failure; no truncation or replacement'
    exp.finish({'status':'PASSED','coverage':coverage,'payloads':payloads,'model_requests':0,
                'dev_validation_final_bfcl_cases_selected':0,'parameter_updates':0,'gpu_hours':0})
    print(json.dumps({'status':'PASSED','coverage':coverage,'payloads':payloads}))


if __name__=='__main__':main()
