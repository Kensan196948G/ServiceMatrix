"""Slack/Teams Webhook設定スキーマ"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


class WebhookConfigCreate(BaseModel):
    """Webhook設定作成スキーマ"""

    name: str
    url: str
    webhook_type: str  # "slack" | "teams"
    is_active: bool = True
    event_filters: dict[str, Any] = {}
    retry_count: int = 3

    @field_validator("webhook_type")
    @classmethod
    def validate_webhook_type(cls, v: str) -> str:
        if v not in ("slack", "teams"):
            raise ValueError("webhook_type must be 'slack' or 'teams'")
        return v


class WebhookConfigUpdate(BaseModel):
    """Webhook設定更新スキーマ"""

    name: str | None = None
    url: str | None = None
    webhook_type: str | None = None
    is_active: bool | None = None
    event_filters: dict[str, Any] | None = None
    retry_count: int | None = None

    @field_validator("webhook_type")
    @classmethod
    def validate_webhook_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("slack", "teams"):
            raise ValueError("webhook_type must be 'slack' or 'teams'")
        return v


class WebhookConfigResponse(BaseModel):
    """Webhook設定レスポンススキーマ"""

    id: int
    name: str
    url: str
    webhook_type: str
    is_active: bool
    event_filters: dict[str, Any]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    """Webhookテスト送信リクエスト"""

    message: str = "ServiceMatrix テスト通知"
    title: str = "テスト送信"


class WebhookTestResponse(BaseModel):
    """Webhookテスト送信レスポンス"""

    success: bool
    webhook_id: int
    webhook_type: str
    message: str
