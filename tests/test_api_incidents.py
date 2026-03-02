"""インシデント API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_incident_seq():
    """func.nextval('incident_seq') の代替（SQLite非対応のためモック）"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"INC-2024-{_counter[0]:06d}"

    with patch("src.services.incident_service._get_next_incident_number", _get_next):
        yield


# ─── 作成テスト ──────────────────────────────────────────────────────────────

async def test_create_incident_success(client, auth_headers):
    """POST /incidents → 201, incident_number が INC- プレフィックスを持つ"""
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "本番DBサーバー障害", "priority": "P1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["incident_number"].startswith("INC-")
    assert data["title"] == "本番DBサーバー障害"
    assert data["status"] == "New"


async def test_create_incident_missing_title(client, auth_headers):
    """タイトルなし → 422 バリデーションエラー"""
    resp = await client.post(
        "/api/v1/incidents",
        json={"priority": "P2"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_create_incident_invalid_priority(client, auth_headers):
    """無効なpriority (P5) → 422 バリデーションエラー"""
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Test", "priority": "P5"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ─── 一覧取得テスト ──────────────────────────────────────────────────────────

async def test_list_incidents_empty(client, auth_headers):
    """GET /incidents → 200, 空リスト（テスト開始時にデータなし）"""
    resp = await client.get("/api/v1/incidents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


async def test_list_incidents_with_data(client, auth_headers):
    """インシデント作成後の GET → total >= 1"""
    await client.post(
        "/api/v1/incidents",
        json={"title": "一覧テスト用インシデント"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/incidents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_list_incidents_pagination(client, auth_headers):
    """skip/limit パラメータ（page/size）が反映される"""
    resp = await client.get("/api/v1/incidents?page=1&size=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["size"] == 5


# ─── 詳細取得テスト ──────────────────────────────────────────────────────────

async def test_get_incident_not_found(client, auth_headers):
    """存在しない UUID → 404"""
    resp = await client.get(f"/api/v1/incidents/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── ステータス遷移テスト ────────────────────────────────────────────────────

async def test_incident_status_transition(client, auth_headers):
    """POST /transitions → New → Acknowledged ステータス変更確認"""
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "遷移テスト", "priority": "P2"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["incident_id"]

    trans_resp = await client.post(
        f"/api/v1/incidents/{inc_id}/transitions",
        json={"new_status": "Acknowledged"},
        headers=auth_headers,
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "Acknowledged"


# ─── 認証テスト ──────────────────────────────────────────────────────────────

async def test_unauthorized_access(client):
    """認証ヘッダーなし → 401"""
    resp = await client.get("/api/v1/incidents")
    assert resp.status_code == 401


# ─── SLA テスト ──────────────────────────────────────────────────────────────

async def test_incident_sla_fields_set(client, auth_headers):
    """P1 作成時に sla_response_due_at / sla_resolution_due_at が設定される"""
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "P1 SLAテスト", "priority": "P1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sla_response_due_at"] is not None
    assert data["sla_resolution_due_at"] is not None
