"""ヘルスチェック・メトリクス テスト"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    """GET /health → 200"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database" in data


async def test_health_check_db_ok(client):
    """DB接続OK → status=ok"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "ok"


async def test_detailed_health(client):
    """GET /health/detailed → 200"""
    resp = await client.get("/api/v1/health/detailed")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data
    assert "database" in data["services"]


async def test_metrics_json(client):
    """GET /metrics → 200"""
    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200


async def test_metrics_prometheus(client):
    """GET /metrics/prometheus → 200 text/plain"""
    resp = await client.get("/api/v1/metrics/prometheus")
    assert resp.status_code == 200
