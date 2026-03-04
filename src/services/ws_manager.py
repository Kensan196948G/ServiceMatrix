"""WebSocket 接続管理・リアルタイム通知サービス"""

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        if channel in self.active_connections:
            connections = self.active_connections[channel]
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                del self.active_connections[channel]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, channel: str = "default"):
        connections = list(self.active_connections.get(channel, []))
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001
                self.disconnect(connection, channel)

    async def broadcast_all(self, message: dict):
        for channel in list(self.active_connections.keys()):
            await self.broadcast(message, channel)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    def channel_count(self, channel: str) -> int:
        return len(self.active_connections.get(channel, []))


manager = ConnectionManager()
