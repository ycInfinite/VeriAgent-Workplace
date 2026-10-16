"""Lossless compact display of the fixed current-S1/teacher cohort; no model calls."""
import argparse
import gzip
import json
import sys
from common import ROOT
from show_noop_review import compact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='+', type=int)
    parser.add_argument('--side', choices=['both', 'teacher', 'S1'], default='both')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    with gzip.open(ROOT/'experiments/S1-FAILURE-PREP-20261012-002/teacher_records.jsonl.gz', 'rt', encoding='utf-8') as f:
        teacher = {r['task_id']: r for r in map(json.loads, f)}
    source = ROOT/'experiments/S1-FAILURE-ACQUIRE-20261012-001/trajectories.jsonl'
    student = {r['task_id']: r for r in map(json.loads, source.read_text(encoding='utf-8').splitlines())} if source.exists() else {}
    for tid in args.ids:
        for side, rows in [('teacher', teacher), ('S1', student)]:
            if args.side not in ['both', side]:
                continue
            r = rows[tid]
            print('TASK', tid, side, 'REWARD', r['verifier']['official_reward'], 'END', r['termination'], 'USER', r['initial_messages'][-1]['content'])
            for m in r['messages'][len(r['initial_messages']):]:
                if m['role'] == 'assistant':
                    print('A', json.dumps(m.get('content', ''), ensure_ascii=False), 'CALLS', json.dumps([c['function'] for c in m.get('tool_calls', [])], ensure_ascii=False))
                else:
                    try:
                        value = json.loads(m['content'])
                    except (ValueError, TypeError):
                        value = m['content']
                    print('O', json.dumps(compact(value), ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
