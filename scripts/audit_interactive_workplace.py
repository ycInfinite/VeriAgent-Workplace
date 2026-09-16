"""CPU-only MCP integration audit using an existing training707 replay fixture."""
import asyncio
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/interactive-python'))
sys.path.insert(0, str(ROOT))
from common import Run, card
from serve_workplace_interactive import InteractiveWorkplace
from veriagent.environment import digest, snapshot
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main(run_id):
    RUN_ID = run_id
    run = Run(RUN_ID, card(
        'Can the interactive tool bridge execute real Workplace tools and preserve evidence?',
        'One fixed training task can be exposed without reference disclosure or provider calls.',
        'MCP tool transport instead of direct Python invocation',
        ['protocol tool listing', 'real observation equality', 'state change', 'official reward',
         'no reset after finish', 'training-only gate', 'tool-call bound'],
        'All CPU controls pass; never interpret a scripted fixture as a model rollout.',
        experiment_kind='CPU_MCP_INTEGRATION_NOT_MODEL_EVAL', seed=None))
    checks = []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        run.append('checks.jsonl', checks[-1])
        if not condition:
            raise AssertionError(name)

    try:
        try:
            InteractiveWorkplace(-1)
        except ValueError:
            check('outside_training_cohort_rejected', True)
        else:
            check('outside_training_cohort_rejected', False)
        negative = InteractiveWorkplace(707, RUN_ID + '-bounds', actor='SCRIPTED_CPU_FIXTURE')
        try:
            negative.execute('missing_tool', {})
        except ValueError:
            check('action_before_get_task_rejected', True)
        request = negative.get_task()
        check('reference_not_in_public_task', not ({'reference','ground_truth'} & set(request)))
        first_state = digest(snapshot(negative.env.tools))
        for _ in range(6):
            negative.execute('customer_relationship_manager_search_customers', {'customer_name': 'Kerry Moore'})
        try:
            negative.execute('customer_relationship_manager_search_customers', {'customer_name': 'Kerry Moore'})
        except ValueError:
            check('seventh_call_rejected', len(negative.env.events) == 6)
        check('lookup_calls_preserve_state', digest(snapshot(negative.env.tools)) == first_state)
        negative.disconnect()
        check('disconnect_preserves_termination', (negative.path/'termination.json').is_file())

        fixture = next(json.loads(line) for line in
            (ROOT/'experiments/TEACHER-ACQUIRE-20260916-001/trajectories.jsonl')
            .read_text(encoding='utf-8').splitlines() if json.loads(line)['task_id'] == 707)
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT/'scripts/serve_workplace_interactive.py'), '--task-id', '707',
                  '--session-id', RUN_ID + '-stdio'], cwd=str(ROOT),
            env={'PYTHONIOENCODING': 'utf-8'})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = (await client.list_tools()).tools
                check('three_explicit_tools', {t.name for t in tools} ==
                      {'get_task','execute_workplace_tool','finish_task'})
                check('no_automatic_replay_annotations', all(t.annotations.idempotentHint is False for t in tools))
                opened = await client.call_tool('get_task', {})
                check('mcp_task_request_succeeded', not opened.isError)
                text = json.loads(opened.content[0].text)
                check('mcp_original_schemas_preserved', text['tools'] == fixture['tool_schemas'])
                for event in fixture['events']:
                    action = event['tool_call']
                    reply = await client.call_tool('execute_workplace_tool', action)
                    body = json.loads(reply.content[0].text)
                    check('real_observation_' + str(event['step']), not reply.isError and
                          digest(body['observation']) == digest(event['observation']))
                repeated = await client.call_tool('get_task', {})
                check('get_task_does_not_reset', json.loads(repeated.content[0].text)
                      ['remaining_workplace_calls'] == 6-len(fixture['events']))
                finish = await client.call_tool('finish_task', {'answer':
                    'SCRIPTED FIXTURE REPLAY ONLY: customer state updated through actual tools.'})
                final = json.loads(finish.content[0].text)
                check('official_verifier_success', not finish.isError and final['official_reward'] == 1)
                check('not_automatically_training_eligible', final['training_eligible'] is False)
                check('post_finish_action_rejected', (await client.call_tool('execute_workplace_tool',
                    {'name':'customer_relationship_manager_search_customers',
                     'arguments':{'customer_name':'Kerry Moore'}})).isError)
                check('post_finish_reset_rejected', (await client.call_tool('get_task', {})).isError)
        log_root = ROOT/'.cache/interactive-sessions'/(RUN_ID+'-stdio')
        raw = json.loads((log_root/'result.json').read_text(encoding='utf-8'))
        check('actual_final_state_matches_old_fixture', raw['final_state_sha256'] == fixture['final_state_sha256'])
        for name in ['identity.json','task_request.json','action_intents.jsonl','tool_events.jsonl',
                     'termination.json','result.json']:
            (run.path/name).write_bytes((log_root/name).read_bytes())
        run.finish({'status':'passed', 'checks':len(checks), 'model_rollouts':0,
                    'api_requests':0,'gpu_hours':0,'parameter_updates':0,
                    'training_approved':0,'mcp_version':importlib.metadata.version('mcp'),
                    'fixture':'existing teacher training707; scripted transport replay only'})
        print(json.dumps({'status':'passed','checks':len(checks),'model_rollouts':0,'run_id':RUN_ID}))
    except Exception as exc:
        run.finish({'status':'failed','error_type':type(exc).__name__, 'checks':checks,
                    'model_rollouts':0,'api_requests':0,'gpu_hours':0}, status='infrastructure_invalid')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    asyncio.run(main(parser.parse_args().run_id))
