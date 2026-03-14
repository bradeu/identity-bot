from celery import Celery
from config.config import get_settings
import openai

settings = get_settings()

openai.api_key = settings.OPENAI_API_KEY

# Create Celery application
celery_app = Celery("backend",
                    broker=settings.CELERY_BROKER_URL,
                    backend=settings.CELERY_RESULT_BACKEND,
                    include=[
                        "tasks.background_tasks",
                        "celery_signals",
                    ])

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_track_started=True,
    task_send_sent_event=True,
)

# Task routing
celery_app.conf.task_routes = {
    "tasks.background_tasks.csv_task": {
        "queue": "processing"
    },
}

# Queue configuration
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_create_missing_queues = True
