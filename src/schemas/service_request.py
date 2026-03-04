"""サービスリクエスト管理Pydanticスキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

VALID_SR_TRANSITIONS: dict[str, set[str]] = {
    "New": {"Pending_Approval", "In_Progress"},
    "Pending_Approval": {"Approved", "Rejected"},
    "Approved": {"In_Progress", "In_Fulfillment"},
    "In_Progress": {"Fulfilled", "Cancelled"},
    "In_Fulfillment": {"Fulfilled", "Failed"},
    "Fulfilled": {"Closed"},
    "Failed": {"Closed"},
    "Rejected": {"Cancelled", "Closed"},
    "Cancelled": set(),
    "Closed": set(),
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


class ServiceRequestApprovalAction(BaseModel):
    actor: str = Field(..., description="承認/却下者のユーザーID or 名前")
    comment: str = ""


class ServiceRequestCompleteAction(BaseModel):
    success: bool = True


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
    catalog_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceRequestToIncidentRequest(BaseModel):
    """SRからインシデント自動生成リクエスト"""

    priority: str = Field(default="P3", pattern="^P[1-4]$")
    category: str | None = None
    additional_notes: str | None = None


class ServiceRequestToIncidentResponse(BaseModel):
    """SRからインシデント自動生成レスポンス"""

    incident_id: uuid.UUID
    incident_number: str
    service_request_id: uuid.UUID
    service_request_number: str
    message: str
