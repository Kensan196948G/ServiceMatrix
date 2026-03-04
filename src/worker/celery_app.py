"""Celery アプリケーション設定"""

from celery import Celery

from src.core.config import settings

# Redis URL (settings から取得)
REDIS_URL = settings.redis_url

celery_app = Celery(
    "servicematrix",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
