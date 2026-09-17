"""Official DeepSeek transport; distinct from Bailian and subscription endpoints."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
import urllib.request

from veriagent.teacher_rollout import APIError, BailianTransport, NoRedirect, read_usage, wire_messages


def endpoint(base_url):
    if base_url not in ('https://api.deepseek.com','https://api.deepseek.com/v1'):
        raise ValueError('Only the official DeepSeek HTTPS endpoint is authorized')
    return base_url + '/chat/completions'


def request_body(messages, schemas, config, cap):
    if config['model']!='deepseek-flash' or config['enable_thinking'] is not False:
        raise ValueError('Unexpected model or reasoning mode')
    tools=[]
    for schema in schemas:
        if schema.get('type')!='function':
            raise ValueError('Unsupported tool schema')
        tools.append({'type':'function','function':{k:deepcopy(v) for k,v in schema.items() if k!='type'}})
    return {'model':'deepseek-flash','messages':wire_messages(messages),'tools':tools,
            'stream':False,'thinking':{'type':'disabled'},'temperature':config['temperature'],
            'max_tokens':cap}


def usage(response):
    inputs,outputs=read_usage(response)
    data=response['usage']
    hit,miss=data.get('prompt_cache_hit_tokens'),data.get('prompt_cache_miss_tokens')
    if any(type(x) is not int or x<0 for x in (hit,miss)) or hit+miss!=inputs:
        raise APIError('invalid_cache_usage')
    details=data.get('completion_tokens_details') or {}
    if not isinstance(details,dict):raise APIError('invalid_completion_usage_details')
    reasoning=details.get('reasoning_tokens')
    if reasoning is not None and (type(reasoning) is not int or reasoning<0):
        raise APIError('invalid_reasoning_usage')
    return {'input_tokens':inputs,'output_tokens':outputs,'cache_hit_tokens':hit,
            'cache_miss_tokens':miss,'reasoning_tokens':reasoning}


def validate_response(response):
    if not isinstance(response.get('model'),str) or not response['model']:
        raise APIError('missing_returned_model_identity')
    values=usage(response)
    if values['reasoning_tokens'] not in (None,0):
        raise APIError('unexpected_reasoning_usage')


def estimated_cost(response, observed_at):
    values=usage(response)
    local=datetime.fromisoformat(observed_at).astimezone(timezone(timedelta(hours=8)))
    peak=local.weekday()<5 and (9<=local.hour<12 or 14<=local.hour<18)
    factor=2 if peak else 1
    return {**values,'price_period':'peak' if peak else 'off_peak',
            'estimated_rmb':factor*(values['cache_miss_tokens']+.02*values['cache_hit_tokens']+
                                   4*values['output_tokens'])/1_000_000}


class DeepSeekTransport(BailianTransport):
    def __init__(self, config):
        self.url=endpoint(config['base_url'])
        self.key_env=config['api_key_environment']
        key=os.environ.get(self.key_env,'')
        if not key.startswith('sk-') or key.startswith(('sk-sp-','sk-ws-')) or any(c.isspace() for c in key):
            raise ValueError('Missing ordinary DeepSeek credential; value suppressed')
        self.opener=urllib.request.build_opener(NoRedirect())

    def __call__(self, body, timeout):
        if body.get('thinking')!={'type':'disabled'} or body.get('model')!='deepseek-flash':
            raise APIError('request_contract_violation')
        if 'enable_thinking' in body or 'seed' in body:
            raise APIError('unsupported_provider_parameters')
        return super().__call__(body,timeout)
