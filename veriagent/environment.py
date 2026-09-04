"""Execute the pinned official Workplace tools and verifier without the NeMo launcher.

This is a project-owned direct-call adapter, NOT a test of the upstream HTTP/Ray stack.
Each instance owns fresh official tool objects. No observations are fabricated.
"""
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/Gym'))
from resources_servers.workplace_assistant.utils import get_tools, is_correct

TOOLKITS = ['email','calendar','analytics','project_management','customer_relationship_manager']

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def snapshot(tool_env):
    """Capture every DataFrame, including read-only inputs; preserve index/order."""
    result = {}
    for name, obj in tool_env['containers'].items():
        for attr, value in vars(obj).items():
            if hasattr(value, 'to_json') and hasattr(value, 'columns'):
                result[f'{name}.{attr}'] = json.loads(value.to_json(orient='split',date_format='iso'))
    return result

def state_diff(before, after):
    changes = {}
    for table in before.keys() | after.keys():
        old, new = before.get(table,{}), after.get(table,{})
        if old == new:
            continue
        old_rows = Counter(canonical(x) for x in old.get('data',[]))
        new_rows = Counter(canonical(x) for x in new.get('data',[]))
        changes[table] = {
            'before_sha256':digest(old),'after_sha256':digest(new),
            'columns_before':old.get('columns'),'columns_after':new.get('columns'),
            'index_before':old.get('index'),'index_after':new.get('index'),
            'removed_rows':[json.loads(x) for x in (old_rows-new_rows).elements()],
            'added_rows':[json.loads(x) for x in (new_rows-old_rows).elements()],
        }
    return changes

class WorkplaceEnv:
    def __init__(self):
        self.reset()

    def reset(self):
        self.tools = get_tools(TOOLKITS)
        self.events = []
        self.initial_state = snapshot(self.tools)
        return deepcopy(self.initial_state)

    def step(self, action):
        """Mirror official online None filtering; capture actual returned value/error."""
        before = snapshot(self.tools)
        started = time.perf_counter()
        error = None
        try:
            args = action['arguments']
            args = json.loads(args) if isinstance(args,str) else args
            if not isinstance(args,dict):
                raise TypeError('Tool arguments must be a JSON object')
            args = {k:v for k,v in args.items() if v is not None}
            result = self.tools['functions'][action['name']](**args)
        except Exception as exc:
            error = {'type':type(exc).__name__,'message':str(exc)}
            result = f"Error executing tool '{action.get('name')}': {exc}"
        after = snapshot(self.tools)
        event = {'step':len(self.events)+1,'tool_call':deepcopy(action),'observation':result,
                 'exception':error,'state_changes':state_diff(before,after),
                 'state_before_sha256':digest(before),'state_after_sha256':digest(after),
                 'latency_seconds':time.perf_counter()-started}
        self.events.append(event)
        return deepcopy(event)

    def verify(self, reference):
        predicted = [e['tool_call'] for e in self.events]
        captured = io.StringIO()
        start = time.perf_counter()
        with redirect_stdout(captured):
            reward = float(is_correct(predicted, reference, None))
        return {'official_reward':reward,'replay_stdout':captured.getvalue(),
                'latency_seconds':time.perf_counter()-start}

