"""WebSocket通知マネージャー・エンドポイントのテスト"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from src.services.notification_manager import ConnectionManager
from src.main import app


# ─── ConnectionManager 単体テスト ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_adds_to_channel():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws, "incidents")
    assert ws in mgr.active_connections["incidents"]
    ws.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_default_channel_is_all():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws)
    assert ws in mgr.active_connections["all"]


@pytest.mark.asyncio
async def test_disconnect_removes_from_channel():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws, "incidents")
    mgr.disconnect(ws, "incidents")
    assert ws not in mgr.active_connections.get("incidents", [])


@pytest.mark.asyncio
async def test_disconnect_unknown_socket_is_noop():
    mgr = ConnectionManager()
    ws = AsyncMock()
    # disconnecting ws that was never connected should not raise
    mgr.disconnect(ws, "incidents")


@pytest.mark.asyncio
async def test_broadcast_sends_to_channel_and_all():
    mgr = ConnectionManager()
    ws_incidents = AsyncMock()
    ws_all = AsyncMock()
    await mgr.connect(ws_incidents, "incidents")
    await mgr.connect(ws_all, "all")

    await mgr.broadcast({"type": "test", "msg": "hello"}, channel="incidents")

    ws_incidents.send_text.assert_called_once()
    ws_all.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections():
    mgr = ConnectionManager()
    ws_dead = AsyncMock()
    ws_dead.send_text.side_effect = Exception("connection closed")
    await mgr.connect(ws_dead, "incidents")

    await mgr.broadcast({"type": "test"}, channel="incidents")

    assert ws_dead not in mgr.active_connections.get("incidents", [])


@pytest.mark.asyncio
async def test_broadcast_incident_update():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws, "all")

    await mgr.broadcast_incident_update("inc-123", "created", {"status": "New"})

    ws.send_text.assert_called_once()
    import json
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload["type"] == "incident_update"
    assert payload["action"] == "created"
    assert payload["incident_id"] == "inc-123"


@pytest.mark.asyncio
async def test_broadcast_sla_alert():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws, "all")

    await mgr.broadcast_sla_alert("inc-456", "warning")

    ws.send_text.assert_called_once()
    import json
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload["type"] == "sla_alert"
    assert payload["warning_level"] == "warning"
    assert payload["incident_id"] == "inc-456"


@pytest.mark.asyncio
async def test_stats_returns_counts():
    mgr = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await mgr.connect(ws1, "incidents")
    await mgr.connect(ws2, "incidents")

    s = mgr.stats()
    assert s["total"] == 2
    assert s["channels"]["incidents"] == 2


# ─── WebSocket stats エンドポイント (HTTP) ──────────────────────────────────

@pytest.mark.asyncio
async def test_ws_stats_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ws/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "channels" in data
