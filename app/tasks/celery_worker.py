"""
Celery application factory.

Creates and configures the Celery instance backed by Redis.
All task modules must be listed in `include` so they are auto-discovered
by the worker process.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "scalency",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.publish_task",
        "app.tasks.repost_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry failed tasks up to 3 times with exponential back-off
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
)
