"""サービスリクエスト管理Pydanticスキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

VALID_SR_TRANSITIONS: dict[str, set[str]] = {
    "New": {"Pending_Approval", "In_Progress"},
    "Pending_Approval": {"Approved", "Rejected"},
    "Approved": {"In_Progress"},
    "In_Progress": {"Fulfilled", "Cancelled"},
    "Rejected": {"Cancelled"},
    "Fulfilled": set(),
    "Cancelled": set(),
}


class ServiceRequestCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    request_type: str | None = None
    requested_by: uuid.UUID | None = None
    due_date: datetime | None = None


class ServiceRequestUpdate(BaseModel):
    description: str | None = None
    status: str | None = None
    request_type: str | None = None
    assigned_to: uuid.UUID | None = None
    approved_by: uuid.UUID | None = None
    due_date: datetime | None = None


class ServiceRequestStatusTransition(BaseModel):
    target_status: str
    comment: str | None = None


class ServiceRequestResponse(BaseModel):
    request_id: uuid.UUID
    request_number: str
    title: str
    description: str | None
    status: str
    request_type: str | None
    requested_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    approved_by: uuid.UUID | None
    due_date: datetime | None
    fulfilled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
