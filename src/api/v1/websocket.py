"""WebSocket リアルタイム通知 API"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.security import decode_token
from src.services.ws_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])

VALID_MESSAGE_TYPES = {"ping", "subscribe", "unsubscribe"}


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """認証済みWebSocket接続 - JWT必須"""
    # JWT検証
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    channel = f"user:{user_id}"
    await manager.connect(websocket, channel)
    try:
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "WebSocket接続確立",
                "connections": manager.connection_count,
            },
            websocket,
        )
        while True:
            data = await websocket.receive_json()
            # メッセージタイプバリデーション
            if not isinstance(data, dict) or data.get("type") not in VALID_MESSAGE_TYPES:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid message type"},
                    websocket,
                )
                continue
            if data.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
            else:
                await manager.broadcast({"type": "notification", "data": data}, channel)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


@router.websocket("/incidents")
async def websocket_incidents(
    websocket: WebSocket,
    token: str = Query(...),
):
    """インシデント更新通知チャンネル - JWT必須"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    channel = "incidents"
    await manager.connect(websocket, channel)
    try:
        await manager.send_personal_message(
            {"type": "connected", "channel": "incidents"},
            websocket,
        )
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
