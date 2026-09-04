"""Read-only guided view of recorded CPU evidence. No new experiment, network or model."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/Q0-TOKENS-20260904-001'

def main():
    p=argparse.ArgumentParser();p.add_argument('--view',choices=['trace','mask','rewards'],default='trace')
    view=p.parse_args().view
    print('READ-ONLY LEARNING VIEW | SCRIPTED CPU EVIDENCE | NOT AN LLM RESULT\n')
    if view=='trace':
        data=json.loads((BASE/'grounded_fixture_DEV_ONLY.json').read_text())
        print('Task:',data['messages'][1]['content'])
        for event in data['events']:
            print('\nStep',event['step'],event['tool_call']['name'])
            print('Arguments:',event['tool_call']['arguments'])
            print('Actual observation:',json.dumps(event['observation'],ensure_ascii=False))
            print('Changed state tables:',list(event['state_changes']))
        print('\nOfficial reward:',data['verifier']['official_reward'])
        print('Data eligible for training:',data['eligible_for_posttraining'])
    elif view=='mask':
        data=json.loads((BASE/'encoded_fixture_DEV_ONLY.json').read_text())
        target=[i for i,l in enumerate(data['labels']) if l!=-100]
        indices=sorted(set(range(max(0,target[0]-4),min(len(data['labels']),target[0]+28))))
        print('position | token_id | label | rendered text')
        for i in indices:
            a,b=data['offsets'][i]
            print(f"{i:5} | {data['input_ids'][i]:8} | {data['labels'][i]:8} | {data['text'][a:b]!r}")
        print('\nProcessed:',data['processed_tokens'],'Supervised:',data['supervised_tokens'])
        print('Tool observations are context; they are not policy-token targets.')
    else:
        data=json.loads((ROOT/'experiments/Q0-ENV-20260904-001/result.json').read_text())
        for k,v in data['variant_counts'].items():
            print(k,':',v)
        print('\nThese are scripted verifier tests, not Qwen success rates.')

if __name__=='__main__':
    main()
