"""CMDB構成管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_cmdb_audit():
    """audit_log_seq の代替（SQLite非対応のためモック）"""
    with patch(
        "src.services.cmdb_service.audit_service.record_audit_log",
        new=AsyncMock(return_value=None),
    ):
        yield


# ─── CI作成テスト ─────────────────────────────────────────────────────────────

async def test_create_ci(client, auth_headers):
    """POST /cmdb/cis → 201, CIが作成される"""
    resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "本番Webサーバー01", "ci_type": "Server"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ci_name"] == "本番Webサーバー01"
    assert data["ci_type"] == "Server"
    assert data["status"] == "Active"


# ─── CI取得テスト ─────────────────────────────────────────────────────────────

async def test_get_ci(client, auth_headers):
    """POST → GET /cmdb/cis/{id} → 200, 同一データ確認"""
    create_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "取得テストDB01", "ci_type": "Database"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    ci_id = create_resp.json()["ci_id"]

    resp = await client.get(f"/api/v1/cmdb/cis/{ci_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ci_id"] == ci_id
    assert data["ci_name"] == "取得テストDB01"
    assert data["ci_type"] == "Database"


# ─── CI一覧テスト ─────────────────────────────────────────────────────────────

async def test_list_cis(client, auth_headers):
    """GET /cmdb/cis → 200, リスト形式で返却"""
    resp = await client.get("/api/v1/cmdb/cis", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ─── CI更新テスト ─────────────────────────────────────────────────────────────

async def test_update_ci(client, auth_headers):
    """PATCH /cmdb/cis/{id} → 200, フィールド更新確認"""
    create_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "更新テストサーバー", "ci_type": "Server"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    ci_id = create_resp.json()["ci_id"]

    update_resp = await client.patch(
        f"/api/v1/cmdb/cis/{ci_id}",
        json={"status": "Maintenance", "version": "2.1.0"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["status"] == "Maintenance"
    assert data["version"] == "2.1.0"


# ─── 404テスト ───────────────────────────────────────────────────────────────

async def test_ci_not_found(client, auth_headers):
    """存在しない UUID → 404"""
    resp = await client.get(f"/api/v1/cmdb/cis/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── 影響分析テスト ──────────────────────────────────────────────────────────

async def test_get_ci_impact_analysis(client, auth_headers):
    """GET /cmdb/cis/{id}/impact → 200, 影響分析レスポンス構造確認"""
    create_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "影響分析テストCI", "ci_type": "Application"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    ci_id = create_resp.json()["ci_id"]

    resp = await client.get(f"/api/v1/cmdb/cis/{ci_id}/impact", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ci_id"] == ci_id
    assert "direct_dependents" in data
    assert "transitive_count" in data
    assert isinstance(data["direct_dependents"], list)


# ─── CI関係作成テスト ─────────────────────────────────────────────────────────

async def test_create_ci_relationship(client, auth_headers):
    """POST /cmdb/relationships → 201, CI間の関係が作成される"""
    ci1_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "関係元サーバー", "ci_type": "Server"},
        headers=auth_headers,
    )
    assert ci1_resp.status_code == 201
    ci1_id = ci1_resp.json()["ci_id"]

    ci2_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "関係先DB", "ci_type": "Database"},
        headers=auth_headers,
    )
    assert ci2_resp.status_code == 201
    ci2_id = ci2_resp.json()["ci_id"]

    rel_resp = await client.post(
        "/api/v1/cmdb/relationships",
        json={
            "source_ci_id": ci1_id,
            "target_ci_id": ci2_id,
            "relationship_type": "depends_on",
        },
        headers=auth_headers,
    )
    assert rel_resp.status_code == 201
    data = rel_resp.json()
    assert data["source_ci_id"] == ci1_id
    assert data["target_ci_id"] == ci2_id
    assert data["relationship_type"] == "depends_on"


# ─── CI関係一覧テスト ─────────────────────────────────────────────────────────

async def test_list_ci_relationships(client, auth_headers):
    """GET /cmdb/cis/{id}/relationships → 200, リスト形式で返却"""
    create_resp = await client.post(
        "/api/v1/cmdb/cis",
        json={"ci_name": "関係一覧テストCI", "ci_type": "Network"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    ci_id = create_resp.json()["ci_id"]

    resp = await client.get(f"/api/v1/cmdb/cis/{ci_id}/relationships", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
