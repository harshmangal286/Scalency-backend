"""
Celery application factory.

For production: Uses Redis as broker and backend.
For local dev: Uses synchronous execution (no Redis needed).
"""

from celery import Celery

from app.core.config import settings

# Detect if running locally (SQLite) or production (PostgreSQL with Redis)
is_local_dev = "sqlite" in settings.DATABASE_URL.lower()

if is_local_dev:
    # Local development: run tasks synchronously without Redis
    broker_url = "memory://"
    backend_url = "cache+memory://"
    celery_config = {
        "task_always_eager": True,  # Execute immediately, don't queue
        "task_eager_propagates": True,  # Propagate exceptions
    }
else:
    # Production: use Redis
    broker_url = settings.REDIS_URL
    backend_url = settings.REDIS_URL
    celery_config = {}

celery_app = Celery(
    "scalency",
    broker=broker_url,
    backend=backend_url,
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
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    **celery_config,
)
