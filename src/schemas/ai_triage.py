"""AIトリアージPydanticスキーマ"""

import uuid

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    """手動トリアージ実行リクエスト"""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None


class TriageResponse(BaseModel):
    """トリアージ結果レスポンス"""

    priority: str
    category: str
    confidence: float
    reasoning: str
    provider: str  # 使用されたプロバイダー名


class IncidentTriageRequest(BaseModel):
    """既存インシデントのトリアージ実行リクエスト"""

    incident_id: uuid.UUID


class BatchTriageRequest(BaseModel):
    """バッチトリアージリクエスト"""

    incident_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)


class BatchTriageItem(BaseModel):
    """バッチトリアージの個別結果"""

    incident_id: uuid.UUID
    priority: str
    category: str
    confidence: float
    reasoning: str
    success: bool = True
    error: str | None = None


class BatchTriageResponse(BaseModel):
    """バッチトリアージレスポンス"""

    items: list[BatchTriageItem]
    total: int
    success_count: int
    failure_count: int


class ProviderInfoResponse(BaseModel):
    """現在のプロバイダー情報"""

    provider: str
    model: str | None = None
    description: str
