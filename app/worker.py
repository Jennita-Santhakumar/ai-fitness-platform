from celery import Celery
from app.core.config import settings

# Initialize Celery app with Redis as message broker and result backend
celery_app = Celery(
    "ai_fitness_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Standard production serialization and timing settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="app.worker.add")
def add(x: int, y: int) -> int:
    """Test task to verify Celery worker connectivity and execution."""
    return x + y
