"""CMDB管理Pydanticスキーマ"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CICreate(BaseModel):
    ci_name: str = Field(..., max_length=200)
    ci_type: str = Field(..., max_length=100)
    ci_class: str | None = None
    version: str | None = None
    owner_id: uuid.UUID | None = None
    description: str | None = None
    attributes: dict | None = None


class CIUpdate(BaseModel):
    ci_name: str | None = Field(None, max_length=200)
    ci_type: str | None = Field(None, max_length=100)
    ci_class: str | None = None
    status: str | None = None
    version: str | None = None
    description: str | None = None
    attributes: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Active", "Inactive", "Maintenance", "Retired"):
            raise ValueError(
                f"無効なステータス: {v}。"
                "Active/Inactive/Maintenance/Retired のいずれかを指定してください"
            )
        return v


class CIResponse(BaseModel):
    ci_id: uuid.UUID
    ci_name: str
    ci_type: str
    ci_class: str | None
    status: str
    version: str | None
    owner_id: uuid.UUID | None
    description: str | None
    attributes: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CIRelationshipCreate(BaseModel):
    source_ci_id: uuid.UUID
    target_ci_id: uuid.UUID
    relationship_type: str = Field(..., max_length=100)
    description: str | None = None


class CIRelationshipResponse(BaseModel):
    relationship_id: uuid.UUID
    source_ci_id: uuid.UUID
    target_ci_id: uuid.UUID
    relationship_type: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImpactAnalysisResponse(BaseModel):
    ci_id: uuid.UUID
    ci_name: str
    direct_dependents: list[CIResponse]
    transitive_count: int
