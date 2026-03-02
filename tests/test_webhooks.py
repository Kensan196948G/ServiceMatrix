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
    mock_incident.id = "abc-123"
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
    mock_incident.id = "def-456"
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
    """issues.closedでissue_closedレスポンス"""
    payload = {
        "action": "closed",
        "issue": {"number": 55, "title": "Old issue", "body": "", "labels": []},
    }
    mock_db = AsyncMock()
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
