"""Teacher request isolation and canonical student formatting, without API calls.

Different teachers have different tokenizers. Re-encode complete visible assistant
turns with the fixed student tokenizer; never claim these are teacher sampled IDs.
This module does not approve data or relax the existing SFT admission gate.
"""
from copy import deepcopy
import hashlib

from veriagent.sft_data import content_sha256, TurnEncoder


def teacher_request(row, task, general_instruction):
    if task['pool'] != 'training_candidate' or task['source_split'] != 'train':
        raise ValueError('Teacher request must come from training pool')
    if row['id'] != task['source_id']:
        raise ValueError('Teacher task identity mismatch')
    messages=deepcopy(row['responses_create_params']['input'])
    messages[0]['content']+='\n\n'+general_instruction
    tools=deepcopy(row['responses_create_params']['tools'])
    request={'messages':messages,'tools':tools}
    validate_request(request,task)
    return request


def validate_request(request,task):
    if set(request)!={'messages','tools'}:
        raise ValueError('Unexpected request field, including verifier/oracle data')
    if task['pool']!='training_candidate':
        raise ValueError('Non-training task')
    if content_sha256(request['messages'])!=task['initial_messages_sha256']:
        raise ValueError('Initial task/prompt differs from fixed B1 cohort')
    if content_sha256(request['tools'])!=task['tool_schemas_sha256']:
        raise ValueError('Tools differ from fixed cohort')
    return True


class CanonicalTeacherEncoder:
    def __init__(self,max_context_tokens=8192):
        self.checked=TurnEncoder(max_context_tokens)
        self.inspector=self.checked.inspector
        self.max_context_tokens=max_context_tokens

    def encode(self,prefix_messages,tools,assistant_message):
        if assistant_message.get('role')!='assistant':
            raise ValueError('Only a visible assistant turn can be a target')
        if set(assistant_message)-{'role','content','tool_calls'}:
            raise ValueError('Unspecified assistant fields require an explicit normalization policy')
        prefix=self.inspector.render(prefix_messages,tools,generate=True)
        complete=self.inspector.render(prefix_messages+[assistant_message],tools,generate=False)
        if not complete.startswith(prefix):
            raise ValueError('Canonical assistant prefix is not a continuation of the input')
        suffix=complete[len(prefix):]
        if not suffix.endswith('<|im_end|>\n'):
            raise ValueError('Unexpected canonical assistant termination')
        # The renderer adds a separator newline after EOS; it is not a policy target.
        target_text=suffix[:-1]
        prefix_ids=self.inspector.tokenizer.encode(prefix,add_special_tokens=False).ids
        target_ids=self.inspector.tokenizer.encode(target_text,add_special_tokens=False).ids
        if not target_ids or target_ids[-1] not in self.checked.eos_ids:
            raise ValueError('Canonical target lacks EOS')
        if len(prefix_ids)+len(target_ids)>self.max_context_tokens:
            raise ValueError('Canonical sequence exceeds bound; no truncation')
        if self.inspector.tokenizer.decode(prefix_ids+target_ids,skip_special_tokens=False)!=prefix+target_text:
            raise ValueError('Canonical encoding roundtrip mismatch')
        return {'input_ids':prefix_ids+target_ids,'labels':[-100]*len(prefix_ids)+target_ids,
            'attention_mask':[1]*(len(prefix_ids)+len(target_ids)),
            'prefix_tokens':len(prefix_ids),'supervised_tokens':len(target_ids),
            'processed_tokens':len(prefix_ids)+len(target_ids),
            'prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),
            'canonical_target_sha256':hashlib.sha256(target_text.encode()).hexdigest(),
            'student_model_revision':self.checked.model_revision,
            'format':'canonical_qwen_non_thinking_complete_visible_assistant_turn_v1',
            'teacher_token_ids_used':False,'training_eligible':False}
