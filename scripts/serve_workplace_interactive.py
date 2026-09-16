"""Single-task Workplace tools for a user's interactive coding-client session.

This server NEVER calls a model/provider, starts a client, or schedules tasks.
Tool logs alone are NOT a complete model transcript or approved SFT data.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SDK = ROOT / '.cache/interactive-python'
if SDK.is_dir():
    sys.path.insert(0, str(SDK))

from veriagent.environment import WorkplaceEnv, digest, snapshot
from veriagent.teacher_data import teacher_request


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def safe_json(value):
    text = json.dumps(value, ensure_ascii=False, default=str)
    if re.search(r'sk-(?:sp-|ws-)?[A-Za-z0-9_.\-/]{16,}', text):
        raise ValueError('Credential-like content rejected; nothing recorded')
    return text


class InteractiveWorkplace:
    def __init__(self, task_id=707, session_id=None, actor='UNVERIFIED_INTERACTIVE_CLIENT'):
        cohort = read_json(ROOT / 'experiments/SFT-PREP-20260910-001/acquisition_manifest.json')
        tasks = [t for t in cohort['tasks'] if t['source_id'] == task_id]
        if len(tasks) != 1 or tasks[0]['pool'] != 'training_candidate':
            raise ValueError('Only the fixed training cohort may be used')
        self.task = tasks[0]
        rows = [json.loads(line) for line in (ROOT / 'data/sft_probe_train20.jsonl')
                .read_text(encoding='utf-8').splitlines() if line.strip()]
        matches = [r for r in rows if r['id'] == task_id]
        if len(matches) != 1:
            raise ValueError('Training row identity mismatch')
        row = matches[0]
        self.request = teacher_request(row, self.task, cohort['B1_addition'])
        self.reference = deepcopy(row['ground_truth'])
        self.sources = read_json(ROOT / 'configs/sources.json')
        self.session_id = session_id or ('INTERACTIVE-' + datetime.now(timezone.utc)
            .strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', self.session_id):
            raise ValueError('Invalid session identity')
        self.path = ROOT / '.cache/interactive-sessions' / self.session_id
        self.actor = actor
        self.env = None
        self.closed = False
        self.started = None
        self.max_calls = 6
        self.max_wall_seconds = 1800

    def write(self, name, value):
        text = safe_json(value)
        with (self.path / name).open('x', encoding='utf-8') as file:
            file.write(text + '\n')

    def append(self, name, value):
        text = safe_json(value)
        with (self.path / name).open('a', encoding='utf-8') as file:
            file.write(text + '\n')

    def get_task(self):
        """Return the fixed training task and original schemas, never the reference."""
        if self.closed:
            raise ValueError('Session closed; cannot restart or select another task')
        if self.env is None:
            self.path.mkdir(parents=True, exist_ok=False)
            self.env = WorkplaceEnv()
            self.started = time.monotonic()
            self.write('identity.json', {
                'session_id': self.session_id, 'kind': 'INTERACTIVE_TOOL_LOG_NOT_MODEL_EVAL',
                'actor_declared': self.actor, 'actor_identity_verified': False,
                'task_uid': self.task['task_uid'], 'source_pool': 'training_candidate',
                'sources': self.sources, 'started_at': datetime.now(timezone.utc).isoformat(),
                'server_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'reference_sha256': digest(self.reference),
                'initial_state_sha256': digest(self.env.initial_state),
                'max_workplace_calls': self.max_calls, 'max_wall_seconds': self.max_wall_seconds,
                'provider_called_by_server': False, 'model_revision': None, 'seed': None,
                'training_eligible': False, 'full_client_transcript_required': True,
                'same_condition_as_B1': False,
            })
            self.write('initial_state.json', self.env.initial_state)
            self.write('task_request.json', self.request)
        return {'session_id': self.session_id, **deepcopy(self.request),
                'instruction': 'Use execute_workplace_tool for real actions. Ground IDs in '
                'task/observations. Call finish_task once when done. This session cannot reset.',
                'remaining_workplace_calls': self.max_calls - len(self.env.events)}

    def require_active(self):
        if self.env is None or self.closed:
            raise ValueError('Call get_task first; completed sessions cannot act again')
        if time.monotonic() - self.started > self.max_wall_seconds:
            self.closed = True
            self.write('termination.json', {'reason': 'wall_time_bound', 'training_eligible': False})
            raise ValueError('Session time bound reached')

    def execute(self, name, arguments):
        self.require_active()
        if len(self.env.events) >= self.max_calls:
            raise ValueError('Tool-call bound reached; finish the task without another action')
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise ValueError('Expected a tool name and JSON-object arguments')
        raw_action = {'name': name, 'arguments': deepcopy(arguments)}
        safe_json(raw_action)
        # Upstream replay consumes OpenAI-style JSON argument strings. The MCP
        # transport supplies an object; serialize here, without changing values.
        action = {'name': name, 'arguments': json.dumps(arguments, ensure_ascii=False)}
        # Persist intent before execution so an interrupted tool call is not erased.
        self.append('action_intents.jsonl', {'step': len(self.env.events) + 1,
                    'mcp_action': raw_action, 'tool_call': action})
        event = self.env.step(action)
        self.append('tool_events.jsonl', event)
        # Keep diagnostic state differences private; only genuine returned observations go back.
        return {'step': event['step'], 'observation': event['observation'],
                'exception': event['exception'],
                'remaining_workplace_calls': self.max_calls - len(self.env.events)}

    def finish(self, answer):
        self.require_active()
        if not isinstance(answer, str) or len(answer) > 12000:
            raise ValueError('Expected a final answer under 12000 characters')
        safe_json(answer)
        self.closed = True  # Verification can never be used to retry the same session.
        self.write('termination.json', {'reason': 'client_finish', 'answer': answer})
        try:
            verified = self.env.verify(self.reference)
        except Exception as exc:
            self.write('result.json', {'infra_invalid': True, 'error_type': type(exc).__name__,
                       'training_eligible': False, 'model_rollout_claimed': False})
            raise RuntimeError('Verifier infrastructure failure; evidence preserved') from None
        result = {'session_id': self.session_id, 'tool_calls': len(self.env.events),
                  'verifier': verified, 'final_state_sha256': digest(snapshot(self.env.tools)),
                  'wall_seconds': time.monotonic() - self.started,
                  'provider_tokens': None, 'model_latency_seconds': None,
                  'full_model_transcript_available': False, 'training_eligible': False,
                  'infra_invalid': False, 'model_rollout_claimed': False}
        self.write('result.json', result)
        return {'closed': True, 'official_reward': verified['official_reward'],
                'tool_calls': len(self.env.events), 'training_eligible': False,
                'note': 'Preserve the full client transcript; tool logs do not establish SFT eligibility.'}

    def disconnect(self):
        if self.env is not None and not self.closed:
            self.closed = True
            self.write('termination.json', {'reason': 'client_disconnected',
                       'training_eligible': False, 'model_rollout_claimed': False})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-id', type=int, default=707)
    parser.add_argument('--session-id')
    args = parser.parse_args()
    # A local tool server has no use for the client's provider credentials.
    for name in ('BAILIAN_TOKEN_PLAN_API_KEY', 'OPENAI_API_KEY', 'VERIAGENT_BAILIAN_API_KEY'):
        os.environ.pop(name, None)
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    session = InteractiveWorkplace(args.task_id, args.session_id)
    server = FastMCP('VeriAgent single interactive task', log_level='ERROR')
    annotations = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                  idempotentHint=False, openWorldHint=False)

    @server.tool(annotations=annotations)
    def get_task() -> dict:
        """Begin one fixed training task; get its user request and original tool schemas."""
        return session.get_task()

    @server.tool(annotations=annotations)
    def execute_workplace_tool(name: str, arguments: dict) -> dict:
        """Execute one named Workplace tool with its original arguments; return real observation."""
        return session.execute(name, arguments)

    @server.tool(annotations=annotations)
    def finish_task(answer: str) -> dict:
        """Submit the final answer, close the session permanently and run the official verifier."""
        return session.finish(answer)

    try:
        server.run(transport='stdio')
    finally:
        session.disconnect()


if __name__ == '__main__':
    main()
