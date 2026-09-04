"""Bounded CPU checks of wire contracts, real no-op evidence and near-duplicate warnings."""
import argparse
from collections import Counter
import importlib.metadata
import json
from common import ROOT, Run, card, load_rows, write_json
from audit_dataset import normalized, question
from veriagent.environment import WorkplaceEnv
from veriagent.http_adapter import make_app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from resources_servers.workplace_assistant.task_data import TaskData

def run(run_id):
    exp=Run(run_id,card('Are the minimal HTTP boundary and task-data contract correct, and are no-op rewards explainable?',
        'Project adapter preserves real observations; new upstream prepare shape needs adaptation; empty reference is not proof of a bad task',
        'Session, request shape, actual lookup versus blind no-op',
        ['HTTP/schema checks','lookup evidence','near-duplicate candidates','runtime identity'],
        'Do not label the native NeMo stack or final split qualified; expose remaining limitations',seed=20260904))
    try:
        train=load_rows('train');validation=load_rows('validation')
        client=TestClient(make_app());checks={}
        seeded=client.post('/seed',json={'reference':train[0]['ground_truth']})
        session_id=seeded.json()['session_id']
        checks['seed_does_not_expose_ground_truth']=set(seeded.json())=={'session_id'}
        search=client.post(f'/sessions/{session_id}/step',json={'name':'email_search_emails','arguments':json.dumps({
            'query':'carlos Task Update on Develop prototype for report generation'})})
        observation=search.json()['output']
        email_id=observation['emails'][0]['email_id']
        replied=client.post(f'/sessions/{session_id}/step',json={'name':'email_reply_email','arguments':json.dumps({
            'email_id':email_id,'body':'Thanks for the update - I will get back to you tomorrow.'})})
        checks['step_exposes_only_tool_output']=set(search.json())=={'output'} and set(replied.json())=={'output'}
        verified=client.post(f'/sessions/{session_id}/verify')
        checks['http_grounded_task_reward_one']=verified.json()['official_reward']==1
        checks['verified_session_is_cleaned']=client.post(f'/sessions/{session_id}/verify').status_code==404
        s2=client.post('/seed',json={'reference':[]}).json()['session_id']
        checks['bad_wire_shape_rejected']=client.post(f'/sessions/{s2}/step',json={'arguments':'{}'}).status_code==422
        unknown=client.post(f'/sessions/{s2}/step',json={'name':'not_a_real_tool','arguments':'{}'})
        checks['tool_error_visible_at_http_200']=unknown.status_code==200 and 'Error executing tool' in unknown.json()['output']
        client.post(f'/sessions/{s2}/verify')
        TaskData.model_validate(train[0])
        checks['nvidia_task_top_level_contract_valid']=True
        nested={'id':train[0]['id'],'responses_create_params':train[0]['responses_create_params'],
                'verifier_metadata':{k:train[0][k] for k in ('ground_truth','category','environment_name')}}
        try:
            TaskData.model_validate(nested)
            checks['new_prepare_shape_rejected_by_current_task_contract']=False
        except ValidationError as exc:
            checks['new_prepare_shape_rejected_by_current_task_contract']=True
            write_json(exp.path/'prepare_shape_validation_errors.json',exc.errors(include_input=False))
        # DEV 709 explicitly asks to cancel future meetings. Search real state first.
        env=WorkplaceEnv()
        event=env.step({'name':'calendar_search_events','arguments':json.dumps({
            'query':'supply chain enhancement workshop','time_min':'2023-12-01'})})
        noop={'task_id':709,'producer':'SCRIPTED_DEV_DIAGNOSTIC','query':question(train[709]),
              'lookup_event':event,'lookup_then_stop_verifier':env.verify(train[709]['ground_truth']),
              'blind_stop_verifier':WorkplaceEnv().verify(train[709]['ground_truth'])}
        write_json(exp.path/'noop_lookup_DEV_ONLY.json',noop)
        # create_plot models a file record; verify whether a PNG is actually created.
        plot_env=WorkplaceEnv()
        plot=plot_env.step({'name':'analytics_create_plot','arguments':json.dumps({
            'time_min':'2023-11-01','time_max':'2023-11-30','value_to_plot':'total_visits','plot_type':'bar'})})
        artifact={'event':plot,'returned_path_exists':(ROOT/plot['observation']).exists(),
                  'interpretation':'Official simulation records a plot path; it does not render a PNG'}
        write_json(exp.path/'plot_effect_diagnostic.json',artifact)
        # Mechanical lexical screen, no final questions/answers emitted or used for tuning.
        vs=[(i,r['category'],set(normalized(question(r)).split())) for i,r in enumerate(validation)]
        candidates=[]
        for i,r in enumerate(train):
            a=set(normalized(question(r)).split())
            for j,category,b in vs:
                if category!=r['category'] or not a or not b:
                    continue
                score=len(a&b)/len(a|b)
                if score>=.9:
                    candidates.append({'train_index':i,'official_validation_index':j,'jaccard':score,
                                       'status':'LEXICAL_CANDIDATE_NOT_PROOF_OF_LEAKAGE'})
        write_json(exp.path/'near_duplicate_metadata_only.json',candidates)
        runtime={name:importlib.metadata.version(name) for name in
                 ('pandas','numpy','pydantic','fastapi','starlette','httpx','jinja2','tokenizers')}
        write_json(exp.path/'runtime_versions.json',runtime)
        result={'checks':checks,'http_transport':'in-process ASGI TestClient, not a deployed native NeMo server',
                'near_duplicate_pairs_jaccard_ge_0_9':len(candidates),
                'near_duplicate_train_rows':len({x['train_index'] for x in candidates}),
                'near_duplicates_semantically_adjudicated':False,
                'native_nemo_service':'NOT_RUN: CPU path deliberately imports official tools/verifier only',
                'noop_blind_and_lookup_reward_equal':noop['lookup_then_stop_verifier']['official_reward']==noop['blind_stop_verifier']['official_reward'],
                'plot_file_actually_created':artifact['returned_path_exists'],
                'runtime':runtime}
        exp.finish(result);print(json.dumps(result,indent=2))
    except Exception as exc:
        exp.finish({'error_type':type(exc).__name__,'error':str(exc)},'infrastructure_invalid');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
