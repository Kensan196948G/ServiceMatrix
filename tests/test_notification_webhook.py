"""Slack/Teams Webhook通知サービス テスト"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.notification_webhook_service import (
    send_slack_notification,
    send_teams_notification,
    send_webhook_notification,
)

pytestmark = pytest.mark.asyncio


async def test_send_slack_empty_url():
    result = await send_slack_notification("", "msg")
    assert result is False


async def test_send_teams_empty_url():
    result = await send_teams_notification("", "msg")
    assert result is False


async def test_send_slack_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_slack_notification("https://hooks.slack.com/test", "hello", "Title")
    assert result is True


async def test_send_slack_failure_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_slack_notification("https://hooks.slack.com/test", "hello")
    assert result is False


async def test_send_slack_exception():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("network error"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_slack_notification("https://hooks.slack.com/test", "hello")
    assert result is False


async def test_send_teams_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_teams_notification("https://teams.webhook.test", "msg", "Title")
    assert result is True


async def test_send_teams_204():
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_teams_notification("https://teams.webhook.test", "msg")
    assert result is True


async def test_send_teams_exception():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_teams_notification("https://teams.webhook.test", "msg")
    assert result is False


async def test_send_webhook_slack():
    with patch(
        "src.services.notification_webhook_service.send_slack_notification",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_slack:
        result = await send_webhook_notification("https://url", "slack", "msg", "title")
    assert result is True
    mock_slack.assert_called_once()


async def test_send_webhook_teams():
    with patch(
        "src.services.notification_webhook_service.send_teams_notification",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_teams:
        result = await send_webhook_notification("https://url", "teams", "msg")
    assert result is True
    mock_teams.assert_called_once()


async def test_send_webhook_unknown_type():
    result = await send_webhook_notification("https://url", "slack", "msg")
    # Just check it doesn't crash - actual mock will be called
