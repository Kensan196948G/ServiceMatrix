"""ServiceRequest 承認フロー完全テスト + 変更カレンダーAPIテスト"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ─── モックフィクスチャ ────────────────────────────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def mock_sr_deps():
    """SR番号採番・監査ログをモック"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"SR-2024-{_counter[0]:06d}"

    with (
        patch("src.services.service_request_service._get_next_sr_number", _get_next),
        patch(
            "src.services.service_request_service.audit_service.record_audit_log",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield


@pytest_asyncio.fixture(autouse=True)
async def mock_change_seq():
    """変更番号採番をモック"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"CHG-2024-{_counter[0]:06d}"

    with patch("src.services.change_service._get_next_change_number", _get_next):
        yield


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


async def _create_sr(client, auth_headers, title="テストSR") -> str:
    resp = await client.post(
        "/api/v1/service-requests",
        json={"title": title},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["request_id"]


async def _transition(client, auth_headers, sr_id: str, target: str) -> dict:
    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": target},
        headers=auth_headers,
    )
    return resp


# ─── 承認フロー遷移テスト ──────────────────────────────────────────────────────


async def test_submit_request_new_to_pending(client, auth_headers):
    """POST /submit: New → Pending_Approval"""
    sr_id = await _create_sr(client, auth_headers, "申請提出テスト")
    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/submit",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Pending_Approval"


async def test_submit_request_invalid_status(client, auth_headers):
    """既にPending_ApprovalのSRをsubmit → 422"""
    sr_id = await _create_sr(client, auth_headers)
    # New → Pending_Approval
    r1 = await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    assert r1.status_code == 200
    # Pending_Approval → Pending_Approval (invalid)
    r2 = await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    assert r2.status_code == 422


async def test_approve_request_success(client, auth_headers):
    """POST /approve: Pending_Approval → Approved"""
    sr_id = await _create_sr(client, auth_headers, "承認テスト")
    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "approver@test.com", "comment": "問題なし"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Approved"


async def test_approve_request_invalid_status(client, auth_headers):
    """New状態でapprove → 422（Pending_Approvalでなければ不可）"""
    sr_id = await _create_sr(client, auth_headers)
    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "approver@test.com", "comment": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_reject_request_success(client, auth_headers):
    """POST /reject: Pending_Approval → Rejected"""
    sr_id = await _create_sr(client, auth_headers, "却下テスト")
    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/reject",
        json={"actor": "approver@test.com", "comment": "予算超過"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Rejected"


async def test_reject_request_invalid_status(client, auth_headers):
    """New状態でreject → 422"""
    sr_id = await _create_sr(client, auth_headers)
    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/reject",
        json={"actor": "approver@test.com", "comment": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_start_fulfillment_success(client, auth_headers):
    """POST /start: Approved → In_Fulfillment"""
    sr_id = await _create_sr(client, auth_headers, "実行開始テスト")
    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "mgr", "comment": ""},
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/start",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "In_Fulfillment"


async def test_start_fulfillment_invalid_status(client, auth_headers):
    """New状態でstart → 422"""
    sr_id = await _create_sr(client, auth_headers)
    resp = await client.post(f"/api/v1/service-requests/{sr_id}/start", headers=auth_headers)
    assert resp.status_code == 422


async def test_complete_request_fulfilled(client, auth_headers):
    """POST /complete success=true: In_Fulfillment → Fulfilled"""
    sr_id = await _create_sr(client, auth_headers, "完了テスト")
    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "mgr", "comment": ""},
        headers=auth_headers,
    )
    await client.post(f"/api/v1/service-requests/{sr_id}/start", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/complete",
        json={"success": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Fulfilled"
    assert data["fulfilled_at"] is not None


async def test_complete_request_failed(client, auth_headers):
    """POST /complete success=false: In_Fulfillment → Failed"""
    sr_id = await _create_sr(client, auth_headers, "失敗テスト")
    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "mgr", "comment": ""},
        headers=auth_headers,
    )
    await client.post(f"/api/v1/service-requests/{sr_id}/start", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/complete",
        json={"success": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Failed"


async def test_complete_request_invalid_status(client, auth_headers):
    """New状態でcomplete → 422"""
    sr_id = await _create_sr(client, auth_headers)
    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/complete",
        json={"success": True},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_full_approval_flow(client, auth_headers):
    """完全承認フロー: New→Pending_Approval→Approved→In_Fulfillment→Fulfilled"""
    sr_id = await _create_sr(client, auth_headers, "フルフローテスト")

    r1 = await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    assert r1.json()["status"] == "Pending_Approval"

    r2 = await client.post(
        f"/api/v1/service-requests/{sr_id}/approve",
        json={"actor": "mgr", "comment": "OK"},
        headers=auth_headers,
    )
    assert r2.json()["status"] == "Approved"

    r3 = await client.post(f"/api/v1/service-requests/{sr_id}/start", headers=auth_headers)
    assert r3.json()["status"] == "In_Fulfillment"

    r4 = await client.post(
        f"/api/v1/service-requests/{sr_id}/complete",
        json={"success": True},
        headers=auth_headers,
    )
    assert r4.json()["status"] == "Fulfilled"
    assert r4.json()["fulfilled_at"] is not None


async def test_rejection_flow(client, auth_headers):
    """却下フロー: New→Pending_Approval→Rejected"""
    sr_id = await _create_sr(client, auth_headers, "却下フロー")

    await client.post(f"/api/v1/service-requests/{sr_id}/submit", headers=auth_headers)
    r = await client.post(
        f"/api/v1/service-requests/{sr_id}/reject",
        json={"actor": "mgr", "comment": "要件不足"},
        headers=auth_headers,
    )
    assert r.json()["status"] == "Rejected"


async def test_submit_not_found(client, auth_headers):
    """存在しないSRをsubmit → 422"""
    resp = await client.post(
        f"/api/v1/service-requests/{uuid.uuid4()}/submit",
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ─── 変更カレンダーAPIテスト ───────────────────────────────────────────────────


async def test_change_calendar_empty(client, auth_headers):
    """変更カレンダー: 期間内データなし → events=[]"""
    resp = await client.get(
        "/api/v1/changes/calendar?start_date=2020-01-01&end_date=2020-01-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["start_date"] == "2020-01-01"
    assert data["end_date"] == "2020-01-31"
    assert data["events"] == []
    assert data["total"] == 0


async def test_change_calendar_with_data(client, auth_headers):
    """変更カレンダー: スケジュール済み変更が含まれる"""
    scheduled = datetime(2030, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    resp = await client.post(
        "/api/v1/changes",
        json={
            "title": "カレンダーテスト変更",
            "change_type": "Normal",
            "scheduled_start_at": scheduled.isoformat(),
            "scheduled_end_at": (scheduled + timedelta(hours=2)).isoformat(),
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    cal = await client.get(
        "/api/v1/changes/calendar?start_date=2030-06-01&end_date=2030-06-30",
        headers=auth_headers,
    )
    assert cal.status_code == 200
    data = cal.json()
    assert data["total"] >= 1
    assert len(data["events"]) >= 1
    assert data["events"][0]["date"] == "2030-06-15"
    assert any(c["title"] == "カレンダーテスト変更" for c in data["events"][0]["changes"])


async def test_change_calendar_requires_auth(client):
    """カレンダーAPI: 未認証 → 401"""
    resp = await client.get(
        "/api/v1/changes/calendar?start_date=2030-01-01&end_date=2030-01-31"
    )
    assert resp.status_code == 401


async def test_change_calendar_missing_params(client, auth_headers):
    """カレンダーAPI: パラメータなし → 422"""
    resp = await client.get("/api/v1/changes/calendar", headers=auth_headers)
    assert resp.status_code == 422
