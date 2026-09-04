"""Mechanical inventory/leakage audit. Never print held-out case contents."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import random
import re
import unicodedata
from common import ROOT, SOURCES, Run, card, load_rows, write_json

def normalized(text):
    return re.sub(r'\W+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip()

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def question(row):
    return '\n'.join(m['content'] for m in row['responses_create_params']['input'] if m['role']=='user')

def template(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[a-z]+',' EMAIL ',text)
    text = re.sub(r'"[^"\n]*"|(?<!\w)\'[^\'\n]+\'(?!\w)',' QUOTED ',text)
    text = re.sub(r'\d+',' NUMBER ',text)
    return normalized(text)

def run(run_id):
    seed=20260904
    exp=Run(run_id,card('Are task records and candidate splits usable without leakage?',
        'Pinned data are structurally valid; exact duplicates can be isolated; composition coverage may be insufficient',
        'Official source split and task/reference structure',
        ['row/unique counts','schema distributions','exact/template overlap','reference composition coverage'],
        'No silent duplicate leakage; any composition claim requires independent prerequisite annotation',seed=seed))
    try:
        raw={s:load_rows(s) for s in ('train','validation')}
        items=[]
        details={}
        for split, rows in raw.items():
            for i,row in enumerate(rows):
                q=question(row)
                names=[x['name'] for x in row['ground_truth']]
                args_ok=True
                for a in row['ground_truth']:
                    try:
                        args_ok &= isinstance(json.loads(a['arguments']),dict)
                    except Exception:
                        args_ok=False
                item={'source_split':split,'source_row_index':i,'source_id':row['id'],
                      'task_uid':f'{SOURCES["dataset_revision"]}:{split}:{i}',
                      'question_sha256':sha(normalized(q)),'template_sha256':sha(template(q)),
                      'category':row['category'],'reference_tools':names,
                      'reference_distinct_tools':len(set(names)),'reference_action_count':len(names),
                      'tool_schema_count':len(row['responses_create_params']['tools']),
                      'reference_arguments_json_objects':bool(args_ok)}
                items.append(item)
            details[split]={'rows':len(rows),'id_unique':len({r['id'] for r in rows}),
                            'categories':dict(Counter(r['category'] for r in rows))}
        train=[x for x in items if x['source_split']=='train']
        final=[x for x in items if x['source_split']=='validation']
        final_hash={x['question_sha256'] for x in final}
        final_templates={x['template_sha256'] for x in final}
        exact_cross=[x for x in train if x['question_sha256'] in final_hash]
        template_cross=[x for x in train if x['template_sha256'] in final_templates]
        for split in details:
            subset=[x for x in items if x['source_split']==split]
            details[split].update({'normalized_unique_questions':len({x['question_sha256'] for x in subset}),
                'template_groups':len({x['template_sha256'] for x in subset}),
                'reference_distinct_tool_count_distribution':dict(Counter(x['reference_distinct_tools'] for x in subset)),
                'reference_action_count_distribution':dict(Counter(x['reference_action_count'] for x in subset)),
                'reference_signatures':dict(Counter(' -> '.join(x['reference_tools']) for x in subset)),
                'tool_schema_count_distribution':dict(Counter(x['tool_schema_count'] for x in subset))})
        # Assign all reference/template relatives to one INTERNAL pool. Official validation stays sealed.
        groups=defaultdict(list)
        for x in train:
            if x['question_sha256'] in final_hash:
                x['pool']='quarantine_exact_official_validation_overlap'
            else:
                groups[x['template_sha256']].append(x)
        keys=sorted(groups)
        random.Random(seed).shuffle(keys)
        examples=[json.loads(l) for l in (ROOT/'vendor/Gym/resources_servers/workplace_assistant/data/example.jsonl').read_text().splitlines() if l.strip()]
        example_hashes={sha(normalized(question(r))) for r in examples}
        forced_dev={k for k in keys if any(x['question_sha256'] in example_hashes for x in groups[k])}
        counts=Counter()
        for key in keys:
            if key in forced_dev:
                for x in groups[key]:
                    x['pool']='development'
                counts['development']+=len(groups[key])
        for key in keys:
            if key in forced_dev:
                continue
            if counts['development']<100:
                pool='development'
            elif counts['checkpoint_validation']<100:
                pool='checkpoint_validation'
            elif counts['composition_reserve_UNQUALIFIED']<200:
                pool='composition_reserve_UNQUALIFIED'
            else:
                pool='training_candidate'
            for x in groups[key]:
                x['pool']=pool
            counts[pool]+=len(groups[key])
        for x in final:
            x['pool']='official_validation_SEALED'
        # 24 deterministic, stratified DEV IDs; no model outcomes involved.
        dev=[x for x in train if x.get('pool')=='development']
        bins=defaultdict(list)
        for x in sorted(dev,key=lambda x:(x['reference_action_count'],x['source_row_index'])):
            bins[x['category']].append(x)
        selected=[]
        # Keep the already-read first examples in development and in the educational sample.
        for x in dev:
            if x['source_row_index'] in (0,1):
                selected.append(x)
                bins[x['category']].remove(x)
        while len(selected)<min(24,len(dev)):
            for category in sorted(bins):
                if bins[category] and len(selected)<24:
                    # Alternate low/high reference length, without claiming it is true planning depth.
                    ix=0 if len(selected)%2==0 else -1
                    selected.append(bins[category].pop(ix))
        internal=defaultdict(set)
        for x in train:
            if not x['pool'].startswith('quarantine'):
                internal[x['template_sha256']].add(x['pool'])
        assertions={'internal_template_groups_disjoint':all(len(v)==1 for v in internal.values()),
                    'exact_final_overlap_removed_from_training':not any(x['question_sha256'] in final_hash for x in train if x['pool']=='training_candidate'),
                    'all_reference_arguments_are_json_objects':all(x['reference_arguments_json_objects'] for x in items),
                    'pilot_is_dev_only':all(x['pool']=='development' for x in selected)}
        manifest={'status':'PROVISIONAL_NOT_TRAINING_AUTHORIZATION','seed':seed,
                  'grouping':'normalized/delexicalized question; conservative heuristic, not semantic proof',
                  'composition_status':'UNQUALIFIED: reference tool sequences omit prerequisite lookups',
                  'records':items}
        write_json(exp.path/'split_manifest.json',manifest)
        write_json(exp.path/'pilot_dev24.json',{'source_split':'train','indices':[x['source_row_index'] for x in selected],
                   'tasks':selected,'selection':'category and reference-action-count stratification; no model outcomes'})
        result={'splits':details,'cross_official_exact_train_rows':len(exact_cross),
                'cross_official_template_train_rows':len(template_cross),
                'template_overlap_is_a_warning_not_proof_of_identical_tasks':True,
                'near_semantic_duplicate_review':'NOT_COMPLETED_BY_THIS_HEURISTIC',
                'pool_counts':dict(Counter(x['pool'] for x in items)),
                'pilot_tasks':len(selected),'pilot_categories':dict(Counter(x['category'] for x in selected)),
                'assertions':assertions,'composition_qualification':'REQUIRES_PREREQUISITE_GRAPH_REVIEW'}
        exp.finish(result)
        print(json.dumps({k:v for k,v in result.items() if k!='splits'},indent=2))
    except Exception as exc:
        exp.finish({'error_type':type(exc).__name__,'error':str(exc)},'infrastructure_invalid')
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
