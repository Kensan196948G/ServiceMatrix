"""SSO/SAML認証統合テスト - Issue #76"""

import uuid

import pytest

from src.models.sso_provider import SSOProvider
from src.models.user import UserRole
from src.services.sso_service import SSOService, SSOUserInfo

# ---------------------------------------------------------------------------
# Unit tests: SSOService
# ---------------------------------------------------------------------------


@pytest.fixture
def svc() -> SSOService:
    return SSOService()


@pytest.fixture
def oidc_provider() -> SSOProvider:
    p = SSOProvider()
    p.provider_id = uuid.uuid4()
    p.name = "Okta Test"
    p.provider_type = "oidc"
    p.is_enabled = True
    p.oidc_client_id = "test-client-id"
    p.oidc_client_secret = "test-secret"  # noqa: S105
    p.oidc_discovery_url = "https://dev-123.okta.com/.well-known/openid-configuration"
    p.group_role_mapping_json = None
    return p


@pytest.fixture
def saml_provider() -> SSOProvider:
    p = SSOProvider()
    p.provider_id = uuid.uuid4()
    p.name = "Azure AD SAML"
    p.provider_type = "saml"
    p.is_enabled = True
    p.saml_idp_entity_id = "https://sts.windows.net/tenant-id/"
    p.saml_idp_sso_url = "https://login.microsoftonline.com/tenant-id/saml2"
    p.saml_idp_certificate = "MIIDcertdata..."
    p.group_role_mapping_json = None
    return p


# ─── グループ→ロールマッピング ─────────────────────────────────────────────────


def test_resolve_role_no_mapping_returns_viewer(
    svc: SSOService, oidc_provider: SSOProvider
) -> None:  # noqa: E501
    """マッピングなしの場合は VIEWER ロールを返す"""
    role = svc.resolve_role_from_groups(oidc_provider, ["Admins", "Users"])
    assert role == UserRole.VIEWER


def test_resolve_role_with_mapping(svc: SSOService, oidc_provider: SSOProvider) -> None:
    """グループマッピングからロールを解決する"""
    import json

    oidc_provider.group_role_mapping_json = json.dumps(
        {"Admins": "system_admin", "Operators": "operator"}
    )
    role = svc.resolve_role_from_groups(oidc_provider, ["Operators"])
    assert role == UserRole.OPERATOR


def test_resolve_role_highest_priority(svc: SSOService, oidc_provider: SSOProvider) -> None:
    """複数グループマッチ時は最上位ロールを採用する"""
    import json

    oidc_provider.group_role_mapping_json = json.dumps(
        {"Admins": "system_admin", "Operators": "operator"}
    )
    role = svc.resolve_role_from_groups(oidc_provider, ["Operators", "Admins"])
    assert role == UserRole.SYSTEM_ADMIN


def test_resolve_role_unknown_group_returns_viewer(
    svc: SSOService, oidc_provider: SSOProvider
) -> None:
    """未知グループは VIEWER にフォールバックする"""
    import json

    oidc_provider.group_role_mapping_json = json.dumps({"Admins": "system_admin"})
    role = svc.resolve_role_from_groups(oidc_provider, ["UnknownGroup"])
    assert role == UserRole.VIEWER


# ─── OIDC 認可 URL 生成 ────────────────────────────────────────────────────────


def test_build_oidc_authorization_url(svc: SSOService, oidc_provider: SSOProvider) -> None:
    """OIDC 認可 URL が正しく組み立てられる"""
    url = svc.build_oidc_authorization_url(
        oidc_provider,
        redirect_uri="https://app.local/callback",
        state="test-state-123",
    )
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "state=test-state-123" in url
    assert "openid" in url


def test_build_oidc_authorization_url_missing_config(svc: SSOService) -> None:
    """設定不完全な場合は ValueError を送出する"""
    provider = SSOProvider()
    provider.oidc_client_id = None
    provider.oidc_discovery_url = None
    with pytest.raises(ValueError, match="不完全"):
        svc.build_oidc_authorization_url(provider, "https://app.local/callback", "state")


# ─── SAML SP メタデータ生成 ────────────────────────────────────────────────────


def test_generate_sp_metadata(svc: SSOService, saml_provider: SSOProvider) -> None:
    """SAML SP メタデータ XML が生成される"""
    metadata = svc.generate_sp_metadata(
        saml_provider,
        sp_entity_id="https://servicematrix.local/saml",
        acs_url="https://servicematrix.local/api/v1/auth/sso/saml/acs",
    )
    assert "EntityDescriptor" in metadata
    assert "servicematrix.local/saml" in metadata
    assert "AssertionConsumerService" in metadata


# ─── JIT プロビジョニング ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provision_user_creates_new_user(
    db_session, svc: SSOService, oidc_provider: SSOProvider
) -> None:
    """新規ユーザーが JIT プロビジョニングされる"""
    user_info = SSOUserInfo(
        email="sso-newuser@example.com",
        display_name="SSO New User",
        groups=[],
        idp_subject="okta|abc123",
    )
    user = await svc.provision_user(db_session, oidc_provider, user_info)
    assert user.email == "sso-newuser@example.com"
    assert user.full_name == "SSO New User"
    assert user.role == UserRole.VIEWER
    assert user.hashed_password == "sso-managed"  # noqa: S105


@pytest.mark.asyncio
async def test_provision_user_updates_existing_user(
    db_session, svc: SSOService, oidc_provider: SSOProvider
) -> None:
    """既存ユーザーの情報が更新される"""
    import json

    from src.models.user import User

    # 既存ユーザーを作成
    existing = User(
        email="sso-existing@example.com",
        username="sso-existing",
        full_name="Old Name",
        hashed_password="old-hash",  # noqa: S106
        role=UserRole.VIEWER,
    )
    db_session.add(existing)
    await db_session.flush()

    oidc_provider.group_role_mapping_json = json.dumps({"Admins": "system_admin"})
    user_info = SSOUserInfo(
        email="sso-existing@example.com",
        display_name="New Name",
        groups=["Admins"],
        idp_subject="okta|xyz789",
    )
    user = await svc.provision_user(db_session, oidc_provider, user_info)
    assert user.full_name == "New Name"
    assert user.role == UserRole.SYSTEM_ADMIN


# ─── SSO プロバイダー CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_sso_provider(db_session, svc: SSOService) -> None:
    """OIDC プロバイダーを作成できる"""
    provider = await svc.create_provider(
        db_session,
        name="Test Okta",
        provider_type="oidc",
        oidc_client_id="client-123",
        oidc_discovery_url="https://dev.okta.com/.well-known/openid-configuration",
    )
    assert provider.name == "Test Okta"
    assert provider.provider_type == "oidc"
    assert provider.oidc_client_id == "client-123"


@pytest.mark.asyncio
async def test_get_sso_provider_not_found(db_session, svc: SSOService) -> None:
    """存在しないプロバイダーは None"""
    result = await svc.get_provider(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_delete_sso_provider(db_session, svc: SSOService) -> None:
    """プロバイダーを削除できる"""
    provider = await svc.create_provider(db_session, name="Delete Test", provider_type="saml")
    result = await svc.delete_provider(db_session, provider.provider_id)
    assert result is True
    assert await svc.get_provider(db_session, provider.provider_id) is None


@pytest.mark.asyncio
async def test_delete_sso_provider_not_found(db_session, svc: SSOService) -> None:
    """存在しないプロバイダー削除は False"""
    result = await svc.delete_provider(db_session, uuid.uuid4())
    assert result is False


# ─── API エンドポイントテスト ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_sso_provider_endpoint(client, auth_headers) -> None:
    """SSO プロバイダー作成エンドポイント"""
    payload = {
        "name": "Okta Production",
        "provider_type": "oidc",
        "oidc_client_id": "prod-client-id",
        "oidc_discovery_url": "https://company.okta.com/.well-known/openid-configuration",
    }
    resp = await client.post("/api/v1/auth/sso/providers", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Okta Production"
    assert data["provider_type"] == "oidc"
    assert data["is_enabled"] is True


@pytest.mark.asyncio
async def test_list_sso_providers_endpoint(client, auth_headers) -> None:
    """SSO プロバイダー一覧エンドポイント"""
    resp = await client.get("/api/v1/auth/sso/providers", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_sso_provider_not_found_endpoint(client, auth_headers) -> None:
    """存在しない SSO プロバイダーは 404"""
    resp = await client.get(f"/api/v1/auth/sso/providers/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_sso_provider_endpoint(client, auth_headers) -> None:
    """SSO プロバイダー削除エンドポイント"""
    create_resp = await client.post(
        "/api/v1/auth/sso/providers",
        json={"name": "Delete Me", "provider_type": "saml"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    provider_id = create_resp.json()["provider_id"]
    resp = await client.delete(f"/api/v1/auth/sso/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sso_endpoint_unauthorized(client) -> None:
    """認証なしは 401"""
    resp = await client.get("/api/v1/auth/sso/providers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_oidc_login_endpoint(client, auth_headers) -> None:
    """OIDC ログイン URL 取得エンドポイント"""
    create_resp = await client.post(
        "/api/v1/auth/sso/providers",
        json={
            "name": "OIDC Login Test",
            "provider_type": "oidc",
            "oidc_client_id": "test-id",
            "oidc_discovery_url": "https://dev.okta.com/.well-known/openid-configuration",
        },
        headers=auth_headers,
    )
    provider_id = create_resp.json()["provider_id"]
    resp = await client.get(
        f"/api/v1/auth/sso/{provider_id}/oidc/login",
        params={"redirect_uri": "https://app.local/callback"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_url" in data
    assert "state" in data


@pytest.mark.asyncio
async def test_oidc_callback_provisions_user(client, auth_headers) -> None:
    """OIDC コールバックで JIT プロビジョニングと JWT 発行"""
    create_resp = await client.post(
        "/api/v1/auth/sso/providers",
        json={
            "name": "JIT Test Provider",
            "provider_type": "oidc",
            "oidc_client_id": "jit-client",
            "group_role_mapping": {"Operators": "operator"},
        },
        headers=auth_headers,
    )
    provider_id = create_resp.json()["provider_id"]
    resp = await client.post(
        f"/api/v1/auth/sso/{provider_id}/oidc/callback",
        json={
            "email": "jit-user@example.com",
            "display_name": "JIT User",
            "groups": ["Operators"],
            "idp_subject": "okta|jit001",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["user_email"] == "jit-user@example.com"
    assert data["role"] == "Operator"


@pytest.mark.asyncio
async def test_saml_metadata_endpoint(client, auth_headers) -> None:
    """SAML SP メタデータ XML 取得エンドポイント"""
    create_resp = await client.post(
        "/api/v1/auth/sso/providers",
        json={"name": "SAML Meta Test", "provider_type": "saml"},
        headers=auth_headers,
    )
    provider_id = create_resp.json()["provider_id"]
    resp = await client.get(f"/api/v1/auth/sso/{provider_id}/saml/metadata")
    assert resp.status_code == 200
    assert "EntityDescriptor" in resp.text
    assert "AssertionConsumerService" in resp.text
