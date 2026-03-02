"""E2Eシナリオ: Change 承認・ライフサイクル全フロー"""
import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_e2e_change_create_to_approve(e2e_client):
    """Change作成→Draft→Submitted→CAB_Review→Approved→Scheduled→In_Progress→Completed"""
    hdrs = e2e_client._e2e_headers

    # 1. Change作成
    resp = await e2e_client.post(
        "/api/v1/changes",
        json={
            "title": "E2E: Webサーバー設定変更",
            "change_type": "Normal",
            "impact_level": "Medium",
            "urgency_level": "Low",
            "implementation_plan": "設定ファイル更新後に再起動",
            "rollback_plan": "バックアップから復元",
        },
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "Draft"
    assert data["change_number"].startswith("CHG-")
    change_id = data["change_id"]

    # 2. Draft → Submitted
    r1 = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Submitted"},
        headers=hdrs,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "Submitted"

    # 3. Submitted → CAB_Review
    r2 = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "CAB_Review"},
        headers=hdrs,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "CAB_Review"

    # 4. CAB承認
    cab = await e2e_client.post(
        f"/api/v1/changes/{change_id}/cab-approval",
        json={"approved": True, "notes": "問題なし。承認する。"},
        headers=hdrs,
    )
    assert cab.status_code == 200
    assert cab.json()["status"] == "Approved"

    # 5. Approved → Scheduled
    r3 = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Scheduled"},
        headers=hdrs,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "Scheduled"

    # 6. Scheduled → In_Progress
    r4 = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "In_Progress"},
        headers=hdrs,
    )
    assert r4.status_code == 200
    assert r4.json()["status"] == "In_Progress"

    # 7. In_Progress → Completed
    r5 = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Completed"},
        headers=hdrs,
    )
    assert r5.status_code == 200
    assert r5.json()["status"] == "Completed"

    # 8. 最終状態確認
    final = await e2e_client.get(f"/api/v1/changes/{change_id}", headers=hdrs)
    assert final.json()["status"] == "Completed"


async def test_e2e_change_risk_score(e2e_client):
    """リスクスコア計算確認: High/High で高スコア"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.post(
        "/api/v1/changes",
        json={
            "title": "E2E: 高リスク変更",
            "change_type": "Emergency",
            "impact_level": "High",
            "urgency_level": "High",
        },
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_level"] is not None

    # Low/Low の場合と比較
    resp_low = await e2e_client.post(
        "/api/v1/changes",
        json={
            "title": "E2E: 低リスク変更",
            "change_type": "Standard",
            "impact_level": "Low",
            "urgency_level": "Low",
        },
        headers=hdrs,
    )
    assert resp_low.status_code == 201
    data_low = resp_low.json()
    assert data["risk_score"] >= data_low["risk_score"]


async def test_e2e_change_rejected_flow(e2e_client):
    """Change却下フロー: Draft→Submitted→CAB_Review→Rejected→Draft"""
    hdrs = e2e_client._e2e_headers

    # Change作成
    resp = await e2e_client.post(
        "/api/v1/changes",
        json={"title": "E2E: 却下フローテスト", "change_type": "Normal"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    change_id = resp.json()["change_id"]

    # Draft → Submitted
    await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Submitted"},
        headers=hdrs,
    )

    # Submitted → CAB_Review
    await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "CAB_Review"},
        headers=hdrs,
    )

    # CAB却下
    cab = await e2e_client.post(
        f"/api/v1/changes/{change_id}/cab-approval",
        json={"approved": False, "notes": "リスクが高すぎる"},
        headers=hdrs,
    )
    assert cab.status_code == 200
    assert cab.json()["status"] == "Rejected"

    # Rejected → Draft (再申請)
    r = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Draft"},
        headers=hdrs,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "Draft"


async def test_e2e_change_create_and_list(e2e_client):
    """複数Change作成・一覧取得フロー"""
    hdrs = e2e_client._e2e_headers

    # 3件作成
    titles = ["E2E: 変更A", "E2E: 変更B", "E2E: 変更C"]
    created_ids = []
    for title in titles:
        resp = await e2e_client.post(
            "/api/v1/changes",
            json={"title": title, "change_type": "Standard"},
            headers=hdrs,
        )
        assert resp.status_code == 201
        created_ids.append(resp.json()["change_id"])

    # 一覧取得
    list_resp = await e2e_client.get("/api/v1/changes", headers=hdrs)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "items" in body
    assert body["total"] >= 3

    ids_in_list = [i["change_id"] for i in body["items"]]
    for cid in created_ids:
        assert cid in ids_in_list


async def test_e2e_change_invalid_transition(e2e_client):
    """不正ステータス遷移のエラーハンドリング"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.post(
        "/api/v1/changes",
        json={"title": "E2E: 不正遷移テスト", "change_type": "Normal"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    change_id = resp.json()["change_id"]

    # Draft → Completed は不正
    err = await e2e_client.post(
        f"/api/v1/changes/{change_id}/transitions",
        json={"new_status": "Completed"},
        headers=hdrs,
    )
    assert err.status_code == 422


async def test_e2e_change_not_found(e2e_client):
    """存在しないChangeへのアクセスは404"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.get(f"/api/v1/changes/{uuid.uuid4()}", headers=hdrs)
    assert resp.status_code == 404
