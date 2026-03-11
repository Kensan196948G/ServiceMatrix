"""Feature Flag スキーマ - Issue #90, Phase 9-DEPLOY-1"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FeatureFlagCreate(BaseModel):
    """Feature Flag 作成リクエスト"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_\-]+$",
        description="フラグ識別名（小文字英数字・アンダースコア・ハイフン）",
        examples=["new_incident_ui", "ai_triage_v2"],
    )
    description: str | None = Field(None, max_length=500)
    is_enabled: bool = Field(False, description="グローバル有効フラグ")
    rollout_percentage: float = Field(
        100.0,
        ge=0.0,
        le=100.0,
        description="有効にするユーザー割合（0.0〜100.0）",
    )
    tenant_id: uuid.UUID | None = Field(
        None,
        description="特定テナント限定。null は全テナント対象",
    )
    metadata_json: str | None = Field(None, description="追加設定（JSON文字列）")

    @field_validator("name")
    @classmethod
    def name_must_be_lowercase(cls, v: str) -> str:
        return v.lower()


class FeatureFlagUpdate(BaseModel):
    """Feature Flag 更新リクエスト"""

    description: str | None = Field(None, max_length=500)
    is_enabled: bool | None = None
    rollout_percentage: float | None = Field(None, ge=0.0, le=100.0)
    tenant_id: uuid.UUID | None = None
    metadata_json: str | None = None


class FeatureFlagResponse(BaseModel):
    """Feature Flag レスポンス"""

    flag_id: uuid.UUID
    name: str
    description: str | None
    is_enabled: bool
    rollout_percentage: float
    tenant_id: uuid.UUID | None
    metadata_json: str | None
    created_at: datetime
    updated_at: datetime
    updated_by: str | None

    model_config = {"from_attributes": True}


class FeatureFlagEvaluation(BaseModel):
    """Feature Flag 評価結果"""

    flag_name: str
    is_active: bool = Field(description="このコンテキストでフラグが有効かどうか")
    reason: str = Field(description="有効/無効の理由")
