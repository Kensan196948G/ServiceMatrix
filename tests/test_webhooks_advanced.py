"""GitHub Webhook強化版テスト - HMAC署名検証・Issue→インシデント・PR→変更要求自動連携"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.webhook_service import (
    CHANGE_REQUEST_TRIGGER_LABELS,
    INCIDENT_TRIGGER_LABELS,
    process_issue_event,
    process_pr_event,
    verify_webhook_signature,
)


def _make_signature(payload: bytes, secret: str) -> str:
    """テスト用HMAC-SHA256署名生成"""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# === HMAC署名検証テスト ===


class TestHMACSignatureVerification:
    """HMAC-SHA256署名検証のテストスイート"""

    def test_valid_signature(self):
        """正しい署名が検証を通過する"""
        payload = b'{"action": "opened"}'
        secret = "webhook-secret-key"  # noqa: S105
        sig = _make_signature(payload, secret)
        assert verify_webhook_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        """不正な署名が検証で拒否される"""
        payload = b'{"action": "opened"}'
        secret = "webhook-secret-key"  # noqa: S105
        wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        assert verify_webhook_signature(payload, wrong_sig, secret) is False

    def test_tampered_payload(self):
        """改ざんされたペイロードが検証で拒否される"""
        original = b'{"action": "opened"}'
        tampered = b'{"action": "closed"}'
        secret = "webhook-secret-key"  # noqa: S105
        sig = _make_signature(original, secret)
        # 元のペイロードの署名を改ざんされたペイロードに対して検証
        assert verify_webhook_signature(tampered, sig, secret) is False

    def test_wrong_secret(self):
        """異なる秘密鍵では検証が失敗する"""
        payload = b'{"action": "opened"}'
        sig = _make_signature(payload, "correct-secret")
        assert verify_webhook_signature(payload, sig, "wrong-secret") is False

    def test_empty_secret_still_computes(self):
        """空のsecretでも署名計算は動作する"""
        payload = b'{"test": true}'
        sig = _make_signature(payload, "")
        assert verify_webhook_signature(payload, sig, "") is True


# === Issue→インシデント自動連携テスト ===


class TestProcessIssueEvent:
    """process_issue_event のテストスイート"""

    @pytest.mark.anyio
    async def test_opened_with_incident_label_creates_incident(self):
        """opened + incidentラベルでインシデント自動作成"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 42,
                "title": "Critical service down",
                "body": "Service is not responding",
                "labels": [{"name": "incident"}, {"name": "P1"}],
            },
        }
        mock_incident = MagicMock()
        mock_incident.id = "inc-uuid-001"
        mock_incident.incident_number = "INC-2026-000001"
        mock_db = AsyncMock()

        with patch(
            "src.services.webhook_service.incident_service.create_incident",
            new=AsyncMock(return_value=mock_incident),
        ) as mock_create:
            result = await process_issue_event(payload, mock_db)

        assert result["action"] == "incident_created"
        assert result["incident_id"] == "inc-uuid-001"
        assert result["issue_number"] == 42
        # タイトルが [GH#<number>] 形式
        call_data = mock_create.call_args[0][1]
        assert call_data["title"] == "[GH#42] Critical service down"
        assert call_data["priority"] == "P1"

    @pytest.mark.anyio
    async def test_opened_with_urgent_label_creates_incident(self):
        """opened + urgentラベルでもインシデント自動作成"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 43,
                "title": "Urgent fix needed",
                "body": "Needs immediate attention",
                "labels": [{"name": "urgent"}],
            },
        }
        mock_incident = MagicMock()
        mock_incident.id = "inc-uuid-002"
        mock_incident.incident_number = "INC-2026-000002"
        mock_db = AsyncMock()

        with patch(
            "src.services.webhook_service.incident_service.create_incident",
            new=AsyncMock(return_value=mock_incident),
        ):
            result = await process_issue_event(payload, mock_db)

        assert result["action"] == "incident_created"
        assert result["incident_number"] == "INC-2026-000002"

    @pytest.mark.anyio
    async def test_opened_without_trigger_label_skips(self):
        """incidentもurgentラベルもない場合はスキップ"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 44,
                "title": "Feature request",
                "body": "Add dark mode",
                "labels": [{"name": "enhancement"}],
            },
        }
        mock_db = AsyncMock()
        result = await process_issue_event(payload, mock_db)
        assert result["status"] == "skipped"
        assert result["reason"] == "no_trigger_label"

    @pytest.mark.anyio
    async def test_opened_no_labels_skips(self):
        """ラベルなしIssueはスキップ"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 45,
                "title": "No labels",
                "body": "",
                "labels": [],
            },
        }
        mock_db = AsyncMock()
        result = await process_issue_event(payload, mock_db)
        assert result["status"] == "skipped"

    @pytest.mark.anyio
    async def test_closed_with_matching_incident_resolves(self):
        """closed + 対応インシデント存在 → Resolvedに更新"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 42,
                "title": "Critical service down",
                "body": "",
                "labels": [],
            },
        }
        mock_incident = MagicMock()
        mock_incident.status = "In_Progress"
        mock_incident.incident_number = "INC-2026-000001"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_incident
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await process_issue_event(payload, mock_db)
        assert result["action"] == "incident_resolved"
        assert result["incident_number"] == "INC-2026-000001"
        assert mock_incident.status == "Resolved"

    @pytest.mark.anyio
    async def test_closed_without_matching_incident(self):
        """closed + 対応インシデントなし → incident_found: False"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 999,
                "title": "Unknown",
                "body": "",
                "labels": [],
            },
        }
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await process_issue_event(payload, mock_db)
        assert result["action"] == "issue_closed"
        assert result["incident_found"] is False

    @pytest.mark.anyio
    async def test_closed_already_resolved_incident_no_update(self):
        """closed + インシデントが既にResolved → 更新しない"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 42,
                "title": "Already resolved",
                "body": "",
                "labels": [],
            },
        }
        mock_incident = MagicMock()
        mock_incident.status = "Resolved"
        mock_incident.incident_number = "INC-2026-000001"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_incident
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await process_issue_event(payload, mock_db)
        assert result["action"] == "issue_closed"
        assert result["incident_found"] is False

    @pytest.mark.anyio
    async def test_other_action_ignored(self):
        """opened/closed以外のアクションは無視"""
        payload = {
            "action": "edited",
            "issue": {"number": 50, "title": "Edit", "body": "", "labels": []},
        }
        mock_db = AsyncMock()
        result = await process_issue_event(payload, mock_db)
        assert result["status"] == "ignored"


# === PR→変更要求自動連携テスト ===


class TestProcessPREvent:
    """process_pr_event のテストスイート"""

    @pytest.mark.anyio
    async def test_opened_with_change_request_label_creates_change(self):
        """opened + change-requestラベルで変更要求自動作成"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 10,
                "title": "Update API endpoint",
                "body": "Refactor the API handler",
                "html_url": "https://github.com/org/repo/pull/10",
                "labels": [{"name": "change-request"}],
            },
        }
        mock_change = MagicMock()
        mock_change.change_id = "chg-uuid-001"
        mock_change.change_number = "CHG-2026-000001"
        mock_db = AsyncMock()

        with patch(
            "src.services.webhook_service.change_service.create_change",
            new=AsyncMock(return_value=mock_change),
        ) as mock_create:
            result = await process_pr_event(payload, mock_db)

        assert result["action"] == "change_created"
        assert result["change_id"] == "chg-uuid-001"
        assert result["pr_number"] == 10
        # タイトルが [PR#<number>] 形式
        call_data = mock_create.call_args[0][1]
        assert call_data["title"] == "[PR#10] Update API endpoint"
        assert call_data["change_type"] == "Normal"

    @pytest.mark.anyio
    async def test_opened_without_change_request_label_skips(self):
        """change-requestラベルなしの場合はスキップ"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 11,
                "title": "Small fix",
                "body": "",
                "html_url": "https://github.com/org/repo/pull/11",
                "labels": [{"name": "bugfix"}],
            },
        }
        mock_db = AsyncMock()
        result = await process_pr_event(payload, mock_db)
        assert result["status"] == "skipped"
        assert result["reason"] == "no_trigger_label"

    @pytest.mark.anyio
    async def test_opened_no_labels_skips(self):
        """ラベルなしPRはスキップ"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 12,
                "title": "No labels PR",
                "body": "",
                "html_url": "https://github.com/org/repo/pull/12",
                "labels": [],
            },
        }
        mock_db = AsyncMock()
        result = await process_pr_event(payload, mock_db)
        assert result["status"] == "skipped"

    @pytest.mark.anyio
    async def test_other_action_ignored(self):
        """opened以外のアクションは無視"""
        payload = {
            "action": "closed",
            "pull_request": {
                "number": 13,
                "title": "Closed PR",
                "body": "",
                "html_url": "https://github.com/org/repo/pull/13",
                "labels": [{"name": "change-request"}],
            },
        }
        mock_db = AsyncMock()
        result = await process_pr_event(payload, mock_db)
        assert result["status"] == "ignored"


# === 定数・設定テスト ===


class TestWebhookConstants:
    """Webhook設定定数のテスト"""

    def test_incident_trigger_labels(self):
        """インシデントトリガーラベルが正しい"""
        assert "incident" in INCIDENT_TRIGGER_LABELS
        assert "urgent" in INCIDENT_TRIGGER_LABELS

    def test_change_request_trigger_labels(self):
        """変更要求トリガーラベルが正しい"""
        assert "change-request" in CHANGE_REQUEST_TRIGGER_LABELS


# === エンドポイント直接呼び出しテスト ===


class TestWebhookAdvancedEndpoint:
    """強化版Webhookエンドポイントの直接呼び出しテスト"""

    @pytest.mark.anyio
    async def test_advanced_endpoint_ping(self, client):
        """/github/advanced pingイベント → pong"""
        payload = {"hook_id": 100, "zen": "Advanced webhook ping"}
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=json.dumps(payload).encode(),
            headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pong"
        assert data["hook_id"] == 100

    @pytest.mark.anyio
    async def test_advanced_endpoint_hmac_valid(self, client, monkeypatch):
        """正しいHMAC署名 → 200"""
        secret = "advanced-webhook-secret"  # noqa: S105
        monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", secret)
        payload = json.dumps({"hook_id": 200, "zen": "Signed request"}).encode()
        sig = _make_signature(payload, secret)
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=payload,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pong"

    @pytest.mark.anyio
    async def test_advanced_endpoint_hmac_invalid(self, client, monkeypatch):
        """不正なHMAC署名 → 403"""
        monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", "real-secret")
        payload = json.dumps({"action": "opened"}).encode()
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=payload,
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": "sha256=invalid",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_advanced_endpoint_hmac_missing_when_secret_set(self, client, monkeypatch):
        """secret設定済みだが署名ヘッダーなし → 403"""
        monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", "some-secret")
        payload = json.dumps({"hook_id": 3}).encode()
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=payload,
            headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_advanced_endpoint_invalid_json(self, client):
        """不正JSONペイロード → 400"""
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=b"not-json{{{",
            headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_advanced_endpoint_unknown_event(self, client):
        """未対応イベント → ignored"""
        payload = json.dumps({"action": "completed"}).encode()
        resp = await client.post(
            "/api/v1/webhooks/github/advanced",
            content=payload,
            headers={"X-GitHub-Event": "deployment", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.anyio
    async def test_advanced_endpoint_issue_with_incident_label(self, client):
        """Issue(incidentラベル付き) → インシデント自動作成"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 500,
                "title": "Production down",
                "body": "All systems are failing",
                "labels": [{"name": "incident"}, {"name": "P1"}],
            },
        }
        mock_incident = MagicMock()
        mock_incident.id = "adv-inc-001"
        mock_incident.incident_number = "INC-2026-000500"

        with patch(
            "src.services.webhook_service.incident_service.create_incident",
            new=AsyncMock(return_value=mock_incident),
        ):
            resp = await client.post(
                "/api/v1/webhooks/github/advanced",
                content=json.dumps(payload).encode(),
                headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "incident_created"
        assert data["incident_id"] == "adv-inc-001"

    @pytest.mark.anyio
    async def test_advanced_endpoint_pr_with_change_request_label(self, client):
        """PR(change-requestラベル付き) → 変更要求自動作成"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 600,
                "title": "Infrastructure change",
                "body": "Update infrastructure",
                "html_url": "https://github.com/org/repo/pull/600",
                "labels": [{"name": "change-request"}],
            },
        }
        mock_change = MagicMock()
        mock_change.change_id = "adv-chg-001"
        mock_change.change_number = "CHG-2026-000600"

        with patch(
            "src.services.webhook_service.change_service.create_change",
            new=AsyncMock(return_value=mock_change),
        ):
            resp = await client.post(
                "/api/v1/webhooks/github/advanced",
                content=json.dumps(payload).encode(),
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "change_created"
        assert data["change_number"] == "CHG-2026-000600"
