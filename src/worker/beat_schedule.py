"""Celery Beat 定期スケジュール設定"""

from celery.schedules import crontab

from src.worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    # SLAチェック: 毎分実行
    "check-sla-every-minute": {
        "task": "tasks.check_sla_breaches",
        "schedule": 60.0,
    },
    # 日次ログクリーンアップチェック: 毎日午前2時
    "daily-log-cleanup-check": {
        "task": "tasks.cleanup_old_logs",
        "schedule": crontab(hour=2, minute=0),
        "args": (365 * 7,),
    },
}
