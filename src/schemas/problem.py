"""問題管理Pydanticスキーマ"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    category: str | None = None
    affected_service: str | None = None
    reported_by: uuid.UUID | None = None


class ProblemUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    priority: str | None = Field(None, pattern="^P[1-4]$")
    category: str | None = None
    affected_service: str | None = None
    assigned_to: uuid.UUID | None = None
    root_cause: str | None = None


class ProblemStatusTransition(BaseModel):
    new_status: str
    notes: str | None = None


class KnownErrorUpdate(BaseModel):
    workaround: str = Field(..., min_length=1)


class ProblemResponse(BaseModel):
    problem_id: uuid.UUID
    problem_number: str
    title: str
    description: str | None
    priority: str
    status: str
    root_cause: str | None
    known_error: bool
    workaround: str | None
    assigned_to: uuid.UUID | None
    reported_by: uuid.UUID | None
    resolved_at: datetime | None
    closed_at: datetime | None
    category: str | None
    affected_service: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
