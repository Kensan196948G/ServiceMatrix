"""GitHub Issue 双方向同期テスト（Issue #40）"""

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ---------- Fixtures ----------


@pytest_asyncio.fixture
async def incident(db_session):
    """テスト用インシデントを作成"""
    from src.models.incident import Incident, IncidentPriority, IncidentStatus

    inc = Incident(
        incident_number=f"INC-2026-{uuid.uuid4().hex[:8].upper()}",
        title="GitHub同期テストインシデント",
        description="テスト用",
        priority=IncidentPriority.P2,
        status=IncidentStatus.NEW,
    )
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)
    return inc


@pytest_asyncio.fixture
async def incident_with_github(db_session):
    """GitHub Issue番号を持つインシデント"""
    import random

    from src.models.incident import Incident, IncidentPriority, IncidentStatus

    github_issue_number = random.randint(10000, 99999)
    inc = Incident(
        incident_number=f"INC-2026-{uuid.uuid4().hex[:8].upper()}",
        title="GitHub連携済みインシデント",
        description="テスト用",
        priority=IncidentPriority.P1,
        status=IncidentStatus.IN_PROGRESS,
        github_issue_number=github_issue_number,
    )
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)
    return inc


def _make_webhook_sig(body: bytes, secret: str = "test-secret") -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ---------- NotificationService テスト ----------


class TestNotificationServiceGitHub:
    async def test_create_incident_github_issue_success(self):
        """インシデント作成時にGitHub Issueを生成できる"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 99}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.services.notification_service.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.github_token = "ghp_token"
            mock_settings.github_repo = "org/repo"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await svc.create_incident_github_issue(
                "INC-2026-001", "テストインシデント", "P2", "詳細説明"
            )
        assert result == 99

    async def test_create_incident_github_issue_no_token(self):
        """GitHub token未設定時はNoneを返す"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        with patch("src.services.notification_service.settings") as mock_settings:
            mock_settings.github_token = ""
            mock_settings.github_repo = "org/repo"
            result = await svc.create_incident_github_issue("INC-001", "Test", "P3")
        assert result is None

    async def test_close_incident_github_issue_success(self):
        """GitHub Issueをクローズできる"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.services.notification_service.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.github_token = "ghp_token"
            mock_settings.github_repo = "org/repo"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.patch = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await svc.close_incident_github_issue(42, "INC-2026-001")
        assert result is True

    async def test_close_incident_github_issue_no_token(self):
        """GitHub token未設定時はFalseを返す"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        with patch("src.services.notification_service.settings") as mock_settings:
            mock_settings.github_token = ""
            mock_settings.github_repo = "org/repo"
            result = await svc.close_incident_github_issue(42, "INC-001")
        assert result is False

    async def test_add_github_issue_comment_success(self):
        """GitHub Issueにコメントを追加できる"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.services.notification_service.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.github_token = "ghp_token"
            mock_settings.github_repo = "org/repo"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await svc.add_github_issue_comment(42, "SLA違反が発生しました", "INC-2026-001")
        assert result is True

    async def test_add_github_issue_comment_no_token(self):
        """GitHub token未設定時はFalseを返す"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        with patch("src.services.notification_service.settings") as mock_settings:
            mock_settings.github_token = ""
            mock_settings.github_repo = ""
            result = await svc.add_github_issue_comment(42, "comment", "INC-001")
        assert result is False

    async def test_create_incident_github_issue_api_error(self):
        """GitHub API エラー時はNoneを返す（例外を外部に出さない）"""
        from src.services.notification_service import NotificationService

        svc = NotificationService()
        with (
            patch("src.core.config.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.github_token = "ghp_token"
            mock_settings.github_repo = "org/repo"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_client_cls.return_value = mock_client

            result = await svc.create_incident_github_issue("INC-001", "Test", "P1")
        assert result is None


# ---------- webhook_service テスト ----------


class TestWebhookServiceGitHubSync:
    async def test_issue_closed_resolves_incident(self, db_session, incident_with_github):
        """GitHub Issueクローズ → Incidentをresolvedに更新"""
        from src.services import webhook_service

        payload = {
            "action": "closed",
            "issue": {"number": incident_with_github.github_issue_number, "title": "test", "body": "", "labels": []},
        }
        result = await webhook_service.process_issues_event(db_session, payload)
        assert result is not None
        assert result["action"] == "incident_resolved"

        await db_session.refresh(incident_with_github)
        assert incident_with_github.status == "Resolved"

    async def test_issue_closed_no_linked_incident(self, db_session):
        """対応するIncidentがない場合はissue_closedを返す"""
        from src.services import webhook_service

        payload = {
            "action": "closed",
            "issue": {"number": 9999, "title": "no match", "body": "", "labels": []},
        }
        result = await webhook_service.process_issues_event(db_session, payload)
        assert result["action"] == "issue_closed"

    async def test_issue_labeled_syncs_priority(self, db_session, incident_with_github):
        """GitHub Issueラベル変更 → Incidentの優先度を同期"""
        from src.services import webhook_service

        payload = {
            "action": "labeled",
            "issue": {
                "number": incident_with_github.github_issue_number,
                "title": "test",
                "body": "",
                "labels": [{"name": "P3"}, {"name": "bug"}],
            },
        }
        result = await webhook_service.process_issues_event(db_session, payload)
        assert result is not None
        assert result["action"] == "priority_synced"
        assert result["priority"] == "P3"

    async def test_issue_labeled_no_priority_label(self, db_session, incident_with_github):
        """優先度ラベルなしの場合はlabel_changedを返す"""
        from src.services import webhook_service

        payload = {
            "action": "labeled",
            "issue": {
                "number": incident_with_github.github_issue_number,
                "title": "test",
                "body": "",
                "labels": [{"name": "bug"}, {"name": "enhancement"}],
            },
        }
        result = await webhook_service.process_issues_event(db_session, payload)
        assert result["action"] == "label_changed"

    async def test_issue_assigned_returns_assignment_changed(self, db_session):
        """GitHub Issueアサイン変更 → assignment_changedを返す"""
        from src.services import webhook_service

        payload = {
            "action": "assigned",
            "issue": {"number": 100, "title": "test", "body": "", "labels": []},
        }
        result = await webhook_service.process_issues_event(db_session, payload)
        assert result["action"] == "assignment_changed"


# ---------- integrations API テスト ----------


class TestGitHubSyncEndpoints:
    async def test_github_sync_status_empty(self, client, auth_headers):
        """GitHub同期済みインシデントが0件の場合"""
        response = await client.get("/api/v1/integrations/github/sync", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "synced_incidents" in data
        assert isinstance(data["items"], list)

    async def test_github_sync_status_with_linked_incidents(
        self, client, auth_headers, db_session, incident_with_github
    ):
        """GitHub Issue連携済みインシデントが含まれる"""
        response = await client.get("/api/v1/integrations/github/sync", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["synced_incidents"] >= 1
        numbers = [item["github_issue_number"] for item in data["items"]]
        assert incident_with_github.github_issue_number in numbers

    async def test_sync_incident_to_github_not_found(self, client, auth_headers):
        """存在しないincident_idは404"""
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/integrations/github/sync/{fake_id}", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_sync_incident_creates_github_issue(
        self, client, auth_headers, db_session, incident
    ):
        """GitHubトークン未設定でも エンドポイントは 200 を返す（issue_number=None）"""
        with patch("src.api.v1.integrations.notification_service") as mock_svc:
            mock_svc.create_incident_github_issue = AsyncMock(return_value=None)
            response = await client.post(
                f"/api/v1/integrations/github/sync/{incident.incident_id}",
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "created"

    async def test_sync_incident_closes_resolved(
        self, client, auth_headers, db_session, incident_with_github
    ):
        """解決済みインシデントのGitHub Issueをクローズ"""
        incident_with_github.status = "Resolved"
        await db_session.commit()

        with patch("src.api.v1.integrations.notification_service") as mock_svc:
            mock_svc.close_incident_github_issue = AsyncMock(return_value=True)
            response = await client.post(
                f"/api/v1/integrations/github/sync/{incident_with_github.incident_id}",
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "closed"
        assert data["success"] is True
