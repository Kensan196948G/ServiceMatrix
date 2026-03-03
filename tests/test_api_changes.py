"""変更管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

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


# ─── 詳細取得(成功)テスト ─────────────────────────────────────────────────────

async def test_get_change_success(client, auth_headers):
    """GET /changes/{id} → 200, 作成した変更が取得できる"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "詳細取得テスト", "change_type": "Standard"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    resp = await client.get(f"/api/v1/changes/{change_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_id"] == change_id
    assert data["title"] == "詳細取得テスト"


# ─── 更新テスト ──────────────────────────────────────────────────────────────

async def test_update_change_success(client, auth_headers):
    """PATCH /changes/{id} → 200, フィールド更新確認"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "更新テスト変更", "change_type": "Normal"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    update_resp = await client.patch(
        f"/api/v1/changes/{change_id}",
        json={"description": "更新されたdescription", "impact_level": "High"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["description"] == "更新されたdescription"
    assert data["impact_level"] == "High"


async def test_update_change_not_found(client, auth_headers):
    """存在しないIDの更新 → 404"""
    import uuid
    resp = await client.patch(
        f"/api/v1/changes/{uuid.uuid4()}",
        json={"description": "更新"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── ステータス遷移失敗テスト ────────────────────────────────────────────────

async def test_change_invalid_transition(client, auth_headers):
    """無効なステータス遷移 → 422"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "無効遷移テスト", "change_type": "Normal"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    # Draft → Approved は無効
    resp = await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Approved"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_transition_change_not_found(client, auth_headers):
    """存在しないIDの遷移 → 404"""
    import uuid
    resp = await client.post(
        f"/api/v1/changes/{uuid.uuid4()}/transitions",
        json={"new_status": "Submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── CAB承認失敗テスト ───────────────────────────────────────────────────────

async def test_cab_approval_not_in_review(client, auth_headers):
    """CAB_Review以外でのCAB承認 → 422"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "CABエラーテスト", "change_type": "Normal"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    # Draft状態でCAB承認は無効
    resp = await client.post(
        f"/api/v1/changes/{change_id}/cab-approval",
        json={"approved": True},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_cab_rejection(client, auth_headers):
    """CAB却下フロー: Draft → Submitted → CAB_Review → Rejected"""
    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "CAB却下テスト", "change_type": "Normal"},
        headers=auth_headers,
    )
    change_id = create_resp.json()["change_id"]

    await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Submitted"}, headers=auth_headers,
    )
    await client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "CAB_Review"}, headers=auth_headers,
    )

    cab_resp = await client.post(
        f"/api/v1/changes/{change_id}/cab-approval",
        json={"approved": False, "notes": "リスクが高い"},
        headers=auth_headers,
    )
    assert cab_resp.status_code == 200
    assert cab_resp.json()["status"] == "Rejected"


async def test_cab_approval_not_found(client, auth_headers):
    """存在しないIDのCAB承認 → 404"""
    import uuid
    resp = await client.post(
        f"/api/v1/changes/{uuid.uuid4()}/cab-approval",
        json={"approved": True},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── 一覧フィルタテスト ─────────────────────────────────────────────────────

async def test_list_changes_with_status_filter(client, auth_headers):
    """GET /changes?status=Draft → statusフィルタ確認"""
    await client.post(
        "/api/v1/changes",
        json={"title": "フィルタテスト", "change_type": "Standard"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/changes?status=Draft", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["status"] == "Draft"


# ─── リスク自動評価エンドポイントテスト ──────────────────────────────────────

async def test_risk_assessment_endpoint(client, auth_headers):
    """POST /changes/{id}/risk-assessment → 200"""
    from src.services.change_risk_service import RiskAssessmentResult

    create_resp = await client.post(
        "/api/v1/changes",
        json={"title": "リスク評価テスト", "change_type": "Emergency", "impact_level": "High"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    mock_result = RiskAssessmentResult(
        change_id=change_id,
        total_score=75,
        risk_level="High",
        factors=[],
        recommendations=["テスト推奨事項"],
        maintenance_window_required=True,
    )

    with patch(
        "src.api.v1.changes.change_risk_service.assess_risk",
        new=AsyncMock(return_value=mock_result),
    ):
        resp = await client.post(
            f"/api/v1/changes/{change_id}/risk-assessment",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_score" in data
    assert "risk_level" in data
    assert "factors" in data


async def test_risk_assessment_not_found(client, auth_headers):
    """存在しないIDのリスク評価 → 404"""
    import uuid
    resp = await client.post(
        f"/api/v1/changes/{uuid.uuid4()}/risk-assessment",
        headers=auth_headers,
    )
    assert resp.status_code == 404
