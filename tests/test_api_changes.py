"""変更管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_change_seq():
    """func.nextval('change_seq') の代替（SQLite非対応のためモック）"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"CHG-2024-{_counter[0]:06d}"

    with patch("src.services.change_service._get_next_change_number", _get_next):
        yield


# ─── 作成テスト ──────────────────────────────────────────────────────────────

async def test_create_change_success(client, auth_headers):
    """POST /changes → 201, change_number が CHG- プレフィックスを持つ"""
    resp = await client.post(
        "/api/v1/changes",
        json={
            "title": "Webサーバー設定変更",
            "change_type": "Normal",
            "impact_level": "Medium",
            "urgency_level": "Low",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["change_number"].startswith("CHG-")
    assert data["title"] == "Webサーバー設定変更"
    assert data["status"] == "Draft"


async def test_create_change_missing_required(client, auth_headers):
    """必須フィールド title なし → 422"""
    resp = await client.post(
        "/api/v1/changes",
        json={"change_type": "Normal"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ─── 一覧・詳細取得テスト ────────────────────────────────────────────────────

async def test_list_changes_empty(client, auth_headers):
    """GET /changes → 200, レスポンス構造を確認"""
    resp = await client.get("/api/v1/changes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


async def test_get_change_not_found(client, auth_headers):
    """存在しない UUID → 404"""
    resp = await client.get(f"/api/v1/changes/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── リスクスコアテスト ──────────────────────────────────────────────────────

async def test_change_risk_score_calculated(client, auth_headers):
    """変更作成時に risk_score が 0–100 の範囲で自動計算される"""
    resp = await client.post(
        "/api/v1/changes",
        json={
            "title": "リスクスコアテスト",
            "change_type": "Emergency",
            "impact_level": "High",
            "urgency_level": "High",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_level"] is not None


# ─── ステータス遷移テスト ────────────────────────────────────────────────────

async def test_change_status_transition(client, auth_headers):
    """Draft → Submitted ステータス遷移"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "Draft→Submitted テスト", "change_type": "Standard"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    trans_resp = await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Submitted"},
        headers=auth_headers,
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "Submitted"


async def test_change_cab_approval(client, auth_headers):
    """CAB 承認フロー: Draft → Submitted → CAB_Review → Approved"""
    # Draft で作成
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "CAB承認テスト", "change_type": "Normal"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    # Draft → Submitted
    r1 = await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Submitted"},
        headers=auth_headers,
    )
    assert r1.status_code == 200

    # Submitted → CAB_Review
    r2 = await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "CAB_Review"},
        headers=auth_headers,
    )
    assert r2.status_code == 200

    # CAB 承認
    cab_resp = await client.post(
        f"/api/v1/changes/{change_id}/cab-approval",
        json={"approved": True, "notes": "問題なし"},
        headers=auth_headers,
    )
    assert cab_resp.status_code == 200
    assert cab_resp.json()["status"] == "Approved"


# ─── 認証テスト ──────────────────────────────────────────────────────────────

async def test_unauthorized_change(client):
    """認証ヘッダーなし → 401"""
    resp = await client.get("/api/v1/changes")
    assert resp.status_code == 401
