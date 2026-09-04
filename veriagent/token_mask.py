"""CPU-only Qwen template/token mask inspection, not an implementation of a trainer."""
import json
from pathlib import Path
import re
from jinja2.sandbox import ImmutableSandboxedEnvironment
from tokenizers import Tokenizer

ROOT=Path(__file__).resolve().parents[1]
BOUNDARIES=('<|im_start|>','<|im_end|>')

class TokenMaskInspector:
    def __init__(self):
        meta=json.loads((ROOT/'configs/tokenizer.json').read_text())
        self.path=ROOT/meta['tokenizer_path']
        self.meta=meta
        config=json.loads((self.path/'tokenizer_config.json').read_text())
        env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
        # Match HF's non-HTML-escaped JSON serialization for the official Jinja template.
        env.filters['tojson']=lambda x,**kwargs:json.dumps(x,ensure_ascii=False,**kwargs)
        self.template=env.from_string(config['chat_template'])
        self.tokenizer=Tokenizer.from_file(str(self.path/'tokenizer.json'))

    def render(self,messages,tools,generate=False):
        # Our boundary-based mask is deliberately fail-closed for delimiter injection.
        serialized=json.dumps({'messages':messages,'tools':tools},ensure_ascii=False)
        if any(x in serialized for x in BOUNDARIES):
            raise ValueError('Literal ChatML boundary in content: unsupported; manual review required')
        return self.template.render(messages=messages,tools=tools,add_generation_prompt=generate,enable_thinking=False)

    def inspect(self,messages,tools):
        text=self.render(messages,tools)
        spans=[]
        blocks=list(re.finditer(r'<\|im_start\|>(system|user|assistant)\n(.*?)<\|im_end\|>',text,re.S))
        if len(blocks)!=text.count('<|im_start|>'):
            raise ValueError('Unrecognized or unfinished template block')
        for m in blocks:
            if m.group(1)=='assistant':
                spans.append((m.start(2),m.end())) # assistant content + EOS, header is context
        enc=self.tokenizer.encode(text,add_special_tokens=False)
        labels=[];owners=[]
        for token,(a,b) in zip(enc.ids,enc.offsets):
            inside=any(a>=s and b<=e and b>a for s,e in spans)
            crossing=any(a<e and b>s and not(a>=s and b<=e) for s,e in spans)
            if crossing:
                raise ValueError('Tokenizer crosses a supervised/context boundary')
            labels.append(token if inside else -100)
            owner=next((m.group(1) for m in blocks if a>=m.start() and b<=m.end()),'separator')
            owners.append(owner)
        return {'text':text,'input_ids':enc.ids,'labels':labels,'offsets':enc.offsets,
                'owners':owners,'supervised_tokens':sum(x!=-100 for x in labels),
                'processed_tokens':len(labels),'assistant_character_spans':spans}

def masked_sequence_logp(token_logps,labels):
    """token_logps[t] is log p(x_t | x_<t); actual trainers must first shift logits."""
    if len(token_logps)!=len(labels):
        raise ValueError('Length mismatch')
    return sum(lp for lp,label in zip(token_logps,labels) if label!=-100)

