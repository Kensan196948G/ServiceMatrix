"""Celery タスクテスト"""

import pytest

pytestmark = pytest.mark.asyncio


def test_celery_app_exists():
    """celery_app が正しく設定されている"""
    from src.worker.celery_app import celery_app

    assert celery_app is not None
    assert celery_app.main == "servicematrix"


def test_celery_app_broker_config():
    """ブローカー設定が存在する"""
    from src.worker.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.timezone == "Asia/Tokyo"


def test_celery_tasks_registered():
    """タスクが登録されている"""
    from src.worker import tasks  # noqa: F401
    from src.worker.celery_app import celery_app

    registered = list(celery_app.tasks.keys())
    assert any("check_sla" in t for t in registered)
    assert any("send_notification" in t for t in registered)
    assert any("ai_triage" in t for t in registered)


def test_send_notification_task():
    """send_notification タスクが正常実行される"""
    from src.worker.tasks import send_notification

    result = send_notification("user-123", "テスト通知", "info")
    assert result["success"] is True
    assert result["user_id"] == "user-123"
    assert result["type"] == "info"
    assert "sent_at" in result


def test_cleanup_old_logs_task():
    """cleanup_old_logs タスクが正常実行される"""
    from src.worker.tasks import cleanup_old_logs

    result = cleanup_old_logs(365 * 7)
    assert result["days_to_keep"] == 365 * 7
    assert result["action"] == "check_only"
    assert "checked_at" in result


async def test_check_sla_async_runs(db_session):
    """_check_sla_async が DB クエリを実行できる"""
    from contextlib import asynccontextmanager
    from unittest.mock import patch

    @asynccontextmanager
    async def mock_session():
        yield db_session

    with patch("src.core.database.AsyncSessionLocal", mock_session):
        from src.worker.tasks import _check_sla_async

        result = await _check_sla_async()
        assert "open_incidents" in result
        assert "checked_at" in result
        assert isinstance(result["open_incidents"], int)


async def test_ai_triage_async_runs():
    """_ai_triage_async が AI 分類を実行できる"""
    from src.worker.tasks import _ai_triage_async

    result = await _ai_triage_async("inc-001", "サーバーダウン", "本番サーバーが応答しない")
    assert result["incident_id"] == "inc-001"
    assert "priority" in result
    assert "category" in result


def test_beat_schedule_configured():
    """Beat スケジュールが設定されている"""
    from src.worker import beat_schedule  # noqa: F401
    from src.worker.celery_app import celery_app

    assert "check-sla-every-minute" in celery_app.conf.beat_schedule


def test_celery_task_names():
    """タスク名が正しく設定されている"""
    from src.worker.tasks import (
        ai_triage_incident,
        check_sla_breaches,
        cleanup_old_logs,
        send_notification,
    )

    assert check_sla_breaches.name == "tasks.check_sla_breaches"
    assert send_notification.name == "tasks.send_notification"
    assert ai_triage_incident.name == "tasks.ai_triage_incident"
    assert cleanup_old_logs.name == "tasks.cleanup_old_logs"


def test_celery_worker_module_importable():
    """worker モジュールがインポート可能"""
    from src.worker import beat_schedule, celery_app, tasks  # noqa: F401

    assert True


def test_notification_task_with_different_types():
    """異なる通知タイプで send_notification が動作する"""
    from src.worker.tasks import send_notification

    for ntype in ["info", "warning", "error"]:
        result = send_notification("user-456", f"{ntype}通知テスト", ntype)
        assert result["success"] is True
        assert result["type"] == ntype


def test_celery_app_task_track_started():
    """task_track_started が有効"""
    from src.worker.celery_app import celery_app

    assert celery_app.conf.task_track_started is True
