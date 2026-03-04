"""レポートAPI テスト"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_reports_stats(client, auth_headers):
    """月次KPI統計取得テスト"""
    resp = await client.get(
        "/api/v1/reports/stats",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "incidents" in data
    assert "mttr_hours" in data
    assert "sla_compliance_rate" in data
    assert "changes" in data


async def test_reports_stats_with_year_month(client, auth_headers):
    """年月指定での統計取得"""
    resp = await client.get(
        "/api/v1/reports/stats?year=2024&month=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"]["year"] == 2024
    assert data["period"]["month"] == 1


async def test_reports_stats_no_auth(client):
    """認証なしでの統計取得 → 401"""
    resp = await client.get("/api/v1/reports/stats")
    assert resp.status_code == 401


async def test_reports_resolution_distribution(client, auth_headers):
    """解決時間分布取得テスト"""
    resp = await client.get(
        "/api/v1/reports/incident-resolution-distribution",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "buckets" in data
    assert len(data["buckets"]) == 5


async def test_reports_resolution_distribution_with_year_month(client, auth_headers):
    """年月指定での解決時間分布取得"""
    resp = await client.get(
        "/api/v1/reports/incident-resolution-distribution?year=2024&month=6",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"]["year"] == 2024
    assert data["period"]["month"] == 6


async def test_reports_monthly_summary(client, auth_headers):
    """月次サマリ取得テスト"""
    resp = await client.get(
        "/api/v1/reports/monthly-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "incidents" in data
    assert "resolution_distribution" in data
    assert len(data["resolution_distribution"]) == 5


async def test_reports_monthly_summary_with_params(client, auth_headers):
    """年月指定の月次サマリ"""
    resp = await client.get(
        "/api/v1/reports/monthly-summary?year=2025&month=3",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"]["year"] == 2025
    assert data["period"]["month"] == 3


async def test_reports_stats_top_services_format(client, auth_headers):
    """topサービス構造確認"""
    resp = await client.get(
        "/api/v1/reports/stats",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "top_affected_services" in data
    assert isinstance(data["top_affected_services"], list)
