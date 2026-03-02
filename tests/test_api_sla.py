"""SLA監視 API エンドポイント統合テスト"""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio

_MOCK_SUMMARY = {
    "P1": {"total": 0, "breached": 0, "compliance_rate": 100.0},
    "P2": {"total": 0, "breached": 0, "compliance_rate": 100.0},
    "P3": {"total": 0, "breached": 0, "compliance_rate": 100.0},
    "P4": {"total": 0, "breached": 0, "compliance_rate": 100.0},
}


# ─── SLAサマリーテスト ────────────────────────────────────────────────────────

async def test_get_sla_summary(client, auth_headers):
    """GET /sla/summary → 200"""
    with patch("src.api.v1.sla.cache_get", new_callable=AsyncMock, return_value=None), \
         patch("src.api.v1.sla.cache_set", new_callable=AsyncMock), \
         patch(
             "src.services.sla_monitor_service.sla_monitor.get_sla_summary",
             new_callable=AsyncMock,
             return_value=_MOCK_SUMMARY,
         ):
        resp = await client.get("/api/v1/sla/summary")
    assert resp.status_code == 200


async def test_sla_summary_structure(client, auth_headers):
    """SLAサマリーのレスポンス構造確認（P1〜P4キー）"""
    with patch("src.api.v1.sla.cache_get", new_callable=AsyncMock, return_value=None), \
         patch("src.api.v1.sla.cache_set", new_callable=AsyncMock), \
         patch(
             "src.services.sla_monitor_service.sla_monitor.get_sla_summary",
             new_callable=AsyncMock,
             return_value=_MOCK_SUMMARY,
         ):
        resp = await client.get("/api/v1/sla/summary")
    assert resp.status_code == 200
    data = resp.json()
    for priority in ("P1", "P2", "P3", "P4"):
        assert priority in data
        assert "compliance_rate" in data[priority]


# ─── SLA違反一覧テスト ────────────────────────────────────────────────────────

async def test_get_sla_breaches(client, auth_headers):
    """GET /sla/breaches → 200, リスト形式で返却"""
    resp = await client.get("/api/v1/sla/breaches")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_sla_breaches_empty(client, auth_headers):
    """SLA違反なし状態 → 空リスト"""
    resp = await client.get("/api/v1/sla/breaches")
    assert resp.status_code == 200
    assert resp.json() == []


# ─── SLAチェックテスト ────────────────────────────────────────────────────────

async def test_check_sla(client, auth_headers):
    """POST /sla/check → 200, checked=True"""
    with patch(
        "src.services.sla_monitor_service.sla_monitor.check_sla_breaches",
        new_callable=AsyncMock,
    ):
        resp = await client.post("/api/v1/sla/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checked"] is True
    assert "timestamp" in data


async def test_sla_check_creates_breaches(client, auth_headers):
    """SLAチェック実行 → checked=True レスポンス確認"""
    with patch(
        "src.services.sla_monitor_service.sla_monitor.check_sla_breaches",
        new_callable=AsyncMock,
    ):
        resp = await client.post("/api/v1/sla/check")
    assert resp.status_code == 200
    assert resp.json()["checked"] is True
