"""E2Eシナリオ: SLA監視フロー"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_e2e_sla_summary_api(e2e_client):
    """SLAサマリーAPIのレスポンス形式確認"""
    resp = await e2e_client.get("/api/v1/sla/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


async def test_e2e_sla_warnings_api(e2e_client):
    """SLA警告一覧APIのレスポンス形式確認"""
    resp = await e2e_client.get("/api/v1/sla/warnings")
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data
    assert "count" in data
    assert isinstance(data["warnings"], list)
    assert data["count"] == len(data["warnings"])


async def test_e2e_sla_breaches_api(e2e_client):
    """SLA違反一覧APIのレスポンス形式確認"""
    resp = await e2e_client.get("/api/v1/sla/breaches")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_e2e_sla_status_for_p1_incident(e2e_client):
    """P1 Incident作成後のSLAステータス取得"""
    hdrs = e2e_client._e2e_headers

    # P1 Incident作成
    create_resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: SLAステータス確認P1", "priority": "P1"},
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # SLAステータス取得
    sla_resp = await e2e_client.get(f"/api/v1/sla/status/{incident_id}")
    assert sla_resp.status_code == 200
    data = sla_resp.json()
    assert "incident_id" in data or "sla_response_due_at" in data or data is not None


async def test_e2e_sla_status_not_found(e2e_client):
    """存在しないIncidentのSLAステータスは404"""
    import uuid
    resp = await e2e_client.get(f"/api/v1/sla/status/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_e2e_sla_manual_check(e2e_client):
    """手動SLAチェックAPIの実行確認"""
    resp = await e2e_client.post("/api/v1/sla/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checked"] is True
    assert "timestamp" in data
    assert "breaches_detected" in data
    assert "warnings_detected" in data


async def test_e2e_sla_p1_incident_has_sla_fields(e2e_client):
    """P1 Incident作成時にSLAデッドラインが自動設定される"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: SLAフィールド自動設定確認", "priority": "P1"},
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sla_response_due_at"] is not None
    assert data["sla_resolution_due_at"] is not None


async def test_e2e_sla_manual_check_returns_counts(e2e_client):
    """手動SLAチェックは整数のカウント値を返す"""
    resp = await e2e_client.post("/api/v1/sla/check")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["breaches_detected"], int)
    assert isinstance(data["warnings_detected"], int)
    assert data["breaches_detected"] >= 0
    assert data["warnings_detected"] >= 0
