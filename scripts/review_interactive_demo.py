"""Post-hoc audit of the user's first interactive demo; no model requests/updates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tarfile

from common import ROOT, Run, card, write_json
from veriagent.environment import WorkplaceEnv, digest, snapshot
from veriagent.token_mask import TokenMaskInspector


def main():
    run = Run('INTERACTIVE-DEMO-20260916-001', card(
        'Did the user-initiated Token Plan demo perform grounded real actions, and is its data eligible?',
        'Tool execution may succeed even when client settings or recording are unsuitable for controlled SFT.',
        'Official interactive client and MCP wrapper, replacing the existing teacher collector',
        ['tool/verifier/state agreement','grounding','observed provider usage','configuration deviations',
         'recording completeness and training eligibility'],
        'Separate actual task success from admission and comparability; no automatic training.',
        experiment_kind='POSTHOC_CPU_AUDIT_OF_USER_INITIATED_DEMO',
        registration_timing='after user execution; NOT a preregistered B1 run',
        source_execution_commit='318e23376f5f8358e52fa3dead81227021597fb1'))
    archive = ROOT/'evidence/interactive-client/INTERACTIVE-DEMO-20260916-001-evidence.tar.gz'
    receipt = json.loads(archive.with_name('INTERACTIVE-DEMO-20260916-001-receipt.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['sha256']
    raw = {}; members = []
    with tarfile.open(archive) as source:
        manifest = json.load(source.extractfile('manifest.json'))
        for i, entry in enumerate(manifest['files']):
            payload = source.extractfile(entry['source_path']).read()
            assert hashlib.sha256(payload).hexdigest() == entry['sha256']
            raw[entry['source_path']] = payload
            name = f'{i:02}-' + Path(entry['source_path']).name
            (run.path/'raw').mkdir(exist_ok=True)
            (run.path/'raw'/name).write_bytes(payload)
            members.append({**entry,'local_file':'raw/'+name})
    write_json(run.path/'raw_manifest.json',{'files':members,'archive_sha256':receipt['sha256']})
    def get(suffix, lines=False):
        matches=[data for path,data in raw.items() if path.endswith(suffix)]
        assert len(matches)==1, suffix
        return ([json.loads(line) for line in matches[0].decode().splitlines() if line.strip()]
                if lines else json.loads(matches[0]))
    session=get('/INTERACTIVE-20260916T084345-9e606799/identity.json')
    result=get('/INTERACTIVE-20260916T084345-9e606799/result.json')
    events=get('/tool_events.jsonl',True)
    request=get('/task_request.json')
    chat=get('/e0f6ff46-e9c7-4ff6-af6a-185f7a031bf2.jsonl',True)
    main_usage=get('/token-usage-2026-09.jsonl',True)
    total_usage=get('/usage_record.jsonl',True)[0]['models']['qwen3.8-max']
    turns=[x for x in chat if x['type']=='assistant']
    calls=[p['functionCall'] for x in turns for p in x['message']['parts'] if 'functionCall' in p]
    responses={p['functionResponse']['id']:p['functionResponse'] for x in chat
               if x['type']=='tool_result' for p in x['message']['parts']}
    world=[c for c in calls if c['name']=='mcp__workplace__execute_workplace_tool']
    assert len(world)==len(events)==3
    for call,event in zip(world,events):
        assert call['args']['name']==event['tool_call']['name']
        assert call['args']['arguments']==json.loads(event['tool_call']['arguments'])
        observed=json.loads(responses[call['id']]['response']['output'])
        assert digest(observed['observation'])==digest(event['observation'])
    env=WorkplaceEnv()
    assert digest(env.initial_state)==session['initial_state_sha256']
    for event in events:
        replay=env.step(event['tool_call'])
        assert digest(replay['observation'])==digest(event['observation'])
        assert replay['state_after_sha256']==event['state_after_sha256']
    assert digest(snapshot(env.tools))==result['final_state_sha256']
    row=next(json.loads(l) for l in (ROOT/'data/sft_probe_train20.jsonl').read_text(encoding='utf-8').splitlines()
             if json.loads(l)['id']==707)
    assert env.verify(row['ground_truth'])['official_reward']==result['verifier']['official_reward']==1
    found=events[0]['observation']['customers']
    update=json.loads(events[1]['tool_call']['arguments'])
    assert len(found)==1 and update['customer_id']==found[0]['customer_id']
    assert update['field']=='status' and update['new_value']=='Proposal'
    assert events[2]['observation']['customers'][0]['status']=='Proposal'
    assert not events[0]['state_changes'] and not events[2]['state_changes']
    changed=events[1]['state_changes']
    assert len(changed)==1
    change=next(iter(changed.values()))
    assert len(change['removed_rows'])==len(change['added_rows'])==1
    a,b=change['removed_rows'][0],change['added_rows'][0]
    fields=[k for k,x,y in zip(change['columns_before'],a,b) if x!=y]
    assert fields==['status']
    sums={k:sum(x[k] for x in main_usage) for k in
          ['inputTokens','outputTokens','cachedTokens','thoughtsTokens','apiDurationMs']}
    first=next(c for c in calls if c['name']=='mcp__workplace__get_task')
    task_text=responses[first['id']]['response']['output']
    compact=json.dumps(json.loads(task_text),ensure_ascii=False,separators=(',',':'))
    inspector=TokenMaskInspector()
    reduction={'old_task_return_student_tokens':len(inspector.tokenizer.encode(task_text,add_special_tokens=False).ids),
               'compact_task_return_student_tokens':len(inspector.tokenizer.encode(compact,add_special_tokens=False).ids),
               'scope':'only equivalent tool-return text; not a complete new provider request'}
    audit={'status':'real_task_success_but_hold_for_controlled_training',
        'source':'user-initiated official Qwen Code session; no collector API automation',
        'task_id':707,'task_pool':'training_candidate','model_requested':'qwen3.8-max','model_revision':None,
        'client_session':turns[0]['sessionId'],'main_assistant_turns':len(turns),'workplace_calls':3,
        'mcp_calls_with_begin_finish':len(calls),'tool_errors':0,'official_reward':1,
        'grounding_checked':True,'actual_and_replay_states_match':True,'only_changed_field':'status',
        'readback_classification':'optional post-write confirmation; not a retry loop',
        'main_recorded_usage':sums,'main_recorded_responses':len(main_usage),
        'client_aggregate_usage':total_usage,
        'unreconciled_extra_usage':{'requests':total_usage['requests']-len(main_usage),
            'inputTokens':total_usage['inputTokens']-sums['inputTokens'],
            'outputTokens':total_usage['outputTokens']-sums['outputTokens'],
            'latencyMs':total_usage['totalLatencyMs']-sums['apiDurationMs'],
            'interpretation':'consistent with default follow-up suggestion; no per-request response evidence for strict attribution'},
        'max_recorded_input_tokens':max(x['inputTokens'] for x in main_usage),
        'recorded_context_windows':sorted({x['contextWindowSize'] for x in turns}),
        'inputs_over_8192':sum(x['inputTokens']>8192 for x in main_usage),
        'thinking_observed':sums['thoughtsTokens']>0,
        'formal_B1_eligible':False,'training_eligible':False,'infra_invalid':False,
        'protocol_invalid_for_controlled_non_thinking_8k':True,
        'admission_holds':['generation settings ignored by --bare','actual inputs exceed8192; thinking active',
                           'wrapper protocol and missing complete wire request differ from admitted source',
                           'extra aggregate request not present in main response log'],
        'compact_return_probe':reduction,'gpu_hours':0,'new_parameter_updates':0,
        'token_plan_credits':None,'incremental_model_rmb':None,
        'research_claim':'one selected debug task; no generalization or before/after improvement claim'}
    run.finish(audit)
    print(json.dumps({k:audit[k] for k in ['status','official_reward','workplace_calls','main_recorded_usage',
                                         'max_recorded_input_tokens','training_eligible','compact_return_probe']}))


if __name__=='__main__':
    main()
