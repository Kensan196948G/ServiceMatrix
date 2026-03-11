"""Redis Streams EventBus テストスイート"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── EventBus ユニットテスト ───────────────────────────────────────────────────


class TestEventBus:
    """EventBus クラスの単体テスト（Redis モック使用）"""

    def _make_bus(self, mock_client: AsyncMock):
        from src.core.event_bus import EventBus

        bus = EventBus(redis_url="redis://localhost:6379/0")
        bus._client = mock_client
        return bus

    def _make_client(self) -> AsyncMock:
        client = AsyncMock()
        client.xadd = AsyncMock(return_value="1234567890-0")
        client.xack = AsyncMock(return_value=1)
        client.xreadgroup = AsyncMock(return_value=[])
        client.xgroup_create = AsyncMock(return_value=True)
        client.xinfo_stream = AsyncMock(
            return_value={"length": 5, "first-entry": None, "last-entry": None, "groups": 1}
        )
        client.xrevrange = AsyncMock(return_value=[])
        client.aclose = AsyncMock()
        return client

    def test_event_bus_init(self):
        """EventBus 初期化テスト"""
        from src.core.event_bus import EventBus

        bus = EventBus(redis_url="redis://testhost:6379/1")
        assert bus._redis_url == "redis://testhost:6379/1"
        assert bus._client is None

    @pytest.mark.asyncio
    async def test_publish_returns_message_id(self):
        """publish がメッセージIDを返す"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        msg_id = await bus.publish("sm:events:incidents", "incident.created", {"id": "123"})
        assert msg_id == "1234567890-0"
        mock_client.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_serializes_payload(self):
        """publish がペイロードをJSONシリアライズして送信する"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        payload = {"id": "abc", "title": "テストインシデント", "priority": "P1"}
        await bus.publish("sm:events:incidents", "incident.created", payload)

        call_args = mock_client.xadd.call_args
        fields = call_args[0][1]
        assert "payload" in fields
        deserialized = json.loads(fields["payload"])
        assert deserialized["id"] == "abc"
        assert deserialized["title"] == "テストインシデント"

    @pytest.mark.asyncio
    async def test_publish_sets_event_type(self):
        """publish がevent_typeフィールドをセットする"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        await bus.publish("sm:events:changes", "change.approved", {})
        call_args = mock_client.xadd.call_args
        fields = call_args[0][1]
        assert fields["event_type"] == "change.approved"

    @pytest.mark.asyncio
    async def test_publish_sets_event_id(self):
        """publish がUUID形式のevent_idをセットする"""
        import uuid

        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        await bus.publish("sm:events:sla", "sla.breached", {})
        call_args = mock_client.xadd.call_args
        fields = call_args[0][1]
        # UUIDとしてパース可能であることを確認
        uuid.UUID(fields["event_id"])

    @pytest.mark.asyncio
    async def test_ack_returns_count(self):
        """ack が確認済みメッセージ数を返す"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        count = await bus.ack("sm:events:incidents", "group-a", "1234567890-0")
        assert count == 1
        mock_client.xack.assert_called_once_with(
            "sm:events:incidents", "group-a", "1234567890-0"
        )

    @pytest.mark.asyncio
    async def test_consume_empty_stream(self):
        """空ストリームからの consume は空リストを返す"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        messages = await bus.consume("sm:events:incidents", "group-a", "consumer-1")
        assert messages == []

    @pytest.mark.asyncio
    async def test_consume_with_messages(self):
        """consume がメッセージを正しくパースする"""
        payload = {"id": "INC-001", "priority": "P1"}
        mock_client = self._make_client()
        mock_client.xreadgroup = AsyncMock(
            return_value=[
                [
                    "sm:events:incidents",
                    [
                        (
                            "1234567890-0",
                            {
                                "event_id": "uuid-abc",
                                "event_type": "incident.created",
                                "payload": json.dumps(payload),
                            },
                        )
                    ],
                ]
            ]
        )
        bus = self._make_bus(mock_client)

        messages = await bus.consume("sm:events:incidents", "group-a", "consumer-1")
        assert len(messages) == 1
        assert messages[0]["event_type"] == "incident.created"
        assert messages[0]["payload"]["id"] == "INC-001"
        assert messages[0]["message_id"] == "1234567890-0"

    @pytest.mark.asyncio
    async def test_ensure_consumer_group_creates_group(self):
        """ensure_consumer_group がxgroup_createを呼ぶ"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        await bus.ensure_consumer_group("sm:events:incidents", "group-a")
        mock_client.xgroup_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_consumer_group_ignores_busygroup(self):
        """既存グループのBUSYGROUPエラーは無視される"""
        import redis.asyncio as aioredis

        mock_client = self._make_client()
        mock_client.xgroup_create = AsyncMock(
            side_effect=aioredis.ResponseError("BUSYGROUP Consumer Group already exists")
        )
        bus = self._make_bus(mock_client)

        # 例外が出ないことを確認
        await bus.ensure_consumer_group("sm:events:incidents", "group-a")

    @pytest.mark.asyncio
    async def test_send_to_dlq(self):
        """DLQへの送信テスト"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        dlq_id = await bus.send_to_dlq(
            original_stream="sm:events:incidents",
            message_id="1234567890-0",
            event_type="incident.created",
            payload={"id": "abc"},
            error="処理タイムアウト",
        )
        assert dlq_id == "1234567890-0"
        mock_client.xadd.assert_called_once()
        call_args = mock_client.xadd.call_args
        fields = call_args[0][1]
        assert fields["error"] == "処理タイムアウト"
        assert fields["original_stream"] == "sm:events:incidents"

    @pytest.mark.asyncio
    async def test_get_stream_info(self):
        """ストリーム情報取得テスト"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        info = await bus.get_stream_info("sm:events:incidents")
        assert info["stream"] == "sm:events:incidents"
        assert info["length"] == 5
        assert info["groups"] == 1

    @pytest.mark.asyncio
    async def test_get_stream_info_not_found(self):
        """存在しないストリームは error フィールドを返す"""
        import redis.asyncio as aioredis

        mock_client = self._make_client()
        mock_client.xinfo_stream = AsyncMock(
            side_effect=aioredis.ResponseError("ERR no such key")
        )
        bus = self._make_bus(mock_client)

        info = await bus.get_stream_info("sm:events:unknown")
        assert "error" in info
        assert info["length"] == 0

    @pytest.mark.asyncio
    async def test_list_streams_returns_all(self):
        """list_streams が全ストリーム情報を返す"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        results = await bus.list_streams()
        # incidents/changes/sla/notifications/dlq の5ストリーム
        assert len(results) == 5
        stream_names = {r["stream"] for r in results}
        assert "sm:events:incidents" in stream_names
        assert "sm:events:dlq" in stream_names

    @pytest.mark.asyncio
    async def test_close(self):
        """close でクライアントがクリアされる"""
        mock_client = self._make_client()
        bus = self._make_bus(mock_client)

        await bus.close()
        mock_client.aclose.assert_called_once()
        assert bus._client is None


# ── ストリーム名・イベント型定数テスト ──────────────────────────────────────────


class TestEventBusConstants:
    def test_stream_names(self):
        """ストリーム名が正しいプレフィックスを持つ"""
        from src.core.event_bus import (
            STREAM_CHANGES,
            STREAM_DLQ,
            STREAM_INCIDENTS,
            STREAM_NOTIFICATIONS,
            STREAM_SLA,
        )

        for stream in [STREAM_INCIDENTS, STREAM_CHANGES, STREAM_SLA, STREAM_NOTIFICATIONS]:
            assert stream.startswith("sm:events:")
        assert STREAM_DLQ == "sm:events:dlq"

    def test_event_type_constants(self):
        """イベント型定数が存在する"""
        from src.core.event_bus import (
            EVENT_CHANGE_APPROVED,
            EVENT_CHANGE_CREATED,
            EVENT_INCIDENT_CREATED,
            EVENT_INCIDENT_RESOLVED,
            EVENT_SLA_BREACHED,
            EVENT_SLA_WARNING,
        )

        assert "incident" in EVENT_INCIDENT_CREATED
        assert "incident" in EVENT_INCIDENT_RESOLVED
        assert "change" in EVENT_CHANGE_CREATED
        assert "change" in EVENT_CHANGE_APPROVED
        assert "sla" in EVENT_SLA_BREACHED
        assert "sla" in EVENT_SLA_WARNING

    def test_global_singleton(self):
        """グローバルシングルトンが存在する"""
        from src.core.event_bus import EventBus, event_bus

        assert isinstance(event_bus, EventBus)


# ── イベント API エンドポイントテスト ─────────────────────────────────────────


class TestEventsAPI:
    def setup_method(self):
        from fastapi.testclient import TestClient

        from src.main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def _patch_event_bus(self) -> Any:
        """event_bus をモックするコンテキストマネージャ"""
        mock_bus = MagicMock()
        mock_bus.list_streams = AsyncMock(
            return_value=[
                {"stream": "sm:events:incidents", "length": 3, "groups": 1},
                {"stream": "sm:events:dlq", "length": 0, "groups": 0},
            ]
        )
        mock_bus.get_stream_info = AsyncMock(
            return_value={"stream": "sm:events:incidents", "length": 3, "groups": 1}
        )
        mock_bus.publish = AsyncMock(return_value="9876543210-0")
        mock_bus._get_client = AsyncMock(return_value=self._make_mock_redis_client())
        return mock_bus

    def _make_mock_redis_client(self) -> AsyncMock:
        client = AsyncMock()
        client.xrevrange = AsyncMock(return_value=[])
        return client

    def test_list_streams_returns_200(self):
        """/api/v1/events/streams が200を返す"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.get("/api/v1/events/streams")
        assert resp.status_code == 200

    def test_list_streams_returns_list(self):
        """/api/v1/events/streams がリスト形式を返す"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.get("/api/v1/events/streams")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_stream_stats_incidents(self):
        """/api/v1/events/streams/incidents/stats が200を返す"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.get("/api/v1/events/streams/incidents/stats")
        assert resp.status_code == 200

    def test_get_stream_stats_unknown(self):
        """未知のストリーム名は404を返す"""
        resp = self.client.get("/api/v1/events/streams/unknown/stats")
        assert resp.status_code == 404

    def test_publish_event_returns_200(self):
        """/api/v1/events/publish が成功する"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.post(
                "/api/v1/events/publish",
                json={
                    "stream": "sm:events:incidents",
                    "event_type": "incident.created",
                    "payload": {"id": "INC-001"},
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message_id"] == "9876543210-0"
        assert data["event_type"] == "incident.created"

    def test_get_dlq_returns_200(self):
        """/api/v1/events/dlq が200を返す"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.get("/api/v1/events/dlq")
        assert resp.status_code == 200

    def test_get_dlq_returns_list(self):
        """/api/v1/events/dlq がリスト形式を返す"""
        mock_bus = self._patch_event_bus()
        with patch("src.api.v1.events.event_bus", mock_bus):
            resp = self.client.get("/api/v1/events/dlq")
        data = resp.json()
        assert isinstance(data, list)
