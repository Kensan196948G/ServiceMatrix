"""外部統合設定 API エンドポイント統合テスト"""
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
        username=f"integ_admin_{uid.hex[:8]}",
        email=f"integ_{uid.hex[:8]}@test.com",
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

BASE = "/api/v1/integrations"


def _integration_payload(**kwargs):
    defaults = {
        "integration_type": "jira",
        "name": "Test Jira",
        "base_url": "https://jira.example.com",
        "is_active": True,
    }
    defaults.update(kwargs)
    return defaults


# ─── 一覧 ────────────────────────────────────────────────────────────────────

async def test_list_integrations(client, auth_headers):
    """GET /integrations → 200, リスト"""
    resp = await client.get(BASE, headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_integrations_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(BASE)
    assert resp.status_code == 401


# ─── 作成 ────────────────────────────────────────────────────────────────────

async def test_create_integration_success(client, auth_headers):
    """POST /integrations → 201"""
    resp = await client.post(BASE, json=_integration_payload(), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Jira"
    assert "config_id" in data


async def test_create_integration_servicenow(client, auth_headers):
    """POST /integrations ServiceNow → 201"""
    resp = await client.post(
        BASE,
        json=_integration_payload(integration_type="servicenow", name="ServiceNow Test"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["integration_type"] == "servicenow"


async def test_create_integration_missing_required(client, auth_headers):
    """必須フィールドなし → 422"""
    resp = await client.post(BASE, json={"base_url": "https://x.com"}, headers=auth_headers)
    assert resp.status_code == 422


# ─── 更新 ────────────────────────────────────────────────────────────────────

async def test_update_integration_success(client, auth_headers):
    """PATCH /{id} → 200, 名前が更新される"""
    create_resp = await client.post(BASE, json=_integration_payload(name="Before"), headers=auth_headers)
    assert create_resp.status_code == 201
    config_id = create_resp.json()["config_id"]

    update_resp = await client.patch(
        f"{BASE}/{config_id}",
        json={"name": "After"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "After"


async def test_update_integration_not_found(client, auth_headers):
    """存在しないID → 404"""
    resp = await client.patch(
        f"{BASE}/{uuid.uuid4()}",
        json={"name": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── 削除 ────────────────────────────────────────────────────────────────────

async def test_delete_integration_success(client, auth_headers):
    """DELETE /{id} → 204"""
    create_resp = await client.post(BASE, json=_integration_payload(name="ToDelete"), headers=auth_headers)
    assert create_resp.status_code == 201
    config_id = create_resp.json()["config_id"]

    del_resp = await client.delete(f"{BASE}/{config_id}", headers=auth_headers)
    assert del_resp.status_code == 204


async def test_delete_integration_not_found(client, auth_headers):
    """存在しないID → 404"""
    resp = await client.delete(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── 接続テスト & 同期ログ ───────────────────────────────────────────────────

async def test_test_integration(client, auth_headers):
    """POST /{id}/test → 200, success=True"""
    create_resp = await client.post(BASE, json=_integration_payload(), headers=auth_headers)
    config_id = create_resp.json()["config_id"]

    resp = await client.post(f"{BASE}/{config_id}/test", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_integration_not_found(client, auth_headers):
    """存在しないIDの接続テスト → 404"""
    resp = await client.post(f"{BASE}/{uuid.uuid4()}/test", headers=auth_headers)
    assert resp.status_code == 404


async def test_get_sync_log(client, auth_headers):
    """GET /{id}/sync-log → 200, リスト"""
    create_resp = await client.post(BASE, json=_integration_payload(), headers=auth_headers)
    config_id = create_resp.json()["config_id"]

    resp = await client.get(f"{BASE}/{config_id}/sync-log", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── Webhook ─────────────────────────────────────────────────────────────────

async def test_webhook_jira_issue_created(client, auth_headers):
    """POST /webhook/jira → 200, Incident作成"""
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "JIRA-123",
            "fields": {"summary": "Test Issue from Jira", "description": "desc"},
        },
    }
    resp = await client.post(f"{BASE}/webhook/jira", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert "incident_id" in data


async def test_webhook_jira_unknown_event(client, auth_headers):
    """未知のイベント → skipped=True"""
    resp = await client.post(
        f"{BASE}/webhook/jira",
        json={"webhookEvent": "unknown_event"},
    )
    assert resp.status_code == 200
    assert resp.json().get("skipped") is True


async def test_webhook_servicenow_incident_created(client, auth_headers):
    """POST /webhook/servicenow → 200, Incident作成"""
    payload = {
        "event": "incident_created",
        "record": {
            "sys_id": "abc12345",
            "short_description": "ServiceNow incident",
            "description": "details",
        },
    }
    resp = await client.post(f"{BASE}/webhook/servicenow", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert "incident_id" in data


async def test_webhook_servicenow_skipped(client, auth_headers):
    """未知のイベント → skipped=True"""
    resp = await client.post(
        f"{BASE}/webhook/servicenow",
        json={"event": "other_event"},
    )
    assert resp.status_code == 200
    assert resp.json().get("skipped") is True
