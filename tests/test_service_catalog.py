"""ServiceCatalog API テスト"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_audit():
    with patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(return_value=None),
    ):
        yield


@pytest_asyncio.fixture(autouse=True)
async def mock_sr_seq():
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"SR-2024-{_counter[0]:06d}"

    with patch("src.services.service_request_service._get_next_sr_number", _get_next):
        yield


# ─── ServiceCatalog CRUD テスト ───────────────────────────────────────────────


async def test_list_catalog_empty(client):
    """GET /service-catalog - 空一覧"""
    resp = await client.get("/api/v1/service-catalog")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_catalog(client, auth_headers):
    """POST /service-catalog - 作成成功"""
    body = {
        "name": "テストサービス",
        "description": "説明",
        "category": "IT",
        "sla_hours": 8,
        "is_active": True,
    }
    resp = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "テストサービス"
    assert data["category"] == "IT"
    assert data["sla_hours"] == 8
    return data["catalog_id"]


async def test_list_catalog_returns_items(client, auth_headers):
    """GET /service-catalog - 作成後は一覧に現れる"""
    body = {"name": "サービスA", "is_active": True}
    await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    resp = await client.get("/api/v1/service-catalog")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["name"] == "サービスA" for i in items)


async def test_get_catalog_detail(client, auth_headers):
    """GET /service-catalog/{id} - 詳細取得"""
    body = {"name": "詳細テスト", "category": "CAT1", "sla_hours": 24}
    created = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    catalog_id = created.json()["catalog_id"]

    resp = await client.get(f"/api/v1/service-catalog/{catalog_id}")
    assert resp.status_code == 200
    assert resp.json()["catalog_id"] == catalog_id


async def test_get_catalog_not_found(client):
    """GET /service-catalog/{id} - 存在しないID → 404"""
    resp = await client.get(f"/api/v1/service-catalog/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_catalog(client, auth_headers):
    """PATCH /service-catalog/{id} - 更新成功"""
    body = {"name": "更新前", "is_active": True}
    created = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    catalog_id = created.json()["catalog_id"]

    resp = await client.patch(
        f"/api/v1/service-catalog/{catalog_id}",
        json={"name": "更新後", "sla_hours": 48},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新後"
    assert resp.json()["sla_hours"] == 48


async def test_update_catalog_not_found(client, auth_headers):
    """PATCH /service-catalog/{id} - 存在しないID → 404"""
    resp = await client.patch(
        f"/api/v1/service-catalog/{uuid.uuid4()}",
        json={"name": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_delete_catalog(client, auth_headers):
    """DELETE /service-catalog/{id} - 削除成功"""
    body = {"name": "削除対象"}
    created = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    catalog_id = created.json()["catalog_id"]

    resp = await client.delete(f"/api/v1/service-catalog/{catalog_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_catalog_not_found(client, auth_headers):
    """DELETE /service-catalog/{id} - 存在しないID → 404"""
    resp = await client.delete(
        f"/api/v1/service-catalog/{uuid.uuid4()}", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_request_from_catalog(client, auth_headers, db_session, authed_user):
    """POST /service-catalog/{id}/request - SRを作成"""
    body = {"name": "申請テスト", "category": "HW", "sla_hours": 4}
    created = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    catalog_id = created.json()["catalog_id"]

    resp = await client.post(
        f"/api/v1/service-catalog/{catalog_id}/request", headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "申請テスト"
    assert data["request_type"] == "HW"


async def test_request_from_catalog_not_found(client, auth_headers):
    """POST /service-catalog/{id}/request - 存在しないカタログ → 404"""
    resp = await client.post(
        f"/api/v1/service-catalog/{uuid.uuid4()}/request", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_create_catalog_requires_auth(client):
    """POST /service-catalog - 認証なし → 401"""
    resp = await client.post("/api/v1/service-catalog", json={"name": "X"})
    assert resp.status_code == 401


async def test_list_catalog_inactive_hidden(client, auth_headers):
    """GET /service-catalog - 非アクティブは一覧から除外"""
    # 非アクティブカタログを作成
    body = {"name": "非アクティブ", "is_active": False}
    created = await client.post("/api/v1/service-catalog", json=body, headers=auth_headers)
    catalog_id = created.json()["catalog_id"]

    # デフォルト（active_only=true）では表示されない
    resp = await client.get("/api/v1/service-catalog")
    assert resp.status_code == 200
    ids = [i["catalog_id"] for i in resp.json()]
    assert catalog_id not in ids

    # active_only=false では表示される
    resp2 = await client.get("/api/v1/service-catalog?active_only=false")
    assert resp2.status_code == 200
    ids2 = [i["catalog_id"] for i in resp2.json()]
    assert catalog_id in ids2
