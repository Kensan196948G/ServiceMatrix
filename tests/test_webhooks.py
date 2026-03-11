"""GitHub Webhook テスト"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.webhook_service import (
    GITHUB_ISSUE_PRIORITY_MAP,
    process_issues_event,
    process_ping_event,
    process_pull_request_event,
    verify_webhook_signature,
)


def _make_signature(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# --- verify_webhook_signature ---

def test_webhook_signature_valid():
    """正しい署名が検証OK"""
    payload = b'{"action": "opened"}'
    secret = "mysecret"
    sig = _make_signature(payload, secret)
    assert verify_webhook_signature(payload, sig, secret) is True


def test_webhook_signature_invalid():
    """間違った署名が検証NG"""
    payload = b'{"action": "opened"}'
    secret = "mysecret"
    wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
    assert verify_webhook_signature(payload, wrong_sig, secret) is False


def test_webhook_signature_empty_secret():
    """secretが空でも関数は動作するが、通常スキップされる"""
    payload = b'{"action": "opened"}'
    sig = _make_signature(payload, "")
    # empty secret: signature still computable
    assert verify_webhook_signature(payload, sig, "") is True


# --- process_ping_event ---

@pytest.mark.anyio
async def test_process_ping_event():
    """pingイベントがpongレスポンス"""
    payload = {"hook_id": 42, "zen": "Keep it logically awesome."}
    result = await process_ping_event(payload)
    assert result["status"] == "pong"
    assert result["hook_id"] == 42
    assert result["zen"] == "Keep it logically awesome."


# --- process_issues_event ---

@pytest.mark.anyio
async def test_process_issues_opened():
    """issues.openedでIncident作成フロー"""
    payload = {
        "action": "opened",
        "issue": {
            "number": 101,
            "title": "Something broke",
            "body": "It is broken",
            "labels": [{"name": "P1"}],
        },
    }

    mock_incident = MagicMock()
    mock_incident.incident_id = "abc-123"
    mock_incident.incident_number = "INC-0001"

    mock_db = AsyncMock()

    with patch("src.services.webhook_service.incident_service.create_incident", new=AsyncMock(return_value=mock_incident)):
        result = await process_issues_event(mock_db, payload)

    assert result["incident_id"] == "abc-123"
    assert result["incident_number"] == "INC-0001"


@pytest.mark.anyio
async def test_process_issues_opened_priority_default():
    """ラベルなしの場合はP3がデフォルト優先度"""
    payload = {
        "action": "opened",
        "issue": {
            "number": 102,
            "title": "Minor issue",
            "body": None,
            "labels": [],
        },
    }

    mock_incident = MagicMock()
    mock_incident.incident_id = "def-456"
    mock_incident.incident_number = "INC-0002"
    mock_db = AsyncMock()

    captured = {}

    async def fake_create(db, data):
        captured["priority"] = data["priority"]
        captured["title"] = data["title"]
        return mock_incident

    with patch("src.services.webhook_service.incident_service.create_incident", new=fake_create):
        result = await process_issues_event(mock_db, payload)

    assert captured["priority"] == "P3"
    assert "[GitHub Issue #102]" in captured["title"]


@pytest.mark.anyio
async def test_process_issues_closed():
    """issues.closedで対応Incidentなしの場合issue_closedレスポンス"""
    payload = {
        "action": "closed",
        "issue": {"number": 55, "title": "Old issue", "body": "", "labels": []},
    }
    from unittest.mock import MagicMock
    mock_db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = execute_result
    result = await process_issues_event(mock_db, payload)
    assert result == {"action": "issue_closed", "issue_number": 55}


# --- process_pull_request_event ---

@pytest.mark.anyio
async def test_process_pr_opened():
    """pull_request.openedでpr_openedレスポンス"""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 7,
            "title": "Add feature X",
            "html_url": "https://github.com/org/repo/pull/7",
            "merged": False,
        },
    }
    mock_db = AsyncMock()
    result = await process_pull_request_event(mock_db, payload)
    assert result["action"] == "pr_opened"
    assert result["pr_number"] == 7
    assert result["title"] == "Add feature X"
    assert result["url"] == "https://github.com/org/repo/pull/7"


@pytest.mark.anyio
async def test_process_pr_merged():
    """pull_request.closed+mergedでpr_mergedレスポンス"""
    payload = {
        "action": "closed",
        "pull_request": {
            "number": 8,
            "title": "Merge feature Y",
            "html_url": "https://github.com/org/repo/pull/8",
            "merged": True,
        },
    }
    mock_db = AsyncMock()
    result = await process_pull_request_event(mock_db, payload)
    assert result == {"action": "pr_merged", "pr_number": 8, "title": "Merge feature Y"}


@pytest.mark.anyio
async def test_process_pr_closed_not_merged():
    """mergedでないcloseはNoneを返す"""
    payload = {
        "action": "closed",
        "pull_request": {
            "number": 9,
            "title": "Closed without merge",
            "html_url": "https://github.com/org/repo/pull/9",
            "merged": False,
        },
    }
    mock_db = AsyncMock()
    result = await process_pull_request_event(mock_db, payload)
    assert result is None


# --- process_issues_event: other action ---

@pytest.mark.anyio
async def test_process_issues_other_action():
    """openedでもclosedでもないアクションはNoneを返す"""
    payload = {
        "action": "edited",
        "issue": {"number": 200, "title": "Edited", "body": "", "labels": []},
    }
    mock_db = AsyncMock()
    result = await process_issues_event(mock_db, payload)
    assert result is None


@pytest.mark.anyio
async def test_process_pr_other_action():
    """openedでもclosed+mergedでもないPRアクションはNoneを返す"""
    payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 10,
            "title": "Sync",
            "html_url": "https://github.com/org/repo/pull/10",
            "merged": False,
        },
    }
    mock_db = AsyncMock()
    result = await process_pull_request_event(mock_db, payload)
    assert result is None


# === Webhook API エンドポイントテスト =============================================

@pytest.mark.anyio
async def test_webhook_api_ping_event(client):
    """POST /webhooks/github (ping) → 200, pongレスポンス"""
    payload = {"hook_id": 99, "zen": "Keep it logically awesome."}
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pong"
    assert data["hook_id"] == 99


@pytest.mark.anyio
async def test_webhook_api_issues_opened(client):
    """POST /webhooks/github (issues.opened) → 200, incident作成"""
    payload = {
        "action": "opened",
        "issue": {
            "number": 300,
            "title": "API Webhook Test Issue",
            "body": "Body text",
            "labels": [{"name": "P2"}],
        },
    }
    mock_incident = MagicMock()
    mock_incident.incident_id = "webhook-inc-id"
    mock_incident.incident_number = "INC-W001"

    with patch(
        "src.services.webhook_service.incident_service.create_incident",
        new=AsyncMock(return_value=mock_incident),
    ):
        resp = await client.post(
            "/api/v1/webhooks/github",
            content=json.dumps(payload).encode(),
            headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == "webhook-inc-id"


@pytest.mark.anyio
async def test_webhook_api_pr_opened(client):
    """POST /webhooks/github (pull_request.opened) → 200"""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 50,
            "title": "New Feature PR",
            "html_url": "https://github.com/org/repo/pull/50",
            "merged": False,
        },
    }
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "pr_opened"
    assert data["pr_number"] == 50


@pytest.mark.anyio
async def test_webhook_api_unknown_event(client):
    """未対応イベント → ignored"""
    payload = {"action": "completed"}
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "check_run", "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ignored"
    assert data["event"] == "check_run"


@pytest.mark.anyio
async def test_webhook_api_invalid_json(client):
    """不正JSONペイロード → 400"""
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=b"not-a-json",
        headers={"X-GitHub-Event": "push", "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_webhook_api_invalid_signature(client, monkeypatch):
    """HMAC署名検証失敗 → 403"""
    monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", "real-secret")
    payload = json.dumps({"action": "opened"}).encode()
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=invalid",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_webhook_api_valid_signature(client, monkeypatch):
    """正しいHMAC署名 → 200"""
    secret = "test-webhook-secret"
    monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", secret)
    payload = json.dumps({"hook_id": 1, "zen": "Signed"}).encode()
    sig = _make_signature(payload, secret)
    resp = await client.post(
        "/api/v1/webhooks/github",
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
async def test_webhook_api_missing_signature_when_secret_set(client, monkeypatch):
    """secret設定済みだが署名ヘッダーなし → 403"""
    monkeypatch.setattr("src.api.v1.webhooks.settings.github_webhook_secret", "some-secret")
    payload = json.dumps({"hook_id": 2}).encode()
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_webhook_api_issues_closed(client):
    """POST /webhooks/github (issues.closed) → 200"""
    payload = {
        "action": "closed",
        "issue": {"number": 301, "title": "Closed Issue", "body": "", "labels": []},
    }
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "issue_closed"


@pytest.mark.anyio
async def test_webhook_api_pr_closed_not_merged(client):
    """PRクローズ（マージなし） → no_action"""
    payload = {
        "action": "closed",
        "pull_request": {
            "number": 51,
            "title": "Closed PR",
            "html_url": "https://github.com/org/repo/pull/51",
            "merged": False,
        },
    }
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_action"
