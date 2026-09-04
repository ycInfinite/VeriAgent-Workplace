"""Conservative split exclusion from recorded metadata; no final case content needed."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
import json
from common import ROOT,Run,card,write_json

def run(run_id):
    exp=Run(run_id,card('Can flagged lexical overlap be quarantined without rewriting official tasks?',
        'A conservative manifest can exclude all flagged training relatives and final relatives of already exposed dev cases',
        'Membership only, using pre-existing similarity metadata',
        ['pool counts','remaining flagged edges','pilot write/no-op strata'],
        'Zero retained flagged edges; composition reserve remains unqualified; no claim of zero semantic overlap',seed=20260904))
    try:
        original=json.loads((ROOT/'experiments/Q0-DATA-20260904-001/split_manifest.json').read_text())
        pairs=json.loads((ROOT/'experiments/Q0-CONTRACT-20260904-001/near_duplicate_metadata_only.json').read_text())
        exposed=set(json.loads((ROOT/'experiments/Q0-DATA-20260904-001/pilot_dev24.json').read_text())['indices'])|set(range(5))
        records=deepcopy(original['records'])
        by_train={r['source_row_index']:r for r in records if r['source_split']=='train'}
        blocked_templates={by_train[p['train_index']]['template_sha256'] for p in pairs}
        blocked_validation={p['official_validation_index'] for p in pairs if p['train_index'] in exposed}
        for r in records:
            r['previous_pool']=r['pool']
            if r['source_split']=='train' and r['template_sha256'] in blocked_templates:
                r['pool']='quarantine_lexical_overlap_or_template_relative'
                r['exclusion_reason']='Conservative exclusion, not a finding that the task is a duplicate'
            if r['source_split']=='validation' and r['source_row_index'] in blocked_validation:
                r['pool']='official_validation_exposed_relative_QUARANTINE'
                r['exclusion_reason']='Lexically close to a previously read/scripted dev example; preserve exposure history'
        dev=[r for r in records if r['pool']=='development']
        bins=defaultdict(list)
        for r in sorted(dev,key=lambda r:(r['reference_action_count'],r['source_row_index'])):
            if r['reference_action_count']>0:
                bins[r['category']].append(r)
        selected=[]
        while len(selected)<20 and any(bins.values()):
            for k in sorted(bins):
                if bins[k] and len(selected)<20:
                    selected.append(bins[k].pop(0 if len(selected)%2==0 else -1))
        noops=defaultdict(list)
        for r in sorted(dev,key=lambda x:x['source_row_index']):
            if r['reference_action_count']==0:
                noops[r['category']].append(r)
        # Four no-op cases across available domains, not simply the first alphabetic category.
        while len(selected)<24 and any(noops.values()):
            category_counts=Counter(r['category'] for r in selected)
            key=min((k for k in noops if noops[k]),key=lambda k:(category_counts[k],k))
            selected.append(noops[key].pop(0))
        for r in dev:
            if len(selected)>=24:
                break
            if r not in selected:
                selected.append(r)
        training={r['source_row_index'] for r in records if r['pool']=='training_candidate'}
        remaining=[p for p in pairs if p['train_index'] in training]
        write_json(exp.path/'split_manifest.json',{'status':'CPU_PREPARED_NOT_TRAINING_AUTHORIZATION','records':records,
            'composition_status':'UNQUALIFIED_DO_NOT_REPORT_COMPOSITION_GENERALIZATION',
            'official_validation_policy':'filtered project final subset; never label it the full official score',
            'semantic_duplicate_freedom':'NOT_PROVEN','source_manifest':'Q0-DATA-20260904-001',
            'similarity_evidence':'Q0-CONTRACT-20260904-001','previous_exposed_train_indices':sorted(exposed)})
        write_json(exp.path/'pilot_dev24.json',{'source_split':'train','indices':[r['source_row_index'] for r in selected],
            'tasks':selected,'selection':'deterministic category/reference-length strata after conservative exclusion',
            'requires_model_qualification':True})
        result={'pool_counts':dict(Counter(r['pool'] for r in records)),'remaining_flagged_training_edges':len(remaining),
                'quarantined_template_groups':len(blocked_templates),'exposed_final_relatives_quarantined':len(blocked_validation),
                'pilot_tasks':len(selected),'pilot_nonempty_reference':sum(r['reference_action_count']>0 for r in selected),
                'pilot_empty_reference':sum(r['reference_action_count']==0 for r in selected),
                'pilot_categories':dict(Counter(r['category'] for r in selected)),
                'gpu_gate':'NOT_APPROVED; composition research scope requires user decision; model evidence absent'}
        assert not remaining
        assert len(selected)==24
        exp.finish(result);print(json.dumps(result,indent=2))
    except Exception as exc:
        exp.finish({'error_type':type(exc).__name__,'error':str(exc)},'infrastructure_invalid');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
