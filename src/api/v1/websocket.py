"""WebSocket リアルタイム通知 API"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.services.ws_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket, token: str = Query(None),
):
    await manager.connect(websocket)
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
            # ping-pong ヘルスチェック
            if data.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
            else:
                await manager.broadcast({"type": "notification", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/incidents")
async def websocket_incidents(websocket: WebSocket):
    """インシデント更新通知チャンネル"""
    await manager.connect(websocket)
    try:
        await manager.send_personal_message(
            {"type": "connected", "channel": "incidents"},
            websocket,
        )
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
