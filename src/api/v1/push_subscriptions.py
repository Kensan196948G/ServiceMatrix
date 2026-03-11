"""Web Push サブスクリプション管理 API

ブラウザの Push 購読情報を登録・削除・一覧する。
VAPID キーの公開鍵を返すエンドポイントも提供する。
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.push_subscription import PushSubscription

try:
    from pywebpush import webpush as _pywebpush_webpush
except ModuleNotFoundError:
    _pywebpush_webpush = None  # type: ignore[assignment]


def webpush(*args, **kwargs):  # type: ignore[misc]
    """pywebpush.webpush ラッパー（テスト・モック差し替え可能）"""
    if _pywebpush_webpush is None:
        raise ImportError("pywebpush がインストールされていません")
    return _pywebpush_webpush(*args, **kwargs)

router = APIRouter(prefix="/push-subscriptions", tags=["push-subscriptions"])


# ── Pydantic スキーマ ──────────────────────────────────────────────────────────


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys
    user_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    device_label: str | None = None


class SubscriptionResponse(BaseModel):
    subscription_id: uuid.UUID
    endpoint: str
    device_label: str | None
    user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class VapidPublicKeyResponse(BaseModel):
    public_key: str


# ── エンドポイント ────────────────────────────────────────────────────────────


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key() -> VapidPublicKeyResponse:
    """VAPID 公開鍵を返す（ブラウザでの Push 購読時に必要）"""
    public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    if not public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VAPID_PUBLIC_KEY が設定されていません",
        )
    return VapidPublicKeyResponse(public_key=public_key)


@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    body: SubscribeRequest,
    session: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Push サブスクリプション登録

    同一エンドポイントが既存の場合は上書き（upsert）する。
    """
    # 既存サブスクリプション確認
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 既存を更新
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
        existing.user_id = body.user_id
        existing.tenant_id = body.tenant_id
        existing.device_label = body.device_label
        await session.flush()
        await session.refresh(existing)
        sub = existing
    else:
        sub = PushSubscription(
            endpoint=body.endpoint,
            p256dh=body.keys.p256dh,
            auth=body.keys.auth,
            user_id=body.user_id,
            tenant_id=body.tenant_id,
            device_label=body.device_label,
        )
        session.add(sub)
        await session.flush()
        await session.refresh(sub)

    return SubscriptionResponse(
        subscription_id=sub.subscription_id,
        endpoint=sub.endpoint,
        device_label=sub.device_label,
        user_id=sub.user_id,
        tenant_id=sub.tenant_id,
    )


@router.get("/", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[SubscriptionResponse]:
    """サブスクリプション一覧"""
    query = select(PushSubscription)
    if user_id:
        query = query.where(PushSubscription.user_id == user_id)
    if tenant_id:
        query = query.where(PushSubscription.tenant_id == tenant_id)
    result = await session.execute(query)
    subs = result.scalars().all()
    return [
        SubscriptionResponse(
            subscription_id=s.subscription_id,
            endpoint=s.endpoint,
            device_label=s.device_label,
            user_id=s.user_id,
            tenant_id=s.tenant_id,
        )
        for s in subs
    ]


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Push サブスクリプション削除"""
    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サブスクリプションが見つかりません",
        )
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.subscription_id == subscription_id
        )
    )


@router.post("/send-test", status_code=status.HTTP_200_OK)
async def send_test_notification(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """テスト Push 通知送信（開発・デバッグ用）"""
    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サブスクリプションが見つかりません",
        )

    vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "")
    vapid_public = os.environ.get("VAPID_PUBLIC_KEY", "")
    vapid_email = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.com")

    if not vapid_private or not vapid_public:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VAPID キーが設定されていません",
        )

    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data='{"title":"テスト通知","body":"ServiceMatrix からのテスト通知です"}',
            vapid_private_key=vapid_private,
            vapid_claims={"sub": f"mailto:{vapid_email}"},
        )
        return {"status": "sent"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Push 送信失敗: {exc}",
        ) from exc
