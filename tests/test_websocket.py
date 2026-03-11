"""WebSocket通知マネージャー・エンドポイントのテスト"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import WebSocketDisconnect

from src.services.notification_manager import ConnectionManager
from src.api.v1.websocket import websocket_endpoint
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


# ─── websocket_endpoint 単体テスト ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_websocket_endpoint_invalid_channel():
    """無効なチャンネル指定 → 4004 でクローズ"""
    ws = AsyncMock()
    await websocket_endpoint(ws, "invalid_channel", "some_token")
    ws.close.assert_called_once_with(code=4004)


@pytest.mark.asyncio
async def test_websocket_endpoint_invalid_token():
    """無効な JWT → 4001 でクローズ"""
    ws = AsyncMock()
    with patch("src.api.v1.websocket.decode_token", side_effect=Exception("bad token")):
        await websocket_endpoint(ws, "incidents", "bad_jwt")
    ws.close.assert_called_once_with(code=4001)


@pytest.mark.asyncio
async def test_websocket_endpoint_client_ping_pong():
    """クライアントから ping を受信してサーバーが pong を返す"""
    ws = AsyncMock()
    calls = [0]

    async def mock_wait_for(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        calls[0] += 1
        if calls[0] == 1:
            return "ping"
        raise WebSocketDisconnect()

    with patch("src.api.v1.websocket.decode_token", return_value={"sub": "user1"}):
        with patch("src.api.v1.websocket.asyncio.wait_for", new=mock_wait_for):
            await websocket_endpoint(ws, "incidents", "valid_token")

    ws.accept.assert_called_once()
    ws.send_text.assert_any_call("pong")


@pytest.mark.asyncio
async def test_websocket_endpoint_server_keepalive_ping():
    """タイムアウト時にサーバーが keepalive ping を送信する"""
    ws = AsyncMock()
    calls = [0]

    async def mock_wait_for(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        calls[0] += 1
        if calls[0] == 1:
            raise TimeoutError()
        raise WebSocketDisconnect()

    with patch("src.api.v1.websocket.decode_token", return_value={"sub": "user1"}):
        with patch("src.api.v1.websocket.asyncio.wait_for", new=mock_wait_for):
            await websocket_endpoint(ws, "changes", "valid_token")

    ws.send_text.assert_any_call('{"type":"ping"}')


@pytest.mark.asyncio
async def test_websocket_endpoint_disconnect_calls_manager_disconnect():
    """WebSocketDisconnect 時に manager.disconnect が呼ばれる"""
    ws = AsyncMock()

    async def mock_wait_for(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        raise WebSocketDisconnect()

    with patch("src.api.v1.websocket.decode_token", return_value={"sub": "user1"}):
        with patch("src.api.v1.websocket.asyncio.wait_for", new=mock_wait_for):
            with patch("src.api.v1.websocket.manager") as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = MagicMock()
                await websocket_endpoint(ws, "sla_alerts", "valid_token")
                mock_manager.disconnect.assert_called_once_with(ws, "sla_alerts")


@pytest.mark.asyncio
async def test_websocket_endpoint_exception_handled_gracefully():
    """接続中の予期しない例外が警告ログ後に正常終了する"""
    ws = AsyncMock()

    async def mock_wait_for(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        raise RuntimeError("unexpected network error")

    with patch("src.api.v1.websocket.decode_token", return_value={"sub": "user1"}):
        with patch("src.api.v1.websocket.asyncio.wait_for", new=mock_wait_for):
            with patch("src.api.v1.websocket.manager") as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = MagicMock()
                # 例外が外部に伝播しないこと
                await websocket_endpoint(ws, "all", "valid_token")
                mock_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_endpoint_all_valid_channels():
    """VALID_CHANNELS のすべてのチャンネルで接続できる"""
    from src.services.notification_manager import VALID_CHANNELS

    for channel in VALID_CHANNELS:
        ws = AsyncMock()

        async def mock_wait_for(coro, timeout):
            try:
                coro.close()
            except Exception:
                pass
            raise WebSocketDisconnect()

        with patch("src.api.v1.websocket.decode_token", return_value={"sub": "user1"}):
            with patch("src.api.v1.websocket.asyncio.wait_for", new=mock_wait_for):
                await websocket_endpoint(ws, channel, "valid_token")

        ws.accept.assert_called_once()
        # close は呼ばれないこと（正常接続のため）
        ws.close.assert_not_called()
