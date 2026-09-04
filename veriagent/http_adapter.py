"""Optional project-owned CPU HTTP adapter over unchanged official tool functions.

Not the native NeMo server. Use only locally; this pilot has no auth/deployment layer.
"""
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from veriagent.environment import WorkplaceEnv

class SeedRequest(BaseModel):
    reference: list[dict[str,str]]

class StepRequest(BaseModel):
    name: str
    arguments: str
    model_config=ConfigDict(extra='forbid')

def make_app():
    app=FastAPI()
    sessions={}

    def session(session_id):
        if session_id not in sessions:
            raise HTTPException(404,'Unknown session')
        return sessions[session_id]

    @app.post('/seed')
    def seed(body:SeedRequest):
        key=uuid4().hex
        sessions[key]=(WorkplaceEnv(),body.reference)
        return {'session_id':key}

    @app.post('/sessions/{session_id}/step')
    def step(session_id:str,body:StepRequest):
        env,_=session(session_id)
        event=env.step(body.model_dump())
        # Only observation goes to the policy; state/ground truth stay in audit records.
        return {'output':event['observation']}

    @app.post('/sessions/{session_id}/verify')
    def verify(session_id:str):
        env,ref=session(session_id)
        try:
            return env.verify(ref)
        finally:
            sessions.pop(session_id,None)
    return app
