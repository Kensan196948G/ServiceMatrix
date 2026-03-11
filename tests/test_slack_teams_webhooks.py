"""Slack/Teams Webhook通知統合テスト (Issue #55)"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.webhook import WebhookConfig
from src.services.slack_teams_webhook_service import (
    _passes_filter,
    dispatch_incident_event,
    send_slack_message,
    send_teams_message,
    send_webhook_with_retry,
)


# ─── ヘルパー ────────────────────────────────────────────────────────────────


def _make_webhook_config(
    webhook_type: str = "slack",
    url: str = "https://hooks.slack.com/services/TEST",
    is_active: bool = True,
    event_filters: dict | None = None,
    retry_count: int = 3,
) -> WebhookConfig:
    """テスト用WebhookConfigオブジェクトを作成"""
    config = WebhookConfig()
    config.id = 1
    config.name = "Test Webhook"
    config.url = url
    config.webhook_type = webhook_type
    config.is_active = is_active
    config.event_filters = event_filters or {}
    config.retry_count = retry_count
    return config


# ─── test_create_webhook_config ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_webhook_config(client, auth_headers):
    """Webhook設定作成 - POST /api/v1/integrations/webhooks"""
    payload = {
        "name": "Slack Alert",
        "url": "https://hooks.slack.com/services/ABC/DEF/GHI",
        "webhook_type": "slack",
        "is_active": True,
        "event_filters": {"priorities": ["P1", "P2"]},
        "retry_count": 3,
    }
    resp = await client.post(
        "/api/v1/integrations/webhooks",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Slack Alert"
    assert data["webhook_type"] == "slack"
    assert data["is_active"] is True
    assert data["event_filters"]["priorities"] == ["P1", "P2"]


# ─── test_list_webhook_configs ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_webhook_configs(client, auth_headers):
    """Webhook設定一覧取得 - GET /api/v1/integrations/webhooks"""
    # まず1件作成
    payload = {
        "name": "Teams Alert",
        "url": "https://teams.webhook.office.com/webhookb2/test",
        "webhook_type": "teams",
        "is_active": True,
        "event_filters": {},
        "retry_count": 2,
    }
    create_resp = await client.post(
        "/api/v1/integrations/webhooks",
        json=payload,
        headers=auth_headers,
    )
    assert create_resp.status_code == 201

    list_resp = await client.get(
        "/api/v1/integrations/webhooks",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1


# ─── test_webhook_slack_send ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_webhook_slack_send():
    """Slack Webhook送信 - httpx モック"""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.services.slack_teams_webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await send_slack_message(
            "https://hooks.slack.com/services/TEST",
            {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]},
        )

    assert result is True


# ─── test_webhook_teams_send ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_webhook_teams_send():
    """Teams Webhook送信 - httpx モック"""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.services.slack_teams_webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await send_teams_message(
            "https://teams.webhook.office.com/webhookb2/test",
            {
                "@type": "MessageCard",
                "summary": "Test",
                "sections": [{"activityTitle": "Test"}],
            },
        )

    assert result is True


# ─── test_webhook_retry_on_failure ───────────────────────────────────────────


@pytest.mark.anyio
async def test_webhook_retry_on_failure():
    """失敗時リトライ - 3回リトライして全て失敗した場合Falseを返す"""
    config = _make_webhook_config(webhook_type="slack", retry_count=3)

    call_count = 0

    async def failing_send(url: str, payload: dict) -> bool:
        nonlocal call_count
        call_count += 1
        return False

    with patch(
        "src.services.slack_teams_webhook_service.send_slack_message",
        side_effect=failing_send,
    ):
        with patch("src.services.slack_teams_webhook_service.asyncio.sleep", new=AsyncMock()):
            result = await send_webhook_with_retry(
                config,
                "incident_created",
                {"title": "Test", "description": "Test", "priority": "P1"},
                max_retries=3,
            )

    assert result is False
    assert call_count == 3


# ─── test_webhook_filter_by_priority ─────────────────────────────────────────


def test_webhook_filter_by_priority():
    """優先度フィルタ動作 - P3インシデントはP1/P2フィルタをパスしない"""
    config = _make_webhook_config(
        event_filters={"priorities": ["P1", "P2"]}
    )

    # P1は通過
    assert _passes_filter(config, "incident_created", {"priority": "P1"}) is True
    # P3は遮断
    assert _passes_filter(config, "incident_created", {"priority": "P3"}) is False
    # フィルタなしは通過
    config_no_filter = _make_webhook_config(event_filters={})
    assert _passes_filter(config_no_filter, "incident_created", {"priority": "P3"}) is True


# ─── test_webhook_dispatch_incident_event ────────────────────────────────────


@pytest.mark.anyio
async def test_webhook_dispatch_incident_event():
    """インシデントイベント配信 - アクティブなWebhook設定に送信"""
    config = _make_webhook_config(
        webhook_type="slack",
        url="https://hooks.slack.com/services/TEST",
        is_active=True,
    )

    mock_incident = MagicMock()
    mock_incident.title = "テストインシデント"
    mock_incident.description = "説明"
    mock_incident.priority = "P1"
    mock_incident.status = "New"
    mock_incident.incident_number = "INC-2026-000001"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [config]
    mock_db.execute = AsyncMock(return_value=mock_result)

    dispatch_calls = []

    async def fake_send_with_retry(cfg, event_type, data, max_retries=3):
        dispatch_calls.append({"event_type": event_type, "cfg": cfg, "data": data})
        return True

    with patch(
        "src.services.slack_teams_webhook_service.send_webhook_with_retry",
        side_effect=fake_send_with_retry,
    ):
        await dispatch_incident_event(mock_db, "incident_created", mock_incident)

    assert len(dispatch_calls) == 1
    assert dispatch_calls[0]["event_type"] == "incident_created"
    assert dispatch_calls[0]["data"]["title"] == "テストインシデント"
    assert dispatch_calls[0]["data"]["priority"] == "P1"


# ─── test_webhook_send_empty_url ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_webhook_send_empty_url():
    """URLが空の場合は即座にFalseを返す"""
    result_slack = await send_slack_message("", {"text": "test"})
    result_teams = await send_teams_message("", {"@type": "MessageCard"})
    assert result_slack is False
    assert result_teams is False


# ─── test_webhook_retry_success_on_second_attempt ────────────────────────────


@pytest.mark.anyio
async def test_webhook_retry_success_on_second_attempt():
    """2回目のリトライで成功する場合Trueを返す"""
    config = _make_webhook_config(webhook_type="teams", retry_count=3)

    call_count = 0

    async def flaky_send(url: str, payload: dict) -> bool:
        nonlocal call_count
        call_count += 1
        return call_count >= 2  # 2回目以降は成功

    with patch(
        "src.services.slack_teams_webhook_service.send_teams_message",
        side_effect=flaky_send,
    ):
        with patch("src.services.slack_teams_webhook_service.asyncio.sleep", new=AsyncMock()):
            result = await send_webhook_with_retry(
                config,
                "incident_updated",
                {"title": "Update", "description": "", "priority": "P2"},
                max_retries=3,
            )

    assert result is True
    assert call_count == 2
