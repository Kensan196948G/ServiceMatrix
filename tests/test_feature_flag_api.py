"""Feature Flag REST API テスト - Issue #91, Phase 9-DEPLOY-2"""

from __future__ import annotations

import uuid
from datetime import UTC

import pytest
import pytest_asyncio

from src.models.user import User, UserRole

BASE_URL = "/api/v1/feature-flags"


# ── Redis モック（テスト環境では Redis 不使用） ───────────────────────────────


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch) -> None:
    """テスト環境で get_redis を None 返しに差し替え（Redis 不使用フォールバック）。"""
    monkeypatch.setattr("src.api.v1.feature_flags.get_redis", lambda: None)


# ── ヘルパー ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def viewer_headers(db_session):
    """VIEWER ロールの認証ヘッダー"""
    from datetime import datetime

    from src.core.security import create_access_token

    uid = uuid.uuid4()
    now = datetime.now(UTC)
    user = User(
        user_id=uid,
        username=f"viewer_{uid.hex[:8]}",
        email=f"viewer_{uid.hex[:8]}@test.com",
        hashed_password="fakehash",  # noqa: S106
        role=UserRole.VIEWER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token({"sub": str(uid), "role": "Viewer"})
    return {"Authorization": f"Bearer {token}"}


async def _create_flag(client, headers: dict, name: str, **kwargs) -> dict:
    """テスト用フラグを API 経由で作成するヘルパー。"""
    payload = {"name": name, "is_enabled": True, **kwargs}
    resp = await client.post(BASE_URL, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── 一覧取得 ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_feature_flags_empty(client, auth_headers) -> None:
    """フラグがない場合は空リスト"""
    resp = await client.get(BASE_URL, headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_feature_flags_with_data(client, auth_headers) -> None:
    """作成済みフラグが一覧に含まれる"""
    await _create_flag(client, auth_headers, "list_test_flag_a")
    await _create_flag(client, auth_headers, "list_test_flag_b")
    resp = await client.get(BASE_URL, headers=auth_headers)
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()]
    assert "list_test_flag_a" in names
    assert "list_test_flag_b" in names


@pytest.mark.asyncio
async def test_list_feature_flags_enabled_only(client, auth_headers) -> None:
    """enabled_only=true フィルタ"""
    await _create_flag(client, auth_headers, "enabled_flag_test", is_enabled=True)
    # 無効フラグを作成
    resp_disabled = await client.post(
        BASE_URL,
        json={"name": "disabled_flag_test", "is_enabled": False},
        headers=auth_headers,
    )
    assert resp_disabled.status_code == 201

    resp = await client.get(f"{BASE_URL}?enabled_only=true", headers=auth_headers)
    assert resp.status_code == 200
    flags = resp.json()
    for f in flags:
        assert f["is_enabled"] is True


@pytest.mark.asyncio
async def test_list_feature_flags_viewer_can_read(client, viewer_headers) -> None:
    """VIEWER ロールでも一覧取得できる"""
    resp = await client.get(BASE_URL, headers=viewer_headers)
    assert resp.status_code == 200


# ── 作成 ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_feature_flag_success(client, auth_headers) -> None:
    """フラグ正常作成"""
    payload = {
        "name": "new_incident_ui",
        "description": "新UIのテスト",
        "is_enabled": True,
        "rollout_percentage": 50.0,
    }
    resp = await client.post(BASE_URL, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "new_incident_ui"
    assert data["is_enabled"] is True
    assert data["rollout_percentage"] == 50.0
    assert data["description"] == "新UIのテスト"
    assert "flag_id" in data


@pytest.mark.asyncio
async def test_create_feature_flag_duplicate(client, auth_headers) -> None:
    """同名フラグの重複作成は 409"""
    await _create_flag(client, auth_headers, "duplicate_flag")
    resp = await client.post(
        BASE_URL, json={"name": "duplicate_flag"}, headers=auth_headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_feature_flag_invalid_name(client, auth_headers) -> None:
    """無効なフラグ名（大文字含む）は 422"""
    resp = await client.post(
        BASE_URL, json={"name": "InvalidName"}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_feature_flag_viewer_forbidden(client, viewer_headers) -> None:
    """VIEWER ロールでの作成は 403"""
    resp = await client.post(
        BASE_URL, json={"name": "forbidden_flag"}, headers=viewer_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_feature_flag_with_tenant(client, auth_headers) -> None:
    """テナント限定フラグの作成"""
    tenant_id = str(uuid.uuid4())
    payload = {"name": "tenant_flag_create", "tenant_id": tenant_id}
    resp = await client.post(BASE_URL, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == tenant_id


# ── 取得（名前） ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_feature_flag_success(client, auth_headers) -> None:
    """名前でのフラグ取得"""
    await _create_flag(client, auth_headers, "get_test_flag")
    resp = await client.get(f"{BASE_URL}/get_test_flag", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "get_test_flag"


@pytest.mark.asyncio
async def test_get_feature_flag_not_found(client, auth_headers) -> None:
    """存在しないフラグは 404"""
    resp = await client.get(f"{BASE_URL}/nonexistent_flag_xyz", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_feature_flag_viewer_can_read(client, viewer_headers) -> None:
    """VIEWER ロールでも取得できる（存在しない場合は 404 が正常）"""
    resp = await client.get(f"{BASE_URL}/nonexistent_flag_xyz", headers=viewer_headers)
    assert resp.status_code == 404


# ── 更新 ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_feature_flag_success(client, auth_headers) -> None:
    """フラグ更新"""
    await _create_flag(client, auth_headers, "update_test_flag", is_enabled=False)
    resp = await client.put(
        f"{BASE_URL}/update_test_flag",
        json={"is_enabled": True, "rollout_percentage": 25.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_enabled"] is True
    assert data["rollout_percentage"] == 25.0


@pytest.mark.asyncio
async def test_update_feature_flag_not_found(client, auth_headers) -> None:
    """存在しないフラグ更新は 404"""
    resp = await client.put(
        f"{BASE_URL}/nonexistent_update_xyz",
        json={"is_enabled": True},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_feature_flag_viewer_forbidden(client, viewer_headers) -> None:
    """VIEWER ロールでの更新は 403"""
    resp = await client.put(
        f"{BASE_URL}/some_flag",
        json={"is_enabled": True},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


# ── 削除 ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_feature_flag_success(client, auth_headers) -> None:
    """フラグ削除"""
    await _create_flag(client, auth_headers, "delete_test_flag")
    resp = await client.delete(f"{BASE_URL}/delete_test_flag", headers=auth_headers)
    assert resp.status_code == 204
    # 削除後は 404
    resp2 = await client.get(f"{BASE_URL}/delete_test_flag", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_feature_flag_not_found(client, auth_headers) -> None:
    """存在しないフラグ削除は 404"""
    resp = await client.delete(
        f"{BASE_URL}/nonexistent_delete_xyz", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_feature_flag_viewer_forbidden(client, viewer_headers) -> None:
    """VIEWER ロールでの削除は 403"""
    resp = await client.delete(f"{BASE_URL}/some_flag", headers=viewer_headers)
    assert resp.status_code == 403


# ── トグル ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_feature_flag_on_to_off(client, auth_headers) -> None:
    """有効フラグを無効化"""
    await _create_flag(client, auth_headers, "toggle_on_flag", is_enabled=True)
    resp = await client.post(
        f"{BASE_URL}/toggle_on_flag/toggle", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False


@pytest.mark.asyncio
async def test_toggle_feature_flag_off_to_on(client, auth_headers) -> None:
    """無効フラグを有効化"""
    resp_create = await client.post(
        BASE_URL,
        json={"name": "toggle_off_flag", "is_enabled": False},
        headers=auth_headers,
    )
    assert resp_create.status_code == 201
    resp = await client.post(
        f"{BASE_URL}/toggle_off_flag/toggle", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_toggle_feature_flag_not_found(client, auth_headers) -> None:
    """存在しないフラグのトグルは 404"""
    resp = await client.post(
        f"{BASE_URL}/nonexistent_toggle_xyz/toggle", headers=auth_headers
    )
    assert resp.status_code == 404


# ── 評価 ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_feature_flag_enabled(client, auth_headers) -> None:
    """有効フラグの評価"""
    await _create_flag(client, auth_headers, "eval_enabled_flag", is_enabled=True)
    resp = await client.get(
        f"{BASE_URL}/eval_enabled_flag/evaluate", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True
    assert data["reason"] == "enabled"


@pytest.mark.asyncio
async def test_evaluate_feature_flag_disabled(client, auth_headers) -> None:
    """無効フラグの評価"""
    resp_create = await client.post(
        BASE_URL,
        json={"name": "eval_disabled_flag", "is_enabled": False},
        headers=auth_headers,
    )
    assert resp_create.status_code == 201
    resp = await client.get(
        f"{BASE_URL}/eval_disabled_flag/evaluate", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False
    assert data["reason"] == "disabled"


@pytest.mark.asyncio
async def test_evaluate_feature_flag_rollout_with_user(client, auth_headers) -> None:
    """ロールアウト 100% では全ユーザーが有効"""
    await _create_flag(
        client,
        auth_headers,
        "eval_rollout_flag",
        is_enabled=True,
        rollout_percentage=100.0,
    )
    resp = await client.get(
        f"{BASE_URL}/eval_rollout_flag/evaluate?user_id=user123",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_evaluate_feature_flag_tenant_mismatch(client, auth_headers) -> None:
    """テナント不一致の評価"""
    tenant_id = str(uuid.uuid4())
    await _create_flag(
        client,
        auth_headers,
        "eval_tenant_flag",
        is_enabled=True,
        tenant_id=tenant_id,
    )
    # 別テナントIDで評価
    other_tenant = str(uuid.uuid4())
    resp = await client.get(
        f"{BASE_URL}/eval_tenant_flag/evaluate?tenant_id={other_tenant}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False
    assert "tenant_mismatch" in data["reason"]


@pytest.mark.asyncio
async def test_evaluate_feature_flag_not_found(client, auth_headers) -> None:
    """存在しないフラグ評価は 404"""
    resp = await client.get(
        f"{BASE_URL}/nonexistent_eval_xyz/evaluate", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_feature_flag_viewer_can_evaluate(
    client, viewer_headers
) -> None:
    """VIEWER でも評価エンドポイントにアクセス可能（404 が正常）"""
    resp = await client.get(
        f"{BASE_URL}/nonexistent_flag/evaluate", headers=viewer_headers
    )
    assert resp.status_code == 404
