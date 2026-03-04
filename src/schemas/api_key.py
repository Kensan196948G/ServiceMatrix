"""APIキー Pydanticスキーマ"""

from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="APIキー名")
    rate_limit: int = Field(default=1000, ge=1, le=100000, description="レート制限（req/時間）")


class APIKeyResponse(BaseModel):
    id: str
    key_prefix: str
    name: str
    owner_id: str | None = None
    rate_limit: int
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class APIKeyCreateResponse(BaseModel):
    """作成時のみ生キーを含むレスポンス"""

    id: str
    key_prefix: str
    name: str
    raw_key: str = Field(..., description="APIキー（この応答でのみ表示されます）")
    rate_limit: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
