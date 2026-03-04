"""インシデント管理Pydanticスキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["本番DBサーバーの応答が停止"],
    )
    description: str | None = Field(
        None,
        examples=[
            "午前3時頃から本番DBサーバーへの接続がタイムアウトしている。"
            "アプリログにconnection refused多数。"
        ],
    )
    priority: str = Field(
        default="P3",
        pattern="^P[1-4]$",
        examples=["P1"],
        description="P1=緊急/P2=高/P3=中/P4=低",
    )
    category: str | None = Field(None, examples=["Infrastructure"])
    subcategory: str | None = Field(None, examples=["Database"])
    affected_service: str | None = Field(None, examples=["OrderService"])
    reported_by: uuid.UUID | None = Field(None, examples=["123e4567-e89b-12d3-a456-426614174000"])


class IncidentUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    priority: str | None = Field(None, pattern="^P[1-4]$")
    category: str | None = None
    affected_service: str | None = None
    assigned_to: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    resolution_notes: str | None = None


class IncidentBulkAssign(BaseModel):
    incident_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    assigned_to: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None


class BulkIncidentUpdate(BaseModel):
    incident_ids: list[uuid.UUID]
    action: str  # "close" | "assign" | "set_priority"
    assignee_id: uuid.UUID | None = None
    priority: str | None = None


class BulkIncidentResponse(BaseModel):
    updated_count: int
    failed_ids: list[uuid.UUID]


class IncidentStatusTransition(BaseModel):
    new_status: str
    notes: str | None = None


class IncidentResponse(BaseModel):
    incident_id: uuid.UUID
    incident_number: str
    title: str
    description: str | None
    priority: str
    status: str
    assigned_to: uuid.UUID | None
    assigned_team_id: uuid.UUID | None
    reported_by: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    sla_response_due_at: datetime | None
    sla_resolution_due_at: datetime | None
    sla_breached: bool
    category: str | None
    affected_service: str | None
    resolution_notes: str | None
    ai_triage_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
