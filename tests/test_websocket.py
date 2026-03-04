"""WebSocket リアルタイム通知 テスト"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

pytestmark = pytest.mark.asyncio


def test_websocket_connection_count_initial():
    """ConnectionManager の初期接続数が0"""
    from src.services.ws_manager import ConnectionManager

    mgr = ConnectionManager()
    assert mgr.connection_count == 0


def test_websocket_connect_notifications():
    """WebSocket /ws/notifications に接続できる"""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/notifications") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert "connections" in data


def test_websocket_ping_pong():
    """ping送信でpongが返る"""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/notifications") as ws:
        ws.receive_json()  # connected message
        ws.send_json({"type": "ping"})
        resp = ws.receive_json()
        assert resp["type"] == "pong"


def test_websocket_incidents_channel():
    """インシデントチャンネルに接続できる"""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/incidents") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert data["channel"] == "incidents"


def test_websocket_broadcast():
    """2クライアント接続時にブロードキャストが届く"""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/notifications") as ws1:
        ws1.receive_json()  # connected
        with client.websocket_connect("/api/v1/ws/notifications") as ws2:
            ws2.receive_json()  # connected
            ws1.send_json({"type": "message", "text": "hello"})
            # ブロードキャストメッセージ受信
            msg1 = ws1.receive_json()
            assert msg1["type"] == "notification"


def test_connection_manager_disconnect():
    """ConnectionManager.disconnect が正常動作"""
    from src.services.ws_manager import ConnectionManager

    mgr = ConnectionManager()
    # 空リストへのdisconnect は例外を出さない
    mgr.disconnect(None)  # type: ignore[arg-type]
    assert mgr.connection_count == 0


def test_websocket_manager_singleton():
    """manager シングルトンが存在する"""
    from src.services.ws_manager import manager

    assert manager is not None
    assert hasattr(manager, "active_connections")
    assert hasattr(manager, "broadcast")


async def test_manager_broadcast_empty():
    """接続なし時のブロードキャストは例外を出さない"""
    from src.services.ws_manager import ConnectionManager

    mgr = ConnectionManager()
    await mgr.broadcast({"type": "test"})  # should not raise


async def test_manager_send_personal_message():
    """send_personal_message はWebSocketのsend_jsonを呼ぶ"""
    from unittest.mock import AsyncMock

    from src.services.ws_manager import ConnectionManager

    mgr = ConnectionManager()
    mock_ws = AsyncMock()
    await mgr.send_personal_message({"type": "test"}, mock_ws)
    mock_ws.send_json.assert_called_once_with({"type": "test"})


def test_websocket_notification_message():
    """通常メッセージがブロードキャストされる"""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/notifications") as ws:
        ws.receive_json()  # connected
        ws.send_json({"type": "alert", "text": "SLA breach"})
        msg = ws.receive_json()
        assert msg["type"] == "notification"
        assert msg["data"]["type"] == "alert"
