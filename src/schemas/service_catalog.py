"""サービスカタログスキーマ"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ServiceCatalogCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    sla_hours: int | None = Field(None, ge=1)
    is_active: bool = True


class ServiceCatalogUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    sla_hours: int | None = Field(None, ge=1)
    is_active: bool | None = None


class ServiceCatalogResponse(BaseModel):
    catalog_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    sla_hours: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
