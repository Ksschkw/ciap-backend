from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]

from app.config import settings

celery_app = Celery(
    "ciap_backend",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.sync_tasks",
        "app.tasks.scoring_tasks",
        "app.tasks.sentiment_tasks",
        "app.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
