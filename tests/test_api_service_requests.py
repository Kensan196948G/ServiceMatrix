"""サービスリクエスト API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_sr_seq():
    """func.nextval('service_request_seq') 及び audit_log_seq の代替モック"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"SR-2024-{_counter[0]:06d}"

    with patch("src.services.service_request_service._get_next_sr_number", _get_next), \
         patch(
             "src.services.service_request_service.audit_service.record_audit_log",
             new=AsyncMock(return_value=None),
         ):
        yield


# ─── 作成テスト ──────────────────────────────────────────────────────────────

async def test_create_sr_success(client, auth_headers):
    """POST /service-requests → 201, request_number が SR- プレフィックスを持つ"""
    resp = await client.post(
        "/api/v1/service-requests",
        json={"title": "ノートPC貸し出し申請", "request_type": "Hardware"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["request_number"].startswith("SR-")
    assert data["title"] == "ノートPC貸し出し申請"
    assert data["status"] == "New"


# ─── 一覧・詳細取得テスト ────────────────────────────────────────────────────

async def test_list_srs_empty(client, auth_headers):
    """GET /service-requests → 200, レスポンス構造を確認"""
    resp = await client.get("/api/v1/service-requests", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


async def test_get_sr_not_found(client, auth_headers):
    """存在しない UUID → 404"""
    resp = await client.get(f"/api/v1/service-requests/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── ステータス遷移テスト ────────────────────────────────────────────────────

async def test_sr_status_transition(client, auth_headers):
    """New → Pending_Approval ステータス遷移"""
    create_resp = await client.post(
        "/api/v1/service-requests",
        json={"title": "遷移テスト用SR"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    sr_id = create_resp.json()["request_id"]

    trans_resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": "Pending_Approval"},
        headers=auth_headers,
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "Pending_Approval"


async def test_sr_fulfill_sets_fulfilled_at(client, auth_headers):
    """In_Progress → Fulfilled 時に fulfilled_at が設定される"""
    create_resp = await client.post(
        "/api/v1/service-requests",
        json={"title": "完了テスト用SR"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    sr_id = create_resp.json()["request_id"]

    # New → In_Progress
    r1 = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": "In_Progress"},
        headers=auth_headers,
    )
    assert r1.status_code == 200

    # In_Progress → Fulfilled
    r2 = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": "Fulfilled"},
        headers=auth_headers,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["status"] == "Fulfilled"
    assert data["fulfilled_at"] is not None


# ─── 認証テスト ──────────────────────────────────────────────────────────────

async def test_unauthorized_sr(client):
    """認証ヘッダーなし → 401"""
    resp = await client.get("/api/v1/service-requests")
    assert resp.status_code == 401
