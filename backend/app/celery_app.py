"""
Celery application configuration for asynchronous task processing.
"""

from celery import Celery

from app.config import settings


celery_app = Celery(
    "artemis_insight",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Johannesburg",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=2,  # Prefetch 2 tasks per worker for better throughput
    worker_max_tasks_per_child=50,  # Restart after 50 tasks to prevent memory leaks
    broker_connection_retry_on_startup=True,
    broker_pool_limit=10,  # Connection pool size
)
