"""マルチテナント基盤テスト - Issue #75"""

import uuid

import pytest

from src.models.tenant import Tenant, TenantPlan
from src.services.tenant_service import TenantService

# ---------------------------------------------------------------------------
# Unit tests: TenantService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tenant(db_session) -> None:
    """テナント作成"""
    svc = TenantService()
    tenant = await svc.create_tenant(
        db_session,
        name="テスト株式会社",
        slug="test-corp",
        plan=TenantPlan.STANDARD,
        settings={"max_users": 100},
    )
    assert isinstance(tenant.tenant_id, uuid.UUID)
    assert tenant.name == "テスト株式会社"
    assert tenant.slug == "test-corp"
    assert tenant.plan == TenantPlan.STANDARD
    assert tenant.is_active is True


@pytest.mark.asyncio
async def test_get_tenant(db_session) -> None:
    """テナントID取得"""
    svc = TenantService()
    created = await svc.create_tenant(db_session, name="取得テスト", slug="get-test")
    found = await svc.get_tenant(db_session, created.tenant_id)
    assert found is not None
    assert found.tenant_id == created.tenant_id


@pytest.mark.asyncio
async def test_get_tenant_not_found(db_session) -> None:
    """存在しないテナントは None"""
    svc = TenantService()
    result = await svc.get_tenant(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_tenant_by_slug(db_session) -> None:
    """slug でのテナント取得"""
    svc = TenantService()
    await svc.create_tenant(db_session, name="Slug テスト", slug="slug-test-unique")
    found = await svc.get_tenant_by_slug(db_session, "slug-test-unique")
    assert found is not None
    assert found.slug == "slug-test-unique"


@pytest.mark.asyncio
async def test_list_tenants(db_session) -> None:
    """テナント一覧取得"""
    svc = TenantService()
    await svc.create_tenant(db_session, name="一覧A", slug="list-a-unique")
    await svc.create_tenant(db_session, name="一覧B", slug="list-b-unique")
    tenants = await svc.list_tenants(db_session, limit=100)
    assert len(tenants) >= 2


@pytest.mark.asyncio
async def test_update_tenant(db_session) -> None:
    """テナント更新"""
    svc = TenantService()
    created = await svc.create_tenant(db_session, name="更新前", slug="update-test-unique")
    updated = await svc.update_tenant(
        db_session,
        tenant_id=created.tenant_id,
        name="更新後",
        plan=TenantPlan.ENTERPRISE,
        is_active=False,
    )
    assert updated is not None
    assert updated.name == "更新後"
    assert updated.plan == TenantPlan.ENTERPRISE
    assert updated.is_active is False


@pytest.mark.asyncio
async def test_update_tenant_not_found(db_session) -> None:
    """存在しないテナント更新は None"""
    svc = TenantService()
    result = await svc.update_tenant(db_session, uuid.uuid4(), name="x")
    assert result is None


@pytest.mark.asyncio
async def test_delete_tenant(db_session) -> None:
    """テナント削除"""
    svc = TenantService()
    created = await svc.create_tenant(db_session, name="削除テスト", slug="delete-test-unique")
    result = await svc.delete_tenant(db_session, created.tenant_id)
    assert result is True
    assert await svc.get_tenant(db_session, created.tenant_id) is None


@pytest.mark.asyncio
async def test_delete_tenant_not_found(db_session) -> None:
    """存在しないテナント削除は False"""
    svc = TenantService()
    result = await svc.delete_tenant(db_session, uuid.uuid4())
    assert result is False


def test_get_tenant_settings_empty() -> None:
    """設定なしのテナントは空辞書"""
    svc = TenantService()
    tenant = Tenant()
    tenant.settings_json = None
    assert svc.get_tenant_settings(tenant) == {}


def test_get_tenant_settings_with_data() -> None:
    """設定ありのテナントはデシリアライズされた辞書"""
    import json

    svc = TenantService()
    tenant = Tenant()
    tenant.settings_json = json.dumps({"key": "value"})
    assert svc.get_tenant_settings(tenant) == {"key": "value"}


def test_is_plan_allowed_free() -> None:
    """FREE テナントは FREE プランのみ許可"""
    svc = TenantService()
    tenant = Tenant()
    tenant.plan = TenantPlan.FREE
    assert svc.is_plan_allowed(tenant, TenantPlan.FREE) is True
    assert svc.is_plan_allowed(tenant, TenantPlan.STANDARD) is False
    assert svc.is_plan_allowed(tenant, TenantPlan.ENTERPRISE) is False


def test_is_plan_allowed_enterprise() -> None:
    """ENTERPRISE テナントは全プランを許可"""
    svc = TenantService()
    tenant = Tenant()
    tenant.plan = TenantPlan.ENTERPRISE
    assert svc.is_plan_allowed(tenant, TenantPlan.FREE) is True
    assert svc.is_plan_allowed(tenant, TenantPlan.STANDARD) is True
    assert svc.is_plan_allowed(tenant, TenantPlan.ENTERPRISE) is True


# ---------------------------------------------------------------------------
# Middleware tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_middleware_valid_header(client) -> None:
    """有効な X-Tenant-ID ヘッダーはそのまま通す"""
    tenant_id = str(uuid.uuid4())
    resp = await client.get("/api/v1/health", headers={"X-Tenant-ID": tenant_id})
    assert resp.status_code == 200
    assert resp.headers.get("x-tenant-id") == tenant_id


@pytest.mark.asyncio
async def test_tenant_middleware_invalid_header(client) -> None:
    """不正な X-Tenant-ID は 400"""
    resp = await client.get("/api/v1/health", headers={"X-Tenant-ID": "not-a-uuid"})
    assert resp.status_code == 400
    assert "X-Tenant-ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_middleware_no_header(client) -> None:
    """X-Tenant-ID なしは通常通り処理"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "x-tenant-id" not in resp.headers


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tenant_endpoint(client, auth_headers) -> None:
    """テナント作成エンドポイント"""
    payload = {
        "name": "API テスト株式会社",
        "slug": "api-test-corp",
        "plan": "standard",
    }
    resp = await client.post("/api/v1/tenants", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API テスト株式会社"
    assert data["slug"] == "api-test-corp"
    assert data["plan"] == "standard"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug(client, auth_headers) -> None:
    """重複 slug は 409"""
    payload = {"name": "重複テスト", "slug": "dup-slug-test"}
    await client.post("/api/v1/tenants", json=payload, headers=auth_headers)
    resp = await client.post("/api/v1/tenants", json=payload, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_tenants_endpoint(client, auth_headers) -> None:
    """テナント一覧エンドポイント"""
    resp = await client.get("/api/v1/tenants", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_tenant_endpoint(client, auth_headers) -> None:
    """テナント取得エンドポイント"""
    create_resp = await client.post(
        "/api/v1/tenants",
        json={"name": "取得テスト", "slug": "get-endpoint-test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    tenant_id = create_resp.json()["tenant_id"]
    resp = await client.get(f"/api/v1/tenants/{tenant_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_get_tenant_not_found_endpoint(client, auth_headers) -> None:
    """存在しないテナントは 404"""
    resp = await client.get(f"/api/v1/tenants/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tenant_endpoint(client, auth_headers) -> None:
    """テナント更新エンドポイント"""
    create_resp = await client.post(
        "/api/v1/tenants",
        json={"name": "更新前テナント", "slug": "update-endpoint-test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    tenant_id = create_resp.json()["tenant_id"]
    resp = await client.patch(
        f"/api/v1/tenants/{tenant_id}",
        json={"name": "更新後テナント", "plan": "enterprise"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新後テナント"
    assert resp.json()["plan"] == "enterprise"


@pytest.mark.asyncio
async def test_delete_tenant_endpoint(client, auth_headers) -> None:
    """テナント削除エンドポイント"""
    create_resp = await client.post(
        "/api/v1/tenants",
        json={"name": "削除エンドポイントテスト", "slug": "delete-endpoint-test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    tenant_id = create_resp.json()["tenant_id"]
    resp = await client.delete(f"/api/v1/tenants/{tenant_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_tenant_endpoint_unauthorized(client) -> None:
    """認証なしは 401"""
    resp = await client.get("/api/v1/tenants")
    assert resp.status_code == 401
