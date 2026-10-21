import logging
from typing import Dict, Any
from celery import Celery
from app.core.config import settings
from app.core.db import SessionLocal
from app.llm.resilience import generate_plan_with_failover
from app.models.plan import PlanRecord

logger = logging.getLogger("ai_fitness.worker")

# Initialize Celery app with Redis as message broker and result backend
celery_app = Celery(
    "ai_fitness_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

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


@celery_app.task(name="app.worker.generate_plan_task", bind=True)
def generate_plan_task(self, user_id: int, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background Celery task that:
    1. Invokes the LLM failover engine to generate a multi-week plan.
    2. Persists the PlanRecord into PostgreSQL.
    3. Returns metadata including the new plan_id.
    """
    logger.info(f"Task {self.request.id} started: generating plan for user_id={user_id}")

    # Generate plan with multi-provider failover
    plan, provider_name, retries = generate_plan_with_failover(inputs=inputs)

    # Persist in DB using a dedicated worker session
    db = SessionLocal()
    try:
        plan_record = PlanRecord(
            user_id=user_id,
            inputs=inputs,
            plan=plan.model_dump(),
            provider=provider_name,
            is_active=False,
        )
        db.add(plan_record)
        db.commit()
        db.refresh(plan_record)

        logger.info(
            f"Task {self.request.id} completed: plan_id={plan_record.id} created via provider={provider_name}"
        )
        return {
            "plan_id": plan_record.id,
            "provider": provider_name,
            "retries": retries,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Task {self.request.id} DB insertion failed: {str(exc)}")
        raise exc
    finally:
        db.close()
