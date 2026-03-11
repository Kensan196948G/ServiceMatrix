"""Organization スキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    settings: dict = Field(default_factory=dict)


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    settings: dict
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
