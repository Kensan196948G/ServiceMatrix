"""EDAイベントコンシューマーワーカー テストスイート"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ── EventConsumerWorker ユニットテスト ────────────────────────────────────────


class TestEventConsumerWorker:
    """EventConsumerWorker クラスの単体テスト"""

    def _make_worker(self):
        from src.services.event_consumer import EventConsumerWorker

        return EventConsumerWorker(
            group="test-group",
            consumer="test-consumer",
            poll_interval=0.01,
            max_retries=2,
        )

    def test_init(self):
        """初期化テスト"""
        worker = self._make_worker()
        assert worker._group == "test-group"
        assert worker._consumer == "test-consumer"
        assert worker._running is False
        assert worker._task is None
        assert worker._handlers == {}

    def test_register_handler(self):
        """ハンドラー登録テスト"""
        worker = self._make_worker()

        async def my_handler(payload):
            pass

        worker.register_handler("sm:events:incidents", "incident.created", my_handler)
        assert "sm:events:incidents" in worker._handlers
        assert "incident.created" in worker._handlers["sm:events:incidents"]
        assert worker._handlers["sm:events:incidents"]["incident.created"] is my_handler

    def test_register_multiple_handlers_same_stream(self):
        """同一ストリームへの複数ハンドラー登録"""
        worker = self._make_worker()

        async def handler_a(payload):
            pass

        async def handler_b(payload):
            pass

        worker.register_handler("sm:events:incidents", "incident.created", handler_a)
        worker.register_handler("sm:events:incidents", "incident.resolved", handler_b)
        assert len(worker._handlers["sm:events:incidents"]) == 2

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """start() でワーカーが起動する"""
        worker = self._make_worker()

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ensure_consumer_group = AsyncMock()
            mock_bus.consume = AsyncMock(return_value=[])
            worker.register_handler("sm:events:incidents", "incident.created", AsyncMock())
            await worker.start()
            assert worker._running is True
            assert worker._task is not None
            await worker.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """二重startは無視される"""
        worker = self._make_worker()

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ensure_consumer_group = AsyncMock()
            mock_bus.consume = AsyncMock(return_value=[])
            worker.register_handler("sm:events:incidents", "incident.created", AsyncMock())
            await worker.start()
            task1 = worker._task
            await worker.start()  # 2回目
            task2 = worker._task
            assert task1 is task2  # タスクが変わらない
            await worker.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_state(self):
        """stop() でワーカーが停止する"""
        worker = self._make_worker()

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ensure_consumer_group = AsyncMock()
            mock_bus.consume = AsyncMock(return_value=[])
            worker.register_handler("sm:events:incidents", "incident.created", AsyncMock())
            await worker.start()
            await worker.stop()
            assert worker._running is False
            assert worker._task is None

    @pytest.mark.asyncio
    async def test_process_message_calls_handler(self):
        """メッセージ受信時にハンドラーが呼ばれる"""
        worker = self._make_worker()
        handler = AsyncMock()

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ack = AsyncMock(return_value=1)
            await worker._process_message(
                "sm:events:incidents",
                {
                    "message_id": "123-0",
                    "event_type": "incident.created",
                    "payload": {"id": "INC-001"},
                },
                {"incident.created": handler},
            )
        handler.assert_called_once_with({"id": "INC-001"})

    @pytest.mark.asyncio
    async def test_process_message_acks_after_success(self):
        """ハンドラー成功後にACKが呼ばれる"""
        worker = self._make_worker()
        mock_ack = AsyncMock(return_value=1)

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ack = mock_ack
            await worker._process_message(
                "sm:events:sla",
                {"message_id": "456-0", "event_type": "sla.breached", "payload": {}},
                {"sla.breached": AsyncMock()},
            )
        mock_ack.assert_called_once_with("sm:events:sla", "test-group", "456-0")

    @pytest.mark.asyncio
    async def test_process_message_unknown_event_type(self):
        """未知のイベント型はACKして無視する"""
        worker = self._make_worker()
        mock_ack = AsyncMock(return_value=1)

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ack = mock_ack
            await worker._process_message(
                "sm:events:incidents",
                {"message_id": "789-0", "event_type": "unknown.event", "payload": {}},
                {"incident.created": AsyncMock()},
            )
        mock_ack.assert_called_once()  # ACKは呼ばれる

    @pytest.mark.asyncio
    async def test_process_message_retry_on_failure(self):
        """ハンドラー失敗時にリトライされる"""
        worker = self._make_worker()
        call_count = {"n": 0}

        async def failing_handler(payload):
            call_count["n"] += 1
            raise ValueError("処理エラー")

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ack = AsyncMock(return_value=1)
            mock_bus.send_to_dlq = AsyncMock(return_value="dlq-123")
            await worker._process_message(
                "sm:events:incidents",
                {"message_id": "err-0", "event_type": "incident.created", "payload": {}},
                {"incident.created": failing_handler},
            )
        # max_retries=2 なので2回試みる
        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_process_message_sends_to_dlq_after_max_retries(self):
        """最大リトライ後にDLQへ転送する"""
        worker = self._make_worker()
        mock_dlq = AsyncMock(return_value="dlq-999")

        async def always_fails(payload):
            raise RuntimeError("致命的エラー")

        with patch("src.services.event_consumer.event_bus") as mock_bus:
            mock_bus.ack = AsyncMock()
            mock_bus.send_to_dlq = mock_dlq
            await worker._process_message(
                "sm:events:incidents",
                {
                    "message_id": "fail-0",
                    "event_type": "incident.created",
                    "payload": {"id": "X"},
                },
                {"incident.created": always_fails},
            )
        mock_dlq.assert_called_once()
        call_kwargs = mock_dlq.call_args[1]
        assert call_kwargs["original_stream"] == "sm:events:incidents"
        assert call_kwargs["message_id"] == "fail-0"


# ── デフォルトハンドラーテスト ────────────────────────────────────────────────


class TestDefaultHandlers:
    """デフォルトイベントハンドラーの単体テスト"""

    @pytest.mark.asyncio
    async def test_handle_incident_created_normal(self):
        """P4インシデント作成ハンドラー正常動作"""
        from src.services.event_consumer import handle_incident_created

        await handle_incident_created({"id": "INC-001", "priority": "P4", "title": "テスト"})

    @pytest.mark.asyncio
    async def test_handle_incident_created_high_priority(self):
        """P1インシデントは警告ログを出す"""
        from src.services.event_consumer import handle_incident_created

        # 例外が出ないことを確認
        await handle_incident_created({"id": "INC-002", "priority": "P1", "title": "緊急障害"})

    @pytest.mark.asyncio
    async def test_handle_sla_breached(self):
        """SLA違反ハンドラー正常動作"""
        from src.services.event_consumer import handle_sla_breached

        await handle_sla_breached({"incident_id": "INC-001", "sla_type": "response"})

    @pytest.mark.asyncio
    async def test_handle_change_approved(self):
        """変更承認ハンドラー正常動作"""
        from src.services.event_consumer import handle_change_approved

        await handle_change_approved({"id": "CHG-001", "approved_by": "admin"})


# ── グローバルシングルトンテスト ─────────────────────────────────────────────


class TestEventConsumerSingleton:
    def test_event_consumer_singleton_exists(self):
        """グローバルシングルトンが存在する"""
        from src.services.event_consumer import EventConsumerWorker, event_consumer

        assert isinstance(event_consumer, EventConsumerWorker)

    def test_event_consumer_has_default_handlers(self):
        """デフォルトワーカーが3ストリームのハンドラーを持つ"""
        from src.core.event_bus import STREAM_CHANGES, STREAM_INCIDENTS, STREAM_SLA
        from src.services.event_consumer import event_consumer

        assert STREAM_INCIDENTS in event_consumer._handlers
        assert STREAM_SLA in event_consumer._handlers
        assert STREAM_CHANGES in event_consumer._handlers

    def test_create_default_worker(self):
        """create_default_worker が正しくハンドラーを登録する"""
        from src.core.event_bus import (
            EVENT_CHANGE_APPROVED,
            EVENT_INCIDENT_CREATED,
            EVENT_SLA_BREACHED,
            STREAM_CHANGES,
            STREAM_INCIDENTS,
            STREAM_SLA,
        )
        from src.services.event_consumer import create_default_worker

        worker = create_default_worker()
        assert EVENT_INCIDENT_CREATED in worker._handlers[STREAM_INCIDENTS]
        assert EVENT_SLA_BREACHED in worker._handlers[STREAM_SLA]
        assert EVENT_CHANGE_APPROVED in worker._handlers[STREAM_CHANGES]
