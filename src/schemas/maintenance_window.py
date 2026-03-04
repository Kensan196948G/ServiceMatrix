"""メンテナンスウィンドウスキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MaintenanceWindowCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurrence_rule: str | None = Field(None, max_length=200)
    is_active: bool = True


class MaintenanceWindowUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = Field(None, max_length=200)
    is_active: bool | None = None


class MaintenanceWindowResponse(BaseModel):
    window_id: uuid.UUID
    name: str
    description: str | None
    start_time: datetime
    end_time: datetime
    is_recurring: bool
    recurrence_rule: str | None
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
