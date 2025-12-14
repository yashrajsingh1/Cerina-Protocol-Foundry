from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class AgentLogEntry(BaseModel):
    agent_name: str
    phase: str
    message: str
    created_at: datetime


class DraftVersionOut(BaseModel):
    model_config = {"from_attributes": True}
    
    id: int
    version_index: int
    content: str
    safety_score: Optional[float] = None
    empathy_score: Optional[float] = None
    created_at: datetime


class ProtocolSessionOut(BaseModel):
    model_config = {"from_attributes": True}
    
    id: int
    intent: str
    thread_id: str
    status: str

    latest_draft: Optional[str] = None
    human_edited_draft: Optional[str] = None
    final_protocol: Optional[str] = None

    safety_score: Optional[float] = None
    empathy_score: Optional[float] = None

    iteration: int
    created_at: datetime
    updated_at: datetime

    drafts: List[DraftVersionOut]


class ProtocolSessionListItem(BaseModel):
    model_config = {"from_attributes": True}
    
    id: int
    intent: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreateProtocolRequest(BaseModel):
    intent: str


class ApproveDraftRequest(BaseModel):
    edited_draft: str


class BlackboardSnapshot(BaseModel):
    state: dict
    created_at: Optional[str] = None


class ProtocolRunResponse(BaseModel):
    session: ProtocolSessionOut
    blackboard: Optional[BlackboardSnapshot] = None
