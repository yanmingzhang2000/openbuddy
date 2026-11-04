"""Pydantic 请求/响应模型。"""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    instruction: str = Field(min_length=1)
    repo_url: str | None = None
    max_steps: int | None = None
    timeout_seconds: int | None = None
    token_budget: int | None = None
    cost_budget_usd: float | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    instruction: str
    status: str
    max_steps: int
    timeout_seconds: int
    token_budget: int
    cost_budget_usd: float
    steps_used: int
    tokens_used: int
    cost_used_usd: float
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


class EventLogResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    sequence: int
    payload: dict
    created_at: dt.datetime

    model_config = {"from_attributes": True}
