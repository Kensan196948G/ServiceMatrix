"""テナント管理テスト - API + サービス層（12ケース以上）"""

import uuid

import pytest
import pytest_asyncio

from src.models.tenant import Tenant
from src.services import tenant_service

# ─── ヘルパー ─────────────────────────────────────────────────────────


def _tenant_payload(slug: str = "test-tenant", name: str = "Test Tenant"):
    return {"name": name, "slug": slug, "description": "テスト用テナント"}


@pytest_asyncio.fixture
async def sample_tenant(db_session):
    """テスト用テナントをDBに直接作成"""
    tenant = Tenant(
        tenant_id=uuid.uuid4(),
        name="Sample Tenant",
        slug="sample-tenant",
        description="サンプルテナント",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    await db_session.refresh(tenant)
    return tenant


# ─── API エンドポイントテスト ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_tenant(client, auth_headers):
    """POST /api/v1/tenants - テナント作成"""
    resp = await client.post(
        "/api/v1/tenants",
        json=_tenant_payload("create-test"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "create-test"
    assert body["name"] == "Test Tenant"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug(client, auth_headers, sample_tenant):
    """POST /api/v1/tenants - 重複スラッグで409"""
    resp = await client.post(
        "/api/v1/tenants",
        json=_tenant_payload(sample_tenant.slug),
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "既に使用されています" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_tenant(client, auth_headers, sample_tenant):
    """GET /api/v1/tenants/{id} - テナント詳細取得"""
    resp = await client.get(
        f"/api/v1/tenants/{sample_tenant.tenant_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == sample_tenant.slug


@pytest.mark.asyncio
async def test_get_tenant_not_found(client, auth_headers):
    """GET /api/v1/tenants/{id} - 存在しないIDで404"""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/tenants/{fake_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_tenants(client, auth_headers, sample_tenant):
    """GET /api/v1/tenants - テナント一覧取得"""
    resp = await client.get("/api/v1/tenants", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_update_tenant(client, auth_headers, sample_tenant):
    """PUT /api/v1/tenants/{id} - テナント更新"""
    resp = await client.put(
        f"/api/v1/tenants/{sample_tenant.tenant_id}",
        json={"name": "Updated Tenant"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Tenant"


@pytest.mark.asyncio
async def test_delete_tenant(client, auth_headers, sample_tenant):
    """DELETE /api/v1/tenants/{id} - テナント削除"""
    resp = await client.delete(
        f"/api/v1/tenants/{sample_tenant.tenant_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # 削除確認
    resp2 = await client.get(
        f"/api/v1/tenants/{sample_tenant.tenant_id}",
        headers=auth_headers,
    )
    assert resp2.status_code == 404


# ─── サービス層直接テスト ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_create_tenant_direct(db_session):
    """tenant_service.create_tenant 直接呼び出し"""
    tenant = await tenant_service.create_tenant(
        db_session, {"name": "Direct Tenant", "slug": "direct-tenant"}
    )
    assert tenant.slug == "direct-tenant"
    assert tenant.tenant_id is not None


@pytest.mark.asyncio
async def test_service_get_tenant_by_slug_direct(db_session, sample_tenant):
    """tenant_service.get_tenant_by_slug 直接呼び出し"""
    found = await tenant_service.get_tenant_by_slug(db_session, sample_tenant.slug)
    assert found is not None
    assert found.name == sample_tenant.name


@pytest.mark.asyncio
async def test_service_list_tenants_direct(db_session, sample_tenant):
    """tenant_service.list_tenants 直接呼び出し"""
    tenants = await tenant_service.list_tenants(db_session, limit=50, offset=0)
    assert len(tenants) >= 1
    slugs = [t.slug for t in tenants]
    assert sample_tenant.slug in slugs


@pytest.mark.asyncio
async def test_service_update_tenant_direct(db_session, sample_tenant):
    """tenant_service.update_tenant 直接呼び出し"""
    updated = await tenant_service.update_tenant(
        db_session, sample_tenant.tenant_id, {"name": "Updated Direct"}
    )
    assert updated is not None
    assert updated.name == "Updated Direct"


@pytest.mark.asyncio
async def test_tenant_is_active_default(db_session):
    """Tenantモデルのis_activeデフォルト値確認"""
    tenant = await tenant_service.create_tenant(
        db_session, {"name": "Active Test", "slug": "active-default-test"}
    )
    assert tenant.is_active is True


@pytest.mark.asyncio
async def test_service_delete_tenant_not_found(db_session):
    """tenant_service.delete_tenant 存在しないIDでFalse"""
    result = await tenant_service.delete_tenant(db_session, uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_create_tenant_invalid_slug(client, auth_headers):
    """POST /api/v1/tenants - 不正なスラッグで422"""
    resp = await client.post(
        "/api/v1/tenants",
        json={"name": "Bad Slug", "slug": "INVALID SLUG!!"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
