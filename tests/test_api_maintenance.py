"""メンテナンスウィンドウ API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def authed_user(db_session):
    """ユニークメールの SystemAdmin ユーザー（コミット後の重複を回避）"""
    from src.models.user import User, UserRole
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    user = User(
        user_id=uid,
        username=f"maint_admin_{uid.hex[:8]}",
        email=f"maint_{uid.hex[:8]}@test.com",
        hashed_password="fakehash",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(authed_user):
    from src.core.security import create_access_token
    token = create_access_token({"sub": str(authed_user.user_id), "role": "SystemAdmin"})
    return {"Authorization": f"Bearer {token}"}

BASE = "/api/v1/maintenance-windows"


def _window_payload(**kwargs):
    now = datetime.now(timezone.utc)
    defaults = {
        "name": "Test Window",
        "start_time": (now + timedelta(hours=1)).isoformat(),
        "end_time": (now + timedelta(hours=3)).isoformat(),
    }
    defaults.update(kwargs)
    return defaults


# ─── 一覧取得 ────────────────────────────────────────────────────────────────

async def test_list_maintenance_windows_empty(client, auth_headers):
    """GET /maintenance-windows → 200, リスト"""
    resp = await client.get(BASE, headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_maintenance_windows_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(BASE)
    assert resp.status_code == 401


# ─── 作成テスト ──────────────────────────────────────────────────────────────

async def test_create_maintenance_window_success(client, auth_headers):
    """POST /maintenance-windows → 201"""
    resp = await client.post(BASE, json=_window_payload(), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Window"
    assert "window_id" in data


async def test_create_maintenance_window_missing_name(client, auth_headers):
    """名前なし → 422"""
    now = datetime.now(timezone.utc)
    resp = await client.post(
        BASE,
        json={
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_create_maintenance_window_end_before_start(client, auth_headers):
    """end_time <= start_time → 422"""
    now = datetime.now(timezone.utc)
    resp = await client.post(
        BASE,
        json={
            "name": "Bad Window",
            "start_time": (now + timedelta(hours=3)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ─── 詳細取得 ────────────────────────────────────────────────────────────────

async def test_get_maintenance_window_success(client, auth_headers):
    """作成 → GET /{id} → 200"""
    create_resp = await client.post(BASE, json=_window_payload(name="GetTest"), headers=auth_headers)
    assert create_resp.status_code == 201
    window_id = create_resp.json()["window_id"]

    resp = await client.get(f"{BASE}/{window_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetTest"


async def test_get_maintenance_window_not_found(client, auth_headers):
    """存在しないID → 404"""
    resp = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── 更新テスト ──────────────────────────────────────────────────────────────

async def test_update_maintenance_window_success(client, auth_headers):
    """PATCH /{id} → 200, 名前が更新される"""
    create_resp = await client.post(BASE, json=_window_payload(name="Original"), headers=auth_headers)
    assert create_resp.status_code == 201
    window_id = create_resp.json()["window_id"]

    update_resp = await client.patch(
        f"{BASE}/{window_id}",
        json={"name": "Updated"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated"


async def test_update_maintenance_window_not_found(client, auth_headers):
    """存在しないID更新 → 404"""
    resp = await client.patch(
        f"{BASE}/{uuid.uuid4()}",
        json={"name": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── 削除テスト ──────────────────────────────────────────────────────────────

async def test_delete_maintenance_window_success(client, auth_headers):
    """DELETE /{id} → 204"""
    create_resp = await client.post(BASE, json=_window_payload(name="ToDelete"), headers=auth_headers)
    assert create_resp.status_code == 201
    window_id = create_resp.json()["window_id"]

    del_resp = await client.delete(f"{BASE}/{window_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{BASE}/{window_id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_delete_maintenance_window_not_found(client, auth_headers):
    """存在しないID削除 → 404"""
    resp = await client.delete(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── アクティブウィンドウ ────────────────────────────────────────────────────

async def test_list_active_windows(client, auth_headers):
    """GET /maintenance-windows/active → 200, リスト"""
    resp = await client.get(f"{BASE}/active", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_check_maintenance(client, auth_headers):
    """GET /maintenance-windows/check → 200, in_maintenance フィールドあり"""
    resp = await client.get(f"{BASE}/check", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "in_maintenance" in data
    assert "windows" in data
