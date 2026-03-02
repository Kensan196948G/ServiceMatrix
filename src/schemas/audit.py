"""監査ログ スキーマ"""
import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    entity_type: str | None
    entity_id: str | None
    action: str
    user_id: uuid.UUID | None
    changes: dict | None
    sequence_number: int
    current_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def map_model_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return {
                "id": getattr(data, "log_id", None),
                "entity_type": getattr(data, "resource_type", None),
                "entity_id": getattr(data, "resource_id", None),
                "action": getattr(data, "action", None),
                "user_id": getattr(data, "user_id", None),
                "changes": getattr(data, "new_values", None),
                "sequence_number": getattr(data, "sequence_number", None),
                "current_hash": getattr(data, "current_hash", None),
                "created_at": getattr(data, "created_at", None),
            }
        return data


class HashChainVerifyResponse(BaseModel):
    is_valid: bool
    checked_count: int
    first_invalid_sequence: int | None
    message: str
