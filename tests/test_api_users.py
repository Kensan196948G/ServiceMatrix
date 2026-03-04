"""ユーザー管理API テスト - GET /auth/users, POST /auth/users"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.core.security import create_access_token
from src.models.user import User, UserRole


def _make_hash(password: str) -> str:
    import bcrypt as _bcrypt
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=4)).decode()


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        user_id=uuid.uuid4(),
        username="admin_users_test",
        email="admin_users@test.com",
        hashed_password=_make_hash("adminpass123"),
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_headers(admin_user):
    token = create_access_token({"sub": str(admin_user.user_id), "role": UserRole.SYSTEM_ADMIN.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def manager_user(db_session):
    user = User(
        user_id=uuid.uuid4(),
        username="manager_users_test",
        email="manager_users@test.com",
        hashed_password=_make_hash("managerpass123"),
        role=UserRole.SERVICE_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def manager_headers(manager_user):
    token = create_access_token({"sub": str(manager_user.user_id), "role": UserRole.SERVICE_MANAGER.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def viewer_user(db_session):
    user = User(
        user_id=uuid.uuid4(),
        username="viewer_users_test",
        email="viewer_users@test.com",
        hashed_password=_make_hash("viewerpass123"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_headers(viewer_user):
    token = create_access_token({"sub": str(viewer_user.user_id), "role": UserRole.VIEWER.value})
    return {"Authorization": f"Bearer {token}"}


# ─── GET /auth/users ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, admin_user, admin_headers):
    """SystemAdmin はユーザー一覧を取得できる"""
    resp = await client.get("/api/v1/auth/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert admin_user.username in usernames


@pytest.mark.asyncio
async def test_list_users_as_manager(client: AsyncClient, manager_user, manager_headers):
    """ServiceManager もユーザー一覧を取得できる"""
    resp = await client.get("/api/v1/auth/users", headers=manager_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_users_as_viewer_forbidden(client: AsyncClient, viewer_user, viewer_headers):
    """Viewer はユーザー一覧取得不可 → 403"""
    resp = await client.get("/api/v1/auth/users", headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_without_auth(client: AsyncClient):
    """未認証でのアクセスは 401"""
    resp = await client.get("/api/v1/auth/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_users_response_schema(client: AsyncClient, admin_user, admin_headers):
    """レスポンスが UserResponse スキーマに準拠している"""
    resp = await client.get("/api/v1/auth/users", headers=admin_headers)
    assert resp.status_code == 200
    for user in resp.json():
        assert "user_id" in user
        assert "username" in user
        assert "email" in user
        assert "role" in user
        assert "is_active" in user


# ─── POST /auth/users ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, admin_user, admin_headers):
    """SystemAdmin は新規ユーザーを作成できる"""
    payload = {
        "username": "newuser_create",
        "email": "newuser_create@test.com",
        "password": "securepass123",
        "full_name": "New User",
        "role": "Viewer",
        "is_active": True,
    }
    resp = await client.post("/api/v1/auth/users", headers=admin_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser_create"
    assert data["email"] == "newuser_create@test.com"
    assert data["role"] == "Viewer"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient, admin_user, admin_headers):
    """重複ユーザー名で 400"""
    payload = {
        "username": admin_user.username,
        "email": "unique_email_dup@test.com",
        "password": "securepass123",
        "role": "Viewer",
    }
    resp = await client.post("/api/v1/auth/users", headers=admin_headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, admin_user, admin_headers):
    """重複メールアドレスで 400"""
    payload = {
        "username": "unique_username_dup",
        "email": admin_user.email,
        "password": "securepass123",
        "role": "Viewer",
    }
    resp = await client.post("/api/v1/auth/users", headers=admin_headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_user_invalid_role(client: AsyncClient, admin_user, admin_headers):
    """無効なロール文字列で 400"""
    payload = {
        "username": "invalid_role_user",
        "email": "invalid_role@test.com",
        "password": "securepass123",
        "role": "InvalidRole",
    }
    resp = await client.post("/api/v1/auth/users", headers=admin_headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_user_as_viewer_forbidden(client: AsyncClient, viewer_user, viewer_headers):
    """Viewer はユーザー作成不可 → 403"""
    payload = {
        "username": "forbidden_create",
        "email": "forbidden_create@test.com",
        "password": "securepass123",
        "role": "Viewer",
    }
    resp = await client.post("/api/v1/auth/users", headers=viewer_headers, json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user_without_auth(client: AsyncClient):
    """未認証でのユーザー作成は 401"""
    payload = {
        "username": "noauth_create",
        "email": "noauth_create@test.com",
        "password": "securepass123",
        "role": "Viewer",
    }
    resp = await client.post("/api/v1/auth/users", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_user_as_manager_forbidden(client: AsyncClient, manager_user, manager_headers):
    """ServiceManager はユーザー作成不可（SystemAdminのみ）→ 403"""
    payload = {
        "username": "manager_created_user",
        "email": "manager_created@test.com",
        "password": "securepass123",
        "role": "Viewer",
    }
    resp = await client.post("/api/v1/auth/users", headers=manager_headers, json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user_with_all_roles(client: AsyncClient, admin_user, admin_headers):
    """各ロールでユーザー作成できる"""
    for role_val in ["SystemAdmin", "ServiceManager", "Operator", "Viewer"]:
        payload = {
            "username": f"role_test_{role_val.lower()}",
            "email": f"role_test_{role_val.lower()}@test.com",
            "password": "securepass123",
            "role": role_val,
        }
        resp = await client.post("/api/v1/auth/users", headers=admin_headers, json=payload)
        assert resp.status_code == 201, f"Failed for role {role_val}: {resp.text}"
        assert resp.json()["role"] == role_val
