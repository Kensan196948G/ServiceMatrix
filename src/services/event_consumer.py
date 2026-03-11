"""EDAイベントコンシューマーワーカー - Redis Streams コンシューマーグループ処理"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from src.core.event_bus import (
    EVENT_CHANGE_APPROVED,
    EVENT_INCIDENT_CREATED,
    EVENT_SLA_BREACHED,
    STREAM_CHANGES,
    STREAM_INCIDENTS,
    STREAM_SLA,
    event_bus,
)

logger = structlog.get_logger(__name__)

# ハンドラー型エイリアス
HandlerFunc = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# コンシューマーグループ名
CONSUMER_GROUP = "sm-workers"
CONSUMER_NAME = "worker-1"


# ── デフォルトハンドラー ──────────────────────────────────────────────────────


async def handle_incident_created(payload: dict[str, Any]) -> None:
    """インシデント作成イベントを処理する。"""
    incident_id = payload.get("id", "unknown")
    priority = payload.get("priority", "P4")
    title = payload.get("title", "")
    logger.info(
        "incident_created_event",
        incident_id=incident_id,
        priority=priority,
        title=title,
    )
    # 高優先度インシデントは通知キューに追加（P1/P2）
    if priority in ("P1", "P2"):
        logger.warning(
            "high_priority_incident_alert",
            incident_id=incident_id,
            priority=priority,
        )


async def handle_sla_breached(payload: dict[str, Any]) -> None:
    """SLA違反イベントを処理する。"""
    incident_id = payload.get("incident_id", "unknown")
    sla_type = payload.get("sla_type", "response")
    logger.warning(
        "sla_breached_alert",
        incident_id=incident_id,
        sla_type=sla_type,
    )


async def handle_change_approved(payload: dict[str, Any]) -> None:
    """変更承認イベントを処理する。"""
    change_id = payload.get("id", "unknown")
    approved_by = payload.get("approved_by", "unknown")
    logger.info(
        "change_approved_notification",
        change_id=change_id,
        approved_by=approved_by,
    )


# ── EventConsumerWorker ───────────────────────────────────────────────────────


class EventConsumerWorker:
    """Redis Streams イベントコンシューマーワーカー。

    複数ストリームを監視し、登録されたハンドラーを非同期で呼び出す。
    失敗したメッセージは自動的にDLQへ転送される。

    Usage:
        worker = EventConsumerWorker()
        worker.register_handler(STREAM_INCIDENTS, "incident.created", my_handler)
        await worker.start()
        # ...
        await worker.stop()
    """

    def __init__(
        self,
        group: str = CONSUMER_GROUP,
        consumer: str = CONSUMER_NAME,
        poll_interval: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        self._group = group
        self._consumer = consumer
        self._poll_interval = poll_interval
        self._max_retries = max_retries
        # {stream: {event_type: handler_func}}
        self._handlers: dict[str, dict[str, HandlerFunc]] = {}
        self._task: asyncio.Task | None = None
        self._running = False

    def register_handler(
        self,
        stream: str,
        event_type: str,
        handler: HandlerFunc,
    ) -> None:
        """イベントハンドラーを登録する。

        Args:
            stream: ストリーム名 (例: "sm:events:incidents")
            event_type: イベント型 (例: "incident.created")
            handler: 非同期ハンドラー関数 (payload: dict) -> None
        """
        if stream not in self._handlers:
            self._handlers[stream] = {}
        self._handlers[stream][event_type] = handler
        logger.debug("handler_registered", stream=stream, event_type=event_type)

    async def start(self) -> None:
        """ワーカーを起動する（バックグラウンドタスクとして常駐）。"""
        if self._running:
            return
        self._running = True

        # コンシューマーグループを事前作成
        for stream in self._handlers:
            try:
                await event_bus.ensure_consumer_group(stream, self._group)
            except Exception as exc:
                logger.warning("consumer_group_setup_error", stream=stream, error=str(exc))

        self._task = asyncio.create_task(self._run_loop(), name="event-consumer-worker")
        logger.info("event_consumer_worker_started", group=self._group, consumer=self._consumer)

    async def stop(self) -> None:
        """ワーカーを停止する。"""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("event_consumer_worker_stopped")

    async def _run_loop(self) -> None:
        """ポーリングループ（バックグラウンドタスク）。"""
        while self._running:
            try:
                await self._poll_all_streams()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("event_consumer_loop_error", error=str(exc))
            await asyncio.sleep(self._poll_interval)

    async def _poll_all_streams(self) -> None:
        """全ストリームからメッセージを取得して処理する。"""
        for stream, handlers in self._handlers.items():
            messages = await event_bus.consume(stream, self._group, self._consumer)
            for msg in messages:
                await self._process_message(stream, msg, handlers)

    async def _process_message(
        self,
        stream: str,
        msg: dict[str, Any],
        handlers: dict[str, HandlerFunc],
    ) -> None:
        """メッセージを処理し、失敗時はDLQへ転送する。"""
        message_id: str = msg.get("message_id", "")
        event_type: str = msg.get("event_type", "")
        payload: dict[str, Any] = msg.get("payload", {})

        handler = handlers.get(event_type)
        if handler is None:
            # 未知のイベント型は無視してACK
            logger.debug("no_handler_for_event", stream=stream, event_type=event_type)
            await event_bus.ack(stream, self._group, message_id)
            return

        for attempt in range(1, self._max_retries + 1):
            try:
                await handler(payload)
                await event_bus.ack(stream, self._group, message_id)
                logger.debug(
                    "event_processed",
                    stream=stream,
                    event_type=event_type,
                    message_id=message_id,
                )
                return
            except Exception as exc:
                logger.warning(
                    "event_handler_error",
                    stream=stream,
                    event_type=event_type,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt == self._max_retries:
                    # 最大リトライ後はDLQへ転送
                    await event_bus.send_to_dlq(
                        original_stream=stream,
                        message_id=message_id,
                        event_type=event_type,
                        payload=payload,
                        error=str(exc),
                    )
                    await event_bus.ack(stream, self._group, message_id)


# ── グローバルワーカーシングルトン ────────────────────────────────────────────

def create_default_worker() -> EventConsumerWorker:
    """デフォルトハンドラー登録済みのワーカーを生成する。"""
    worker = EventConsumerWorker()
    worker.register_handler(STREAM_INCIDENTS, EVENT_INCIDENT_CREATED, handle_incident_created)
    worker.register_handler(STREAM_SLA, EVENT_SLA_BREACHED, handle_sla_breached)
    worker.register_handler(STREAM_CHANGES, EVENT_CHANGE_APPROVED, handle_change_approved)
    return worker


event_consumer = create_default_worker()
