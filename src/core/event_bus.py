"""Redis Streams イベントバス - イベント駆動アーキテクチャ基盤"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis  # type: ignore[import-untyped]
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

# ── ストリーム名定数 ──────────────────────────────────────────────────────────

STREAM_INCIDENTS = "sm:events:incidents"
STREAM_CHANGES = "sm:events:changes"
STREAM_SLA = "sm:events:sla"
STREAM_NOTIFICATIONS = "sm:events:notifications"
STREAM_DLQ = "sm:events:dlq"

# ── イベント型定数 ────────────────────────────────────────────────────────────

EVENT_INCIDENT_CREATED = "incident.created"
EVENT_INCIDENT_UPDATED = "incident.updated"
EVENT_INCIDENT_RESOLVED = "incident.resolved"
EVENT_CHANGE_CREATED = "change.created"
EVENT_CHANGE_APPROVED = "change.approved"
EVENT_CHANGE_REJECTED = "change.rejected"
EVENT_SLA_BREACHED = "sla.breached"
EVENT_SLA_WARNING = "sla.warning"


class EventBus:
    """Redis Streams ベースのイベントバス。

    publish/consume/ack の3メソッドによるシンプルなAPIで
    イベント駆動アーキテクチャを実現する。
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """接続クローズ"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── 発行 ──────────────────────────────────────────────────────────────────

    async def publish(
        self,
        stream: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        max_len: int = 10_000,
    ) -> str:
        """イベントをストリームに発行する。

        Args:
            stream: ストリーム名 (例: STREAM_INCIDENTS)
            event_type: イベント型 (例: EVENT_INCIDENT_CREATED)
            payload: イベントペイロード（JSON シリアライズ可能）
            max_len: ストリームの最大エントリ数（古いエントリを自動削除）

        Returns:
            生成されたメッセージID (Redis の "*" 自動採番)
        """
        client = await self._get_client()
        event_id = str(uuid.uuid4())
        fields = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False),
        }
        message_id: str = await client.xadd(stream, fields, maxlen=max_len, approximate=True)
        logger.info(
            "event_published",
            stream=stream,
            event_type=event_type,
            event_id=event_id,
            message_id=message_id,
        )
        return message_id

    # ── 購読 ──────────────────────────────────────────────────────────────────

    async def ensure_consumer_group(self, stream: str, group: str) -> None:
        """コンシューマーグループが存在しなければ作成する。"""
        client = await self._get_client()
        try:
            await client.xgroup_create(stream, group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        count: int = 10,
        block_ms: int = 2000,
    ) -> list[dict[str, Any]]:
        """コンシューマーグループからメッセージを取得する。

        Args:
            stream: ストリーム名
            group: コンシューマーグループ名
            consumer: コンシューマー識別子
            count: 1回に取得するメッセージ数
            block_ms: ブロッキング待機時間（ミリ秒）

        Returns:
            メッセージのリスト。各要素は
            {"message_id": str, "event_id": str, "event_type": str, "payload": dict}
        """
        client = await self._get_client()
        await self.ensure_consumer_group(stream, group)
        raw = await client.xreadgroup(
            group,
            consumer,
            {stream: ">"},
            count=count,
            block=block_ms,
        )
        results: list[dict[str, Any]] = []
        if not raw:
            return results
        for _stream_name, messages in raw:
            for message_id, fields in messages:
                try:
                    payload = json.loads(fields.get("payload", "{}"))
                except json.JSONDecodeError:
                    payload = {}
                results.append(
                    {
                        "message_id": message_id,
                        "event_id": fields.get("event_id", ""),
                        "event_type": fields.get("event_type", ""),
                        "payload": payload,
                    }
                )
        return results

    # ── 確認 ──────────────────────────────────────────────────────────────────

    async def ack(self, stream: str, group: str, message_id: str) -> int:
        """メッセージ処理完了を確認する（ACK）。

        Returns:
            確認したメッセージ数 (通常 1)
        """
        client = await self._get_client()
        count: int = await client.xack(stream, group, message_id)
        return count

    # ── デッドレターキュー ────────────────────────────────────────────────────

    async def send_to_dlq(
        self,
        original_stream: str,
        message_id: str,
        event_type: str,
        payload: dict[str, Any],
        error: str,
    ) -> str:
        """処理失敗メッセージをDLQに送信する。"""
        client = await self._get_client()
        dlq_fields = {
            "original_stream": original_stream,
            "original_message_id": message_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False),
            "error": error,
        }
        dlq_id: str = await client.xadd(STREAM_DLQ, dlq_fields, maxlen=5_000, approximate=True)
        logger.warning(
            "event_sent_to_dlq",
            original_stream=original_stream,
            message_id=message_id,
            event_type=event_type,
            error=error,
        )
        return dlq_id

    # ── 統計 ──────────────────────────────────────────────────────────────────

    async def get_stream_info(self, stream: str) -> dict[str, Any]:
        """ストリームの統計情報を返す。"""
        client = await self._get_client()
        try:
            info = await client.xinfo_stream(stream)
            return {
                "stream": stream,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except aioredis.ResponseError:
            return {"stream": stream, "length": 0, "error": "stream not found"}

    async def list_streams(self) -> list[dict[str, Any]]:
        """既定のストリーム群の情報一覧を返す。"""
        streams = [STREAM_INCIDENTS, STREAM_CHANGES, STREAM_SLA, STREAM_NOTIFICATIONS, STREAM_DLQ]
        results = []
        for stream in streams:
            info = await self.get_stream_info(stream)
            results.append(info)
        return results


# ── グローバルシングルトン ─────────────────────────────────────────────────────
event_bus = EventBus()
