"""Celery アプリケーション設定"""

from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "servicematrix",
    broker=settings.redis_url,
    backend=settings.redis_url,
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
