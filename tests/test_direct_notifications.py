"""notifications.py エンドポイント直接呼び出しテスト - カバレッジ向上

ASGI TestClient では async 関数ボディが追跡されないため、
直接呼び出しパターンで全分岐をカバーする。

対象: src/api/v1/notifications.py
カバー対象行: 47-59, 74-88, 102-107, 126-134
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────

DEFAULT_SETTINGS_JSON = json.dumps(
    {
        "email": True,
        "sla_breach": True,
        "incident_created": True,
        "change_approved": False,
        "sr_completed": False,
        "webhook_url": "",
        "webhook_type": "slack",
    }
)


def _make_user():
    user = MagicMock()
    user.user_id = uuid.uuid4()
    return user


def _make_settings_record(user_id=None):
    record = MagicMock()
    record.settings_id = uuid.uuid4()
    record.user_id = user_id or uuid.uuid4()
    record.settings_json = DEFAULT_SETTINGS_JSON
    record.updated_at = datetime.now(timezone.utc)
    return record


def _make_execute_result(scalar_one_or_none=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    return result


# ─── get_notification_settings ─────────────────────────────────────────────────


async def test_get_settings_existing_record():
    """get_notification_settings: 既存レコードあり → settings を返す"""
    from src.api.v1.notifications import get_notification_settings

    current_user = _make_user()
    record = _make_settings_record(user_id=current_user.user_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=record))

    result = await get_notification_settings(current_user=current_user, db=db)

    assert result.user_id == current_user.user_id
    assert result.settings.email is True
    assert result.settings.sla_breach is True


async def test_get_settings_no_record_creates_default():
    """get_notification_settings: レコードなし → デフォルト作成（lines 52-56）"""
    from src.api.v1.notifications import get_notification_settings

    current_user = _make_user()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=None))

    # db.add は await されない同期呼び出しのため MagicMock で side_effect を設定
    # （ORM column default は実 DB flush まで未適用のため属性を初期化する）
    def _init_record(record):
        record.settings_id = uuid.uuid4()
        record.settings_json = DEFAULT_SETTINGS_JSON
        record.updated_at = datetime.now(timezone.utc)

    db.add = MagicMock(side_effect=_init_record)

    result = await get_notification_settings(current_user=current_user, db=db)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result.user_id == current_user.user_id


async def test_get_settings_returns_response_schema():
    """get_notification_settings: NotificationSettingsResponse 形式で返す"""
    from src.api.v1.notifications import get_notification_settings, NotificationSettingsResponse

    current_user = _make_user()
    record = _make_settings_record(user_id=current_user.user_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=record))

    result = await get_notification_settings(current_user=current_user, db=db)

    assert isinstance(result, NotificationSettingsResponse)


# ─── update_notification_settings ─────────────────────────────────────────────


async def test_update_settings_existing_record():
    """update_notification_settings: 既存レコード更新 (lines 74-93)"""
    from src.api.v1.notifications import (
        update_notification_settings,
        NotificationSettingsSchema,
    )

    current_user = _make_user()
    record = _make_settings_record(user_id=current_user.user_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=record))

    body = NotificationSettingsSchema(
        email=False,
        sla_breach=False,
        incident_created=True,
        change_approved=True,
        sr_completed=True,
        webhook_url="https://hooks.example.com",
        webhook_type="teams",
    )

    result = await update_notification_settings(
        body=body, current_user=current_user, db=db
    )

    # settings_json が更新される
    assert record.settings_json == json.dumps(body.model_dump())
    db.flush.assert_called_once()


async def test_update_settings_creates_when_not_found():
    """update_notification_settings: レコードなし → 新規作成 (lines 79-81)"""
    from src.api.v1.notifications import (
        update_notification_settings,
        NotificationSettingsSchema,
    )

    current_user = _make_user()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=None))

    body = NotificationSettingsSchema(email=True)

    # db.add は await されない同期呼び出しのため MagicMock で side_effect を設定
    def _init_record(record):
        record.settings_id = uuid.uuid4()
        record.updated_at = datetime.now(timezone.utc)

    db.add = MagicMock(side_effect=_init_record)

    result = await update_notification_settings(
        body=body, current_user=current_user, db=db
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()


async def test_update_settings_updates_settings_json():
    """update_notification_settings: settings_json が body の内容に更新される"""
    from src.api.v1.notifications import (
        update_notification_settings,
        NotificationSettingsSchema,
    )

    current_user = _make_user()
    record = _make_settings_record(user_id=current_user.user_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=record))

    body = NotificationSettingsSchema(
        email=False,
        sla_breach=True,
        incident_created=False,
        change_approved=False,
        sr_completed=False,
        webhook_url="https://webhook.test.com",
        webhook_type="slack",
    )

    await update_notification_settings(body=body, current_user=current_user, db=db)

    updated = json.loads(record.settings_json)
    assert updated["email"] is False
    assert updated["webhook_url"] == "https://webhook.test.com"


# ─── reset_notification_settings ──────────────────────────────────────────────


async def test_reset_settings_existing_record():
    """reset_notification_settings: 既存レコード削除 (lines 102-107)"""
    from src.api.v1.notifications import reset_notification_settings

    current_user = _make_user()
    record = _make_settings_record(user_id=current_user.user_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=record))

    result = await reset_notification_settings(current_user=current_user, db=db)

    db.delete.assert_called_once_with(record)
    assert result is None


async def test_reset_settings_no_record():
    """reset_notification_settings: レコードなし → 何もしない"""
    from src.api.v1.notifications import reset_notification_settings

    current_user = _make_user()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(scalar_one_or_none=None))

    result = await reset_notification_settings(current_user=current_user, db=db)

    db.delete.assert_not_called()
    assert result is None


# ─── test_webhook ─────────────────────────────────────────────────────────────


async def test_webhook_success():
    """test_webhook: 送信成功 → success=True, message='送信成功' (lines 126-137)"""
    from src.api.v1.notifications import test_webhook, WebhookTestRequest

    current_user = _make_user()
    body = WebhookTestRequest(
        webhook_url="https://hooks.slack.com/services/test", webhook_type="slack"
    )

    # ローカルインポート `from src.services.notification_webhook_service import ...`
    # のためソースモジュールをパッチする
    with patch(
        "src.services.notification_webhook_service.send_webhook_notification",
        new=AsyncMock(return_value=True),
    ):
        result = await test_webhook(body=body, current_user=current_user)

    assert result.success is True
    assert result.message == "送信成功"


async def test_webhook_failure():
    """test_webhook: 送信失敗 → success=False, 失敗メッセージ"""
    from src.api.v1.notifications import test_webhook, WebhookTestRequest

    current_user = _make_user()
    body = WebhookTestRequest(
        webhook_url="https://invalid-url.example.com", webhook_type="teams"
    )

    with patch(
        "src.services.notification_webhook_service.send_webhook_notification",
        new=AsyncMock(return_value=False),
    ):
        result = await test_webhook(body=body, current_user=current_user)

    assert result.success is False
    assert "失敗" in result.message


async def test_webhook_calls_service_with_correct_args():
    """test_webhook: send_webhook_notification に正しい引数が渡される"""
    from src.api.v1.notifications import test_webhook, WebhookTestRequest

    current_user = _make_user()
    webhook_url = "https://hooks.slack.com/services/test123"
    body = WebhookTestRequest(webhook_url=webhook_url, webhook_type="slack")

    with patch(
        "src.services.notification_webhook_service.send_webhook_notification",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        await test_webhook(body=body, current_user=current_user)

    mock_send.assert_called_once_with(
        webhook_url,
        "slack",
        "ServiceMatrix接続テスト成功 ✅",
        "ServiceMatrix テスト通知",
    )
