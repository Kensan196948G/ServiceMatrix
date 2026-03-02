"""E2Eシナリオ: Incident ライフサイクル全フロー"""
import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_e2e_incident_create_to_close(e2e_client):
    """Incident作成→In_Progress→Resolved→Closed フロー"""
    hdrs = e2e_client._e2e_headers

    # 1. Incident作成
    resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 本番DBサーバー障害", "priority": "P1", "description": "E2E全フロー検証"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "New"
    assert data["incident_number"].startswith("INC-")
    incident_id = data["incident_id"]

    # 2. 作成直後の詳細取得
    get_resp = await e2e_client.get(f"/api/v1/incidents/{incident_id}", headers=hdrs)
    assert get_resp.status_code == 200
    assert get_resp.json()["incident_id"] == incident_id

    # 3. New → In_Progress
    r1 = await e2e_client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"new_status": "In_Progress"},
        headers=hdrs,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "In_Progress"

    # 4. In_Progress → Resolved
    r2 = await e2e_client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"new_status": "Resolved"},
        headers=hdrs,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "Resolved"

    # 5. Resolved → Closed
    r3 = await e2e_client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"new_status": "Closed"},
        headers=hdrs,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "Closed"

    # 6. 最終状態確認
    final = await e2e_client.get(f"/api/v1/incidents/{incident_id}", headers=hdrs)
    assert final.json()["status"] == "Closed"


async def test_e2e_incident_create_and_get_list(e2e_client):
    """複数Incident作成・一覧取得フロー"""
    hdrs = e2e_client._e2e_headers

    # 2件作成
    titles = ["E2E: ネットワーク障害", "E2E: メモリリーク検知"]
    created_ids = []
    for title in titles:
        resp = await e2e_client.post(
            "/api/v1/incidents",
            json={"title": title, "priority": "P2"},
            headers=hdrs,
        )
        assert resp.status_code == 201
        created_ids.append(resp.json()["incident_id"])

    # 一覧取得
    list_resp = await e2e_client.get("/api/v1/incidents", headers=hdrs)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2

    # 作成したIDが含まれることを確認
    ids_in_list = [i["incident_id"] for i in body["items"]]
    for cid in created_ids:
        assert cid in ids_in_list


async def test_e2e_incident_priority_update(e2e_client):
    """Incident優先度変更フロー"""
    hdrs = e2e_client._e2e_headers

    # P3で作成
    create_resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 優先度変更テスト", "priority": "P3"},
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]
    assert create_resp.json()["priority"] == "P3"

    # P1に更新
    patch_resp = await e2e_client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"priority": "P1"},
        headers=hdrs,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["priority"] == "P1"

    # SLAフィールドが設定済みであることを確認
    get_resp = await e2e_client.get(f"/api/v1/incidents/{incident_id}", headers=hdrs)
    assert get_resp.json()["sla_response_due_at"] is not None


async def test_e2e_incident_invalid_transition(e2e_client):
    """不正ステータス遷移のエラーハンドリング"""
    hdrs = e2e_client._e2e_headers

    # Incident作成 (New状態)
    create_resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 不正遷移テスト", "priority": "P2"},
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # New → Closed は不正遷移
    err_resp = await e2e_client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"new_status": "Closed"},
        headers=hdrs,
    )
    assert err_resp.status_code == 422


async def test_e2e_incident_full_lifecycle_with_pending(e2e_client):
    """Incident: New→Acknowledged→In_Progress→Pending→In_Progress→Resolved→Closed"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 保留を含む完全ライフサイクル", "priority": "P2"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    inc_id = resp.json()["incident_id"]

    for new_status, expected in [
        ("Acknowledged", "Acknowledged"),
        ("In_Progress", "In_Progress"),
        ("Pending", "Pending"),
        ("In_Progress", "In_Progress"),
        ("Resolved", "Resolved"),
        ("Closed", "Closed"),
    ]:
        r = await e2e_client.post(
            f"/api/v1/incidents/{inc_id}/transitions",
            json={"new_status": new_status},
            headers=hdrs,
        )
        assert r.status_code == 200, f"{new_status} 遷移失敗: {r.text}"
        assert r.json()["status"] == expected


async def test_e2e_incident_sla_fields_on_p1(e2e_client):
    """P1 Incident作成時にSLAフィールドが設定される"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: SLAフィールド確認", "priority": "P1"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sla_response_due_at"] is not None
    assert data["sla_resolution_due_at"] is not None
    assert data["sla_breached"] is False


async def test_e2e_incident_not_found(e2e_client):
    """存在しないIncidentへのアクセスは404"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.get(f"/api/v1/incidents/{uuid.uuid4()}", headers=hdrs)
    assert resp.status_code == 404


async def test_e2e_incident_status_filter(e2e_client):
    """ステータスフィルタで絞り込み取得できる"""
    hdrs = e2e_client._e2e_headers

    # In_Progress 状態のIncidentを作成
    cr = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: フィルタテスト用", "priority": "P3"},
        headers=hdrs,
    )
    assert cr.status_code == 201
    inc_id = cr.json()["incident_id"]

    await e2e_client.post(
        f"/api/v1/incidents/{inc_id}/transitions",
        json={"new_status": "In_Progress"},
        headers=hdrs,
    )

    # In_Progress フィルタ
    list_resp = await e2e_client.get(
        "/api/v1/incidents?status=In_Progress", headers=hdrs
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert all(i["status"] == "In_Progress" for i in items)
    ids = [i["incident_id"] for i in items]
    assert inc_id in ids


async def test_e2e_incident_unauthorized(e2e_client):
    """認証なしのアクセスは401"""
    resp = await e2e_client.get("/api/v1/incidents")
    assert resp.status_code == 401
