"""通知サービス テスト"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.notification_service import NotificationService, notification_service

# ─── ヘルパー ────────────────────────────────────────────────────────────────


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"number": 42, "html_url": "https://github.com/test/repo/issues/42"}
    resp.raise_for_status = MagicMock()
    return resp


# ─── テストケース ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notify_sla_breach_no_config():
    """設定なし → スキップして空dictを返す"""
    service = NotificationService()
    with (
        patch("src.services.notification_service.settings") as mock_settings,
    ):
        mock_settings.github_token = ""
        mock_settings.github_repo = ""
        mock_settings.alert_webhook_enabled = False
        mock_settings.alert_webhook_url = ""

        result = await service.notify_sla_breach(
            incident_number="INC-001",
            incident_title="Test",
            priority="P1",
            breach_type="resolution",
        )

    assert result == {}


@pytest.mark.asyncio
async def test_notify_github_issue_success(monkeypatch):
    """GitHub Token設定あり → httpx.AsyncClient.post が呼ばれる"""
    service = NotificationService()
    mock_resp = _mock_response(201, {"number": 99, "html_url": "https://github.com/test/issues/99"})

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_testtoken"  # noqa: S105
        mock_settings.github_repo = "owner/repo"
        mock_settings.alert_webhook_enabled = False
        mock_settings.alert_webhook_url = ""

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.notify_sla_breach(
                incident_number="INC-001",
                incident_title="Test Incident",
                priority="P1",
                breach_type="resolution",
            )

    assert "github_issue" in result
    assert result["github_issue"]["number"] == 99
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_notify_github_issue_failure_graceful(monkeypatch):
    """GitHub API失敗 → graceful degradation（例外を投げない）"""
    service = NotificationService()

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_testtoken"  # noqa: S105
        mock_settings.github_repo = "owner/repo"
        mock_settings.alert_webhook_enabled = False
        mock_settings.alert_webhook_url = ""

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("API error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.notify_sla_breach(
                incident_number="INC-001",
                incident_title="Test",
                priority="P1",
                breach_type="resolution",
            )

    # 例外が発生せず、Noneが返る
    assert result.get("github_issue") is None


@pytest.mark.asyncio
async def test_notify_webhook_success(monkeypatch):
    """Webhook有効 → POSTが送信される"""
    service = NotificationService()
    mock_resp = _mock_response(200, {})

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = ""
        mock_settings.github_repo = ""
        mock_settings.alert_webhook_enabled = True
        mock_settings.alert_webhook_url = "https://hooks.example.com/webhook"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.notify_sla_breach(
                incident_number="INC-002",
                incident_title="Webhook Test",
                priority="P2",
                breach_type="response",
            )

    assert "webhook" in result
    assert result["webhook"]["status"] == "sent"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_notify_webhook_disabled():
    """Webhook無効 → 送信されない"""
    service = NotificationService()

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = ""
        mock_settings.github_repo = ""
        mock_settings.alert_webhook_enabled = False
        mock_settings.alert_webhook_url = "https://hooks.example.com/webhook"

        result = await service.notify_sla_breach(
            incident_number="INC-003",
            incident_title="Disabled Test",
            priority="P3",
            breach_type="resolution",
        )

    assert "webhook" not in result
    assert result == {}


@pytest.mark.asyncio
async def test_notify_webhook_failure_graceful(monkeypatch):
    """Webhook失敗 → graceful degradation"""
    service = NotificationService()

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = ""
        mock_settings.github_repo = ""
        mock_settings.alert_webhook_enabled = True
        mock_settings.alert_webhook_url = "https://hooks.example.com/webhook"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.notify_sla_breach(
                incident_number="INC-004",
                incident_title="Failure Test",
                priority="P1",
                breach_type="response",
            )

    # 例外が発生せず、Noneが返る
    assert result.get("webhook") is None


@pytest.mark.asyncio
async def test_sla_monitor_calls_notification(monkeypatch):
    """check_sla_breaches で通知が呼ばれることを確認"""
    import uuid
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from src.models.incident import Incident
    from src.services.sla_monitor_service import SLAMonitorService

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Incident.__table__.create, checkfirst=True)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    notify_mock = AsyncMock(return_value={})

    async with async_session() as session:
        now = datetime.now(UTC)
        past = now - timedelta(hours=1)
        incident = Incident(
            incident_id=uuid.uuid4(),
            incident_number="INC-MON-001",
            title="Monitor Test",
            priority="P1",
            status="In_Progress",
            sla_breached=False,
            sla_response_due_at=now + timedelta(minutes=30),
            sla_resolution_due_at=past,
            created_at=now,
            updated_at=now,
        )
        session.add(incident)
        await session.flush()

        service = SLAMonitorService()
        audit_patch = "src.services.sla_monitor_service.audit_service.record_audit_log"
        with (
            patch(audit_patch, new=AsyncMock()),
            patch(
                "src.services.sla_monitor_service.notification_service.notify_sla_breach",
                new=notify_mock,
            ),
        ):
            count = await service.check_sla_breaches(session)

    assert count >= 1
    notify_mock.assert_called_once()
    call_kwargs = notify_mock.call_args.kwargs
    assert call_kwargs["incident_number"] == "INC-MON-001"
    assert call_kwargs["breach_type"] == "resolution"

    await engine.dispose()


@pytest.mark.asyncio
async def test_notify_sla_breach_both_channels(monkeypatch):
    """GitHub + Webhookの両方が呼ばれる"""
    service = NotificationService()
    github_resp = _mock_response(201, {"number": 10, "html_url": "https://github.com/test/issues/10"})
    webhook_resp = _mock_response(200, {})

    call_count = 0

    async def mock_post(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "api.github.com" in url:
            return github_resp
        return webhook_resp

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_testtoken"  # noqa: S105
        mock_settings.github_repo = "owner/repo"
        mock_settings.alert_webhook_enabled = True
        mock_settings.alert_webhook_url = "https://hooks.example.com/webhook"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.notify_sla_breach(
                incident_number="INC-005",
                incident_title="Both Channels",
                priority="P1",
                breach_type="resolution",
            )

    assert "github_issue" in result
    assert "webhook" in result
    assert call_count == 2


def test_notification_service_singleton():
    """notification_serviceがNotificationServiceインスタンスであること"""
    assert isinstance(notification_service, NotificationService)
