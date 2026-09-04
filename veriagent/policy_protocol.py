"""Strict, non-executing parser for Qwen tool-call text and diagnostic helpers."""
import json
import re

CALL=re.compile(r'<tool_call>\s*(.*?)\s*</tool_call>',re.S)

def parse_tool_calls(text):
    calls=[];errors=[]
    for index,match in enumerate(CALL.finditer(text)):
        raw=match.group(1)
        try:
            obj=json.loads(raw)
            if not isinstance(obj,dict) or not isinstance(obj.get('name'),str) or 'arguments' not in obj:
                raise ValueError('Expected name and arguments object')
            args=obj['arguments']
            if isinstance(args,str):args=json.loads(args)
            if not isinstance(args,dict):raise ValueError('arguments must be a JSON object')
            calls.append({'name':obj['name'],'arguments':json.dumps(args,ensure_ascii=False),
                          'parsed_arguments':args,'raw':raw,'span':[match.start(),match.end()]})
        except (json.JSONDecodeError,ValueError,TypeError):
            errors.append({'call_index':index,'raw':raw,'error':'Invalid tool call JSON/structure'})
    if text.count('<tool_call>')!=len(calls)+len(errors) or text.count('</tool_call>')!=len(calls)+len(errors):
        errors.append({'raw':text,'error':'Unbalanced tool-call delimiters'})
    content=CALL.sub('',text).replace('<|im_end|>','').replace('<|endoftext|>','').strip()
    return calls,errors,content

def identifier_candidates(arguments,visible_text):
    findings=[]
    for key,value in arguments.items():
        if not isinstance(value,str) or not value:continue
        is_id=key.endswith('_id')
        is_email=('@' in value and (key.endswith('_email') or key in ('recipient','email')))
        if is_id or is_email:
            supported=bool(re.search(r'(?<![\w])'+re.escape(value)+r'(?![\w])',visible_text,re.I))
            findings.append({'argument':key,'value':value,'observed_in_policy_context':supported,
                             'kind':'identifier' if is_id else 'email'})
    return findings
