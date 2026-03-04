"""バックアップ管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def authed_user(db_session):
    """ユニークメールの SystemAdmin ユーザー"""
    from src.models.user import User, UserRole
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    user = User(
        user_id=uid,
        username=f"backup_admin_{uid.hex[:8]}",
        email=f"backup_{uid.hex[:8]}@test.com",
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

BASE = "/api/v1/backup"


# ─── バックアップ作成 ────────────────────────────────────────────────────────

async def test_create_backup_success(client, auth_headers):
    """POST /backup/create → 200, filename/size_bytes/type 含む"""
    resp = await client.post(f"{BASE}/create", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data
    assert "size_bytes" in data
    assert "created_at" in data
    assert data["type"] in ("mock", "postgresql")


async def test_create_backup_unauthorized(client):
    """認証なし → 401"""
    resp = await client.post(f"{BASE}/create")
    assert resp.status_code == 401


# ─── バックアップ一覧 ────────────────────────────────────────────────────────

async def test_list_backups(client, auth_headers):
    """GET /backup/list → 200, backups/total 構造"""
    resp = await client.get(f"{BASE}/list", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "backups" in data
    assert "total" in data
    assert isinstance(data["backups"], list)
    assert data["total"] == len(data["backups"])


async def test_list_backups_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}/list")
    assert resp.status_code == 401


async def test_list_backups_after_create(client, auth_headers):
    """バックアップ作成後に一覧に反映される"""
    await client.post(f"{BASE}/create", headers=auth_headers)
    resp = await client.get(f"{BASE}/list", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


# ─── バックアップ状態 ────────────────────────────────────────────────────────

async def test_get_backup_status(client, auth_headers):
    """GET /backup/status → 200, backup_dir/db_type/total_backups 含む"""
    resp = await client.get(f"{BASE}/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "backup_dir" in data
    assert "db_type" in data
    assert "total_backups" in data
    assert data["db_type"] in ("sqlite", "postgresql")


async def test_get_backup_status_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}/status")
    assert resp.status_code == 401


# ─── ダウンロード ────────────────────────────────────────────────────────────

async def test_download_backup_not_found(client, auth_headers):
    """存在しないファイル → 404"""
    resp = await client.get(f"{BASE}/download/nonexistent.sql", headers=auth_headers)
    assert resp.status_code == 404


async def test_download_backup_path_traversal(client, auth_headers):
    """パストラバーサル攻撃（.. 含む） → 400"""
    resp = await client.get(f"{BASE}/download/..evil.sql", headers=auth_headers)
    assert resp.status_code == 400


async def test_download_backup_after_create(client, auth_headers):
    """作成後にダウンロード可能"""
    create_resp = await client.post(f"{BASE}/create", headers=auth_headers)
    assert create_resp.status_code == 200
    filename = create_resp.json()["filename"]

    dl_resp = await client.get(f"{BASE}/download/{filename}", headers=auth_headers)
    assert dl_resp.status_code == 200


# ─── 削除 ────────────────────────────────────────────────────────────────────

async def test_delete_backup_success(client, auth_headers):
    """作成 → DELETE → 200"""
    create_resp = await client.post(f"{BASE}/create", headers=auth_headers)
    filename = create_resp.json()["filename"]

    del_resp = await client.delete(f"{BASE}/{filename}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert "削除しました" in del_resp.json()["message"]


async def test_delete_backup_not_found(client, auth_headers):
    """存在しないファイル → 404"""
    resp = await client.delete(f"{BASE}/nonexistent.sql", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_backup_path_traversal(client, auth_headers):
    """パストラバーサル（.. 含む） → 400"""
    resp = await client.delete(f"{BASE}/..evil.sql", headers=auth_headers)
    assert resp.status_code == 400
