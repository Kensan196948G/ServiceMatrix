"""WebSocket接続管理・ブロードキャスト"""

import json
from typing import Any

from fastapi import WebSocket

from src.core.logging import get_logger

logger = get_logger(__name__)

VALID_CHANNELS = {"incidents", "changes", "sla_alerts", "all"}


class ConnectionManager:
    """WebSocket接続プール管理"""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "all") -> None:
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(
            "ws_connected",
            channel=channel,
            total=len(self.active_connections[channel]),
        )

    def disconnect(self, websocket: WebSocket, channel: str = "all") -> None:
        conns = self.active_connections.get(channel, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info(
            "ws_disconnected",
            channel=channel,
            remaining=len(conns),
        )

    async def broadcast(self, message: dict[str, Any], channel: str = "all") -> None:
        """チャンネルの全接続にメッセージをブロードキャスト。
        "all"チャンネルへのメッセージは全チャンネル購読者にも配信する。"""
        payload = json.dumps(message, ensure_ascii=False, default=str)

        # 対象チャンネルへ送信
        target_channels: set[str] = {channel}
        # channel特有のメッセージは "all" 購読者にも届ける
        if channel != "all":
            target_channels.add("all")

        for ch in target_channels:
            dead: list[WebSocket] = []
            for ws in list(self.active_connections.get(ch, [])):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, ch)

    async def broadcast_incident_update(
        self, incident_id: str, action: str, data: dict[str, Any]
    ) -> None:
        """インシデント更新をブロードキャスト"""
        await self.broadcast(
            {
                "type": "incident_update",
                "action": action,
                "incident_id": incident_id,
                "data": data,
            },
            channel="incidents",
        )

    async def broadcast_sla_alert(self, incident_id: str, warning_level: str) -> None:
        """SLAアラートをブロードキャスト"""
        await self.broadcast(
            {
                "type": "sla_alert",
                "incident_id": incident_id,
                "warning_level": warning_level,
            },
            channel="sla_alerts",
        )

    def stats(self) -> dict[str, Any]:
        """接続統計を返す"""
        per_channel = {ch: len(conns) for ch, conns in self.active_connections.items()}
        return {
            "total": sum(per_channel.values()),
            "channels": per_channel,
        }


manager = ConnectionManager()
