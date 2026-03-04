"""WebSocket APIエンドポイント - リアルタイム通知"""

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.logging import get_logger
from src.core.security import decode_token
from src.services.notification_manager import VALID_CHANNELS, manager

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

KEEPALIVE_INTERVAL = 30  # seconds


@router.websocket("/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """チャンネル購読 WebSocket エンドポイント。
    channel: incidents | changes | sla_alerts | all
    """
    if channel not in VALID_CHANNELS:
        await websocket.close(code=4004)
        return

    # JWT 認証
    try:
        decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        logger.warning("ws_auth_failed", channel=channel)
        return

    await manager.connect(websocket, channel)
    try:
        # keepalive loop
        while True:
            # Wait for ping from client or timeout for server-side ping
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=KEEPALIVE_INTERVAL)
                if data == "ping":
                    await websocket.send_text("pong")
            except TimeoutError:
                # Server-initiated ping
                await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("ws_error", channel=channel, error=str(exc))
    finally:
        manager.disconnect(websocket, channel)


@router.get("/stats")
async def websocket_stats() -> dict:
    """WebSocket接続統計（アクティブ接続数・チャンネル別）"""
    return manager.stats()
