"""CPU-only uploaded bundle/tokenizer/tool checks. No model construction or GPU call."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

from collect_training_probe import validate_inputs
from veriagent.environment import WorkplaceEnv,snapshot
from veriagent.sft_data import TurnEncoder

ROOT=Path(__file__).resolve().parents[1]

def main():
    cfg=json.loads((ROOT/'configs/sft_acquisition_plan.json').read_text())
    manifest=json.loads((ROOT/cfg['cohort_manifest']).read_text())
    rows=[json.loads(x) for x in (ROOT/cfg['data_path']).read_text().splitlines() if x.strip()]
    validate_inputs(cfg,manifest,rows)
    encoder=TurnEncoder(cfg['max_context_tokens'])
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(ROOT/cfg['weights_path'],local_files_only=True)
    counts=[]
    for row,meta in zip(rows,manifest['tasks']):
        if row['task_uid']!=meta['task_uid']:raise ValueError('Cohort order mismatch')
        messages=json.loads(json.dumps(row['responses_create_params']['input']))
        messages[0]['content']+='\n\n'+manifest['B1_addition']
        schemas=row['responses_create_params']['tools']
        rendered=tokenizer.apply_chat_template(messages,tools=schemas,tokenize=False,
            add_generation_prompt=True,enable_thinking=False)
        if hashlib.sha256(rendered.encode()).hexdigest()!=meta['initial_prompt_sha256']:
            raise ValueError('Actual Transformers tokenizer prompt mismatch')
        ids=tokenizer(rendered,add_special_tokens=False)['input_ids']
        other=encoder.inspector.tokenizer.encode(rendered,add_special_tokens=False).ids
        if ids!=other or len(ids)!=meta['initial_input_tokens']:
            raise ValueError('Actual Transformers token IDs mismatch')
        counts.append(len(ids))
    env=WorkplaceEnv();before=snapshot(env.tools)
    for action in rows[0]['ground_truth']:env.step(action)
    reward=env.verify(rows[0]['ground_truth'])['official_reward']
    changed=snapshot(env.tools)!=before
    env.reset();reset_ok=snapshot(env.tools)==before
    if reward!=1 or not changed or not reset_ok:raise ValueError('Scripted training-task tool smoke failed')
    result={'status':'NO_CARD_PREPARATION_CHECKS_PASSED','model_loaded':False,'parameter_updates':0,
        'actual_transformers_prompt_matches':len(counts),'actual_token_id_matches':len(counts),
        'initial_tokens_min':min(counts),'initial_tokens_max':max(counts),
        'scripted_tool_smoke':{'task_uid':rows[0]['task_uid'],'reward':reward,'state_changed':changed,
            'reset_equal':reset_ok,'producer':'SCRIPTED_CPU_NOT_POLICY_TRAINING_DATA'},
        'packages':{x:importlib.metadata.version(x) for x in
                    ['torch','transformers','tokenizers','pandas','numpy','huggingface-hub','jinja2']},
        'limitations':['No GPU compatibility or real model load tested','No model trajectory collected',
                       'No SFT trainer/CE/update/reload tested']}
    target=ROOT/'logs/no_card_validation.json'
    if target.exists():raise FileExistsError('No-card validation result already exists')
    target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
