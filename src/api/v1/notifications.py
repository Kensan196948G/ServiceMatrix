"""通知設定 API エンドポイント"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.notification_settings import NotificationSettings
from src.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSettingsSchema(BaseModel):
    email: bool = True
    sla_breach: bool = True
    incident_created: bool = True
    change_approved: bool = False
    sr_completed: bool = False
    webhook_url: str = ""
    webhook_type: str = "slack"  # "slack" | "teams"

    model_config = {"json_schema_extra": {"example": {"email": True, "sla_breach": True}}}


class NotificationSettingsResponse(BaseModel):
    settings_id: uuid.UUID
    user_id: uuid.UUID
    settings: NotificationSettingsSchema
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    """現在のユーザーの通知設定を取得"""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == current_user.user_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        # デフォルト設定で新規作成
        record = NotificationSettings(user_id=current_user.user_id)
        db.add(record)
        await db.flush()

    settings_dict = json.loads(record.settings_json)
    return NotificationSettingsResponse(
        settings_id=record.settings_id,
        user_id=record.user_id,
        settings=NotificationSettingsSchema(**settings_dict),
        updated_at=record.updated_at,
    )


@router.patch("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettingsSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    """通知設定を更新"""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == current_user.user_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        record = NotificationSettings(user_id=current_user.user_id)
        db.add(record)

    record.settings_json = json.dumps(body.model_dump())
    record.updated_at = datetime.utcnow()
    await db.flush()

    settings_dict = json.loads(record.settings_json)
    return NotificationSettingsResponse(
        settings_id=record.settings_id,
        user_id=record.user_id,
        settings=NotificationSettingsSchema(**settings_dict),
        updated_at=record.updated_at,
    )


@router.delete("/settings", status_code=status.HTTP_204_NO_CONTENT)
async def reset_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """通知設定をデフォルトにリセット"""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == current_user.user_id)
    )
    record = result.scalar_one_or_none()
    if record:
        await db.delete(record)


class WebhookTestRequest(BaseModel):
    webhook_url: str
    webhook_type: str = "slack"


class WebhookTestResponse(BaseModel):
    success: bool
    message: str


@router.post("/settings/test-webhook", response_model=WebhookTestResponse)
async def test_webhook(
    body: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
) -> WebhookTestResponse:
    """Webhook URL接続テスト"""
    from src.services.notification_webhook_service import send_webhook_notification

    success = await send_webhook_notification(
        body.webhook_url,
        body.webhook_type,  # type: ignore[arg-type]
        "ServiceMatrix接続テスト成功 ✅",
        "ServiceMatrix テスト通知",
    )
    return WebhookTestResponse(
        success=success,
        message="送信成功" if success else "送信失敗（URL・権限を確認してください）",
    )
