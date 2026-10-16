"""Display only registered current-S1 comparison dev traces for semantic review."""
import argparse
import json
import sys
from common import ROOT
from show_noop_review import compact
from veriagent.sft_data import content_sha256


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--condition', choices=['S1', 'CHOSEN_SFT', 'DPO'], required=True)
    p.add_argument('--seed', type=int, choices=[42, 43])
    p.add_argument('--dedup', action='store_true')
    p.add_argument('ids', nargs='+', type=int)
    args = p.parse_args(); sys.stdout.reconfigure(encoding='utf-8')
    cfg = json.loads((ROOT/'configs/current_s1_preference_plan.json').read_text(encoding='utf-8'))
    source = ROOT/'experiments'/cfg['eval_run_ids'][args.condition]/'trajectories.jsonl'
    store = ROOT/'reports/current-preference-20261016/rendered_observations.json'
    seen = json.loads(store.read_text(encoding='utf-8')) if args.dedup and store.exists() else {}
    for r in map(json.loads, source.read_text(encoding='utf-8').splitlines()):
        if r['task_id'] not in args.ids or args.seed is not None and r['seed'] != args.seed:
            continue
        assert r['source_pool'] == 'development' and r['task_uid'] in cfg['evaluation']['task_uids']
        print('CASE', args.condition, r['task_id'], r['seed'], 'REWARD', r['verifier']['official_reward'], 'END', r['termination'], 'USER', r['initial_messages'][-1]['content'])
        for m in r['messages'][len(r['initial_messages']):]:
            if m['role'] == 'assistant':
                print('A', json.dumps(m.get('content', ''), ensure_ascii=False), 'CALLS', json.dumps([c['function'] for c in m.get('tool_calls', [])], ensure_ascii=False))
            else:
                try: value = json.loads(m['content'])
                except (ValueError, TypeError): value = m['content']
                h = content_sha256(value)
                if args.dedup and h in seen:
                    print('O_ALREADY_DISPLAYED_THIS_AUDIT', h)
                else:
                    print('O', h, json.dumps(compact(value), ensure_ascii=False, separators=(',', ':')))
                    seen[h] = value
    if args.dedup:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
