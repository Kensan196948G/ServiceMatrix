"""変更管理Pydanticスキーマ"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ChangeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    change_type: str = Field(default="Normal", pattern="^(Standard|Normal|Emergency|Major)$")
    impact_level: str | None = Field(None, pattern="^(Low|Medium|High)$")
    urgency_level: str | None = Field(None, pattern="^(Low|Medium|High)$")
    implementation_plan: str | None = None
    rollback_plan: str | None = None
    test_plan: str | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None


class ChangeUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    impact_level: str | None = Field(None, pattern="^(Low|Medium|High)$")
    urgency_level: str | None = Field(None, pattern="^(Low|Medium|High)$")
    implementation_plan: str | None = None
    rollback_plan: str | None = None
    test_plan: str | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    assigned_to: uuid.UUID | None = None


class ChangeStatusTransition(BaseModel):
    new_status: str
    notes: str | None = None


class CABApproval(BaseModel):
    approved: bool
    notes: str | None = None


class ChangeResponse(BaseModel):
    change_id: uuid.UUID
    change_number: str
    title: str
    description: str | None
    change_type: str
    status: str
    risk_score: int
    risk_level: str | None
    impact_level: str | None
    urgency_level: str | None
    requested_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    cab_approved_by: uuid.UUID | None
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    cab_reviewed_at: datetime | None
    implementation_plan: str | None
    rollback_plan: str | None
    test_plan: str | None
    cab_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
