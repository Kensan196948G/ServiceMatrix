"""認証・RBAC結合テスト"""
import uuid
from unittest.mock import patch

import bcrypt as _bcrypt
import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.models.user import User, UserRole


def _make_hash(password: str) -> str:
    """bcrypt v5直接ハッシュ（passlib非経由）"""
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=4)).decode()


def _verify(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


@pytest_asyncio.fixture
async def mock_incident_seq():
    """func.nextval('incident_seq') の代替（SQLite非対応のためモック）"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"INC-2024-{_counter[0]:06d}"

    with patch("src.services.incident_service._get_next_incident_number", _get_next):
        yield


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        user_id=uuid.uuid4(),
        username="testadmin",
        email="admin@test.com",
        hashed_password=_make_hash("testpass123"),
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session):
    user = User(
        user_id=uuid.uuid4(),
        username="testviewer",
        email="viewer@test.com",
        hashed_password=_make_hash("testpass123"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ─── ログインテスト ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User, monkeypatch):
    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["access_token"]


@pytest.mark.asyncio
async def test_login_invalid_credentials(
    client: AsyncClient, test_user: User, monkeypatch
):
    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "anypassword",
    })
    assert resp.status_code == 401


# ─── /auth/me テスト ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_endpoint_with_valid_token(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "username" in data


@pytest.mark.asyncio
async def test_me_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_with_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401


# ─── インシデント作成 RBAC テスト ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_incident_with_valid_auth(
    client: AsyncClient, auth_headers: dict, mock_incident_seq
):
    resp = await client.post("/api/v1/incidents", headers=auth_headers, json={
        "title": "Test Incident",
        "description": "RBAC test incident",
        "priority": "P3",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_incident_without_auth(client: AsyncClient):
    resp = await client.post("/api/v1/incidents", json={
        "title": "Unauthorized Incident",
        "description": "Should be rejected",
        "priority": "P3",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_create_incident(
    client: AsyncClient, viewer_user: User
):
    """VIEWER roleはインシデント作成不可 → 403"""
    from src.core.security import create_access_token
    token = create_access_token({
        "sub": str(viewer_user.user_id),
        "role": viewer_user.role.value,
    })
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/incidents", headers=headers, json={
        "title": "Viewer Incident",
        "description": "Should be forbidden",
        "priority": "P3",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_system_admin_can_access_all(client: AsyncClient, auth_headers: dict):
    """SYSTEM_ADMINは主要エンドポイントにアクセス可能"""
    r1 = await client.get("/api/v1/incidents", headers=auth_headers)
    assert r1.status_code == 200

    r2 = await client.get("/api/v1/changes", headers=auth_headers)
    assert r2.status_code == 200

    r3 = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert r3.status_code == 200


# ─── ログイン成功フロー（last_login_at更新確認） ────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_both_tokens(client: AsyncClient, test_user: User, monkeypatch):
    """ログイン成功でaccess_tokenとrefresh_tokenの両方を返す"""
    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session, monkeypatch):
    """非アクティブユーザーのログインは403"""
    inactive_user = User(
        user_id=uuid.uuid4(),
        username="inactiveuser",
        email="inactive@test.com",
        hashed_password=_make_hash("testpass123"),
        role=UserRole.OPERATOR,
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.flush()

    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    resp = await client.post("/api/v1/auth/login", json={
        "username": "inactiveuser",
        "password": "testpass123",
    })
    assert resp.status_code == 403


# ─── リフレッシュトークンテスト ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, test_user: User, monkeypatch):
    """有効なリフレッシュトークンで新しいトークンペアを取得"""
    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "testpass123",
    })
    assert login_resp.status_code == 200
    refresh_tok = login_resp.json()["refresh_token"]

    refresh_resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_tok,
    })
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """無効なリフレッシュトークン → 401"""
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.refresh.token",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token(client: AsyncClient, test_user: User, monkeypatch):
    """アクセストークンをリフレッシュ用に使うと401（type != refresh）"""
    monkeypatch.setattr("src.api.v1.auth.verify_password", _verify)
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "testpass123",
    })
    access_tok = login_resp.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_tok,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_inactive_user(client: AsyncClient, db_session, monkeypatch):
    """リフレッシュ時にユーザーが非アクティブなら401"""
    from src.core.security import create_refresh_token
    user = User(
        user_id=uuid.uuid4(),
        username="refresh_inactive",
        email="refresh_inactive@test.com",
        hashed_password=_make_hash("testpass123"),
        role=UserRole.OPERATOR,
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    refresh_tok = create_refresh_token({"sub": str(user.user_id), "role": user.role.value})
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_tok,
    })
    assert resp.status_code == 401

