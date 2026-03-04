"""パフォーマンスベースラインテスト（応答時間の基準値確認）"""
import time

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check_response_time(client):
    """ヘルスチェックは500ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/health")
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 500


async def test_list_incidents_response_time(client, auth_headers):
    """インシデント一覧は2000ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/incidents", headers=auth_headers)
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 2000


async def test_list_changes_response_time(client, auth_headers):
    """変更一覧は2000ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/changes", headers=auth_headers)
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 2000


async def test_sla_summary_response_time(client):
    """SLAサマリーは2000ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/sla/summary")
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 2000


async def test_websocket_stats_response_time(client):
    """WebSocket統計は500ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/ws/stats")
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 500


async def test_ai_decisions_response_time(client, auth_headers):
    """AI決定ログ一覧は2000ms以内に応答"""
    start = time.monotonic()
    resp = await client.get("/api/v1/ai/decisions", headers=auth_headers)
    duration_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert duration_ms < 2000
