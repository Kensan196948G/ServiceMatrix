"""integrations.py / compliance.py 追加カバレッジテスト

対象:
  src/api/v1/integrations.py (67%) - GitHub sync / webhook エンドポイント
    lines 163-165: github_sync_status - DB query実行
    lines 187-210: sync_incident_to_github - 404/closed/created/no_change
    lines 219-240: webhook_jira - issue_created/issue_updated/skipped/invalid
    lines 253-271: webhook_servicenow - incident_created/skipped/invalid
  src/api/v1/compliance.py (91%) - SLA FAIL分岐・get_compliance_score
    lines 189-190: SLA監視フィールド未実装 → FAIL
    lines 287-295: get_compliance_score エンドポイント
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_count_execute(counts: list[int]):
    """db.execute が count を返すモック"""
    results = []
    for c in counts:
        r = MagicMock()
        r.scalar_one.return_value = c
        results.append(r)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    return db


def _make_incident_mock(
    incident_id=None,
    status="New",
    github_issue_number=None,
):
    inc = MagicMock()
    inc.incident_id = incident_id or uuid.uuid4()
    inc.incident_number = "INC-2026-000001"
    inc.title = "テストインシデント"
    inc.description = "テスト説明"
    inc.priority = "P3"
    inc.status = status
    inc.github_issue_number = github_issue_number
    return inc


def _make_request_mock(json_body: dict | None, raise_on_json: bool = False):
    """FastAPI Request のモック（json() を await できるよう設定）"""
    req = AsyncMock()
    if raise_on_json:
        req.json = AsyncMock(side_effect=Exception("invalid json"))
    else:
        req.json = AsyncMock(return_value=json_body)
    return req


# ─── integrations.py: github_sync_status (lines 163-165) ─────────────────────


async def test_github_sync_status_returns_synced_incidents():
    """github_sync_status: DB から GitHub 連携インシデントを取得して返す"""
    from src.api.v1.integrations import github_sync_status

    inc = _make_incident_mock(github_issue_number=42)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    current_user = MagicMock()

    result = await github_sync_status(db=db, current_user=current_user)

    assert result["synced_incidents"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["github_issue_number"] == 42
    db.execute.assert_called_once()


async def test_github_sync_status_empty_returns_zero():
    """github_sync_status: 連携インシデントなし → synced_incidents=0"""
    from src.api.v1.integrations import github_sync_status

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    result = await github_sync_status(db=db, current_user=MagicMock())

    assert result["synced_incidents"] == 0
    assert result["items"] == []


# ─── integrations.py: sync_incident_to_github (lines 187-210) ────────────────


async def test_sync_incident_to_github_not_found_raises_404():
    """sync_incident_to_github: インシデント不存在 → 404"""
    from fastapi import HTTPException

    from src.api.v1.integrations import sync_incident_to_github

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await sync_incident_to_github(
            incident_id=uuid.uuid4(),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_sync_incident_to_github_resolved_with_issue_closes():
    """sync_incident_to_github: Resolved + github_issue_number あり → close アクション"""
    from src.api.v1.integrations import sync_incident_to_github

    inc = _make_incident_mock(status="Resolved", github_issue_number=99)
    db = AsyncMock()
    db.get = AsyncMock(return_value=inc)

    with patch(
        "src.api.v1.integrations.notification_service.close_incident_github_issue",
        new=AsyncMock(return_value=True),
    ) as mock_close:
        result = await sync_incident_to_github(
            incident_id=inc.incident_id,
            db=db,
            current_user=MagicMock(),
        )

    assert result["action"] == "closed"
    assert result["github_issue_number"] == 99
    assert result["success"] is True
    mock_close.assert_called_once()


async def test_sync_incident_to_github_no_issue_creates():
    """sync_incident_to_github: github_issue_number なし → create アクション"""
    from src.api.v1.integrations import sync_incident_to_github

    inc = _make_incident_mock(status="New", github_issue_number=None)
    db = AsyncMock()
    db.get = AsyncMock(return_value=inc)

    with patch(
        "src.api.v1.integrations.notification_service.create_incident_github_issue",
        new=AsyncMock(return_value=101),
    ) as mock_create:
        result = await sync_incident_to_github(
            incident_id=inc.incident_id,
            db=db,
            current_user=MagicMock(),
        )

    assert result["action"] == "created"
    assert result["github_issue_number"] == 101
    mock_create.assert_called_once()
    db.commit.assert_called_once()


async def test_sync_incident_to_github_has_issue_no_change():
    """sync_incident_to_github: github_issue_number あり・未解決 → no_change"""
    from src.api.v1.integrations import sync_incident_to_github

    inc = _make_incident_mock(status="In_Progress", github_issue_number=55)
    db = AsyncMock()
    db.get = AsyncMock(return_value=inc)

    result = await sync_incident_to_github(
        incident_id=inc.incident_id,
        db=db,
        current_user=MagicMock(),
    )

    assert result["action"] == "no_change"
    assert result["github_issue_number"] == 55


# ─── integrations.py: webhook_jira (lines 219-240) ──────────────────────────


async def test_webhook_jira_issue_created_creates_incident():
    """webhook_jira: jira:issue_created → Incident作成・incident_id返却"""
    from src.api.v1.integrations import webhook_jira

    body = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Jira Issue タイトル",
                "description": "詳細説明",
            },
        },
    }
    req = _make_request_mock(body)
    db = AsyncMock()
    db.add = MagicMock()

    mock_incident = MagicMock()
    mock_incident.incident_id = uuid.uuid4()

    with patch("src.api.v1.integrations.Incident", return_value=mock_incident):
        result = await webhook_jira(request=req, db=db)

    assert result["received"] is True
    db.add.assert_called_once()
    db.commit.assert_called_once()


async def test_webhook_jira_issue_updated_creates_incident():
    """webhook_jira: jira:issue_updated → Incident作成"""
    from src.api.v1.integrations import webhook_jira

    body = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "PROJ-456",
            "fields": {"summary": "Updated Issue", "description": None},
        },
    }
    req = _make_request_mock(body)
    db = AsyncMock()
    db.add = MagicMock()

    mock_incident = MagicMock()
    mock_incident.incident_id = uuid.uuid4()

    with patch("src.api.v1.integrations.Incident", return_value=mock_incident):
        result = await webhook_jira(request=req, db=db)

    assert result["received"] is True
    db.add.assert_called_once()


async def test_webhook_jira_unknown_event_skips():
    """webhook_jira: 不明イベント → received=True, skipped=True"""
    from src.api.v1.integrations import webhook_jira

    body = {"webhookEvent": "jira:issue_deleted"}
    req = _make_request_mock(body)
    db = AsyncMock()

    result = await webhook_jira(request=req, db=db)

    assert result["received"] is True
    assert result.get("skipped") is True
    db.add.assert_not_called()


async def test_webhook_jira_invalid_json_raises_400():
    """webhook_jira: 不正JSON → 400"""
    from fastapi import HTTPException

    from src.api.v1.integrations import webhook_jira

    req = _make_request_mock(None, raise_on_json=True)
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await webhook_jira(request=req, db=db)

    assert exc_info.value.status_code == 400


# ─── integrations.py: webhook_servicenow (lines 253-271) ────────────────────


async def test_webhook_servicenow_incident_created_creates_incident():
    """webhook_servicenow: incident_created → Incident作成"""
    from src.api.v1.integrations import webhook_servicenow

    body = {
        "event": "incident_created",
        "record": {
            "sys_id": "abc12345",
            "short_description": "ServiceNow障害",
            "description": "詳細",
        },
    }
    req = _make_request_mock(body)
    db = AsyncMock()
    db.add = MagicMock()

    mock_incident = MagicMock()
    mock_incident.incident_id = uuid.uuid4()

    with patch("src.api.v1.integrations.Incident", return_value=mock_incident):
        result = await webhook_servicenow(request=req, db=db)

    assert result["received"] is True
    db.add.assert_called_once()
    db.commit.assert_called_once()


async def test_webhook_servicenow_unknown_event_skips():
    """webhook_servicenow: 不明イベント → received=True, skipped=True"""
    from src.api.v1.integrations import webhook_servicenow

    body = {"event": "incident_updated"}
    req = _make_request_mock(body)
    db = AsyncMock()

    result = await webhook_servicenow(request=req, db=db)

    assert result["received"] is True
    assert result.get("skipped") is True
    db.add.assert_not_called()


async def test_webhook_servicenow_invalid_json_raises_400():
    """webhook_servicenow: 不正JSON → 400"""
    from fastapi import HTTPException

    from src.api.v1.integrations import webhook_servicenow

    req = _make_request_mock(None, raise_on_json=True)
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await webhook_servicenow(request=req, db=db)

    assert exc_info.value.status_code == 400


# ─── compliance.py: get_compliance_score (lines 287-295) ─────────────────────


async def test_get_compliance_score_returns_scores():
    """get_compliance_score: overall_score / soc2_score / iso27001_score を返す"""
    from src.api.v1.compliance import get_compliance_score

    # SOC2 (4 クエリ) + ISO27001 (4 クエリ) = 8 クエリ
    db = _make_count_execute([5, 10, 3, 7, 5, 10, 3, 7])
    current_user = MagicMock()

    result = await get_compliance_score(db=db, current_user=current_user)

    assert "overall_score" in result
    assert "soc2_score" in result
    assert "iso27001_score" in result
    assert "summary" in result
    assert isinstance(result["overall_score"], (int, float))


async def test_get_compliance_score_all_zero_lowers_score():
    """get_compliance_score: 全カウント0 → スコアが100未満"""
    from src.api.v1.compliance import get_compliance_score

    db = _make_count_execute([0, 0, 0, 0, 0, 0, 0, 0])
    current_user = MagicMock()

    result = await get_compliance_score(db=db, current_user=current_user)

    assert result["overall_score"] < 100
