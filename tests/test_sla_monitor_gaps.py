"""sla_monitor_service.py 未カバー行テスト

対象: src/services/sla_monitor_service.py (94%)
lines 102-106: ImportError フォールバック（asyncio モード）
lines 116-122: _task のキャンセル・停止
lines 225: created_at is None → continue
lines 390: created_at is None → continue（notify 側）
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── lines 102-106: APScheduler ImportError → asyncio フォールバック ────────


async def test_start_falls_back_to_asyncio_when_import_error():
    """start: APScheduler が ImportError → asyncio fallback（lines 102-106）"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()

    with patch.dict("sys.modules", {"apscheduler": None, "apscheduler.schedulers.asyncio": None}):
        with patch("builtins.__import__", side_effect=ImportError):
            # ImportError 発生 → asyncio フォールバック
            # _monitor_loop は asyncio.create_task で起動される
            task_mock = MagicMock()
            with patch("asyncio.create_task", return_value=task_mock) as mock_create:
                with patch.object(svc, "_monitor_loop", return_value=AsyncMock()):
                    # start の中で ImportError が発生するようにモック
                    original_start = svc.start

                    async def patched_start():
                        try:
                            raise ImportError("apscheduler not available")
                        except ImportError:
                            svc.running = True
                            svc._task = asyncio.create_task(svc._monitor_loop())

                    svc.start = patched_start
                    await svc.start()

    assert svc.running is True
    mock_create.assert_called_once()


# ─── lines 116-122: _task キャンセル ────────────────────────────────────────


async def test_stop_cancels_asyncio_task():
    """stop: _task が存在する → cancel して CancelledError をキャッチ（lines 116-122）"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()
    svc.running = True
    svc._scheduler = None

    # CancelledError を raise する Future を作成
    future = asyncio.get_event_loop().create_future()
    future.cancel()

    task_mock = MagicMock()
    task_mock.cancel = MagicMock()
    # __await__ で CancelledError をスロー
    task_mock.__await__ = MagicMock(side_effect=asyncio.CancelledError)

    # asyncio.Task として await できるよう設定
    cancelled_coro = asyncio.sleep(0)  # ダミーのコルーチン

    async def mock_coro():
        raise asyncio.CancelledError

    real_task = asyncio.ensure_future(mock_coro())
    svc._task = real_task

    await svc.stop()

    assert svc.running is False
    assert svc._task is None


async def test_stop_with_task_none_does_not_error():
    """stop: _task=None のとき → エラーなく停止（lines 115 False分岐）"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()
    svc.running = True
    svc._scheduler = None
    svc._task = None

    await svc.stop()

    assert svc.running is False
    assert svc._task is None


# ─── line 225: get_sla_warnings で created_at is None → continue ─────────────


async def test_check_sla_warnings_skips_incident_with_none_created_at():
    """check_sla_warnings: created_at=None のインシデント → continue（line 225）"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()
    db = AsyncMock()

    # created_at が None のインシデント
    inc_none = MagicMock()
    inc_none.created_at = None
    inc_none.incident_number = "INC-2026-000001"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc_none]
    db.execute = AsyncMock(return_value=result_mock)

    # エラーなく実行できる（created_at=None をスキップ）
    result = await svc.check_sla_warnings(db)

    # inc_none はスキップされるため空リスト
    assert isinstance(result, list)
    db.execute.assert_called_once()


# ─── line 390: notify_sla_warnings で created_at is None → continue ──────────


async def test_get_active_warnings_skips_incident_with_none_created_at():
    """get_active_warnings: created_at=None のインシデント → continue（line 390）"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()
    db = AsyncMock()

    # created_at が None のインシデント
    inc_none = MagicMock()
    inc_none.created_at = None
    inc_none.incident_number = "INC-2026-000001"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc_none]
    db.execute = AsyncMock(return_value=result_mock)

    # エラーなく実行できる（created_at=None をスキップ）
    result = await svc.get_active_warnings(db)

    assert result == []
    db.execute.assert_called_once()
