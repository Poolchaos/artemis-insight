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
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completion (enable retry on crash)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
    worker_prefetch_multiplier=1,  # Prevent task hoarding, process one at a time
    worker_max_tasks_per_child=50,  # Restart after 50 tasks to prevent memory leaks
    broker_connection_retry_on_startup=True,
    broker_pool_limit=10,  # Connection pool size
    task_send_sent_event=True,  # Track task events for monitoring
    worker_send_task_events=True,  # Enable task event monitoring
)

# Celery Beat Schedule - periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-stuck-jobs-every-5-minutes': {
        'task': 'app.tasks.cleanup_stuck_jobs_task',
        'schedule': 300.0,  # Run every 5 minutes
    },
}
