import logging
from datetime import date
from typing import Dict, Any, Optional
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.db import SessionLocal
from app.llm.resilience import generate_plan_with_failover
from app.models.briefing import Briefing
from app.models.plan import PlanRecord
from app.models.user import User

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

# Celery Beat schedule for periodic jobs
celery_app.conf.beat_schedule = {
    "daily-morning-briefing": {
        "task": "app.worker.generate_daily_briefings",
        "schedule": crontab(hour=7, minute=0),
    },
}


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


def generate_briefing_for_user(db, user_id: int, target_date: date) -> Briefing:
    """
    Generates and persists a daily briefing for a specific user and date.
    Idempotent: if a briefing already exists for this (user_id, target_date), returns it.
    """
    existing = (
        db.query(Briefing)
        .filter(Briefing.user_id == user_id, Briefing.date == target_date)
        .first()
    )
    if existing:
        return existing

    # Find active plan or most recent plan
    plan_record = (
        db.query(PlanRecord)
        .filter(PlanRecord.user_id == user_id, PlanRecord.is_active == True)
        .first()
    )
    if not plan_record:
        plan_record = (
            db.query(PlanRecord)
            .filter(PlanRecord.user_id == user_id)
            .order_by(PlanRecord.created_at.desc())
            .first()
        )

    if plan_record and "weeks" in plan_record.plan:
        plan_data = plan_record.plan
        weeks = plan_data.get("weeks", [])
        if weeks:
            weekday = target_date.weekday()
            current_week = weeks[0]
            days = current_week.get("days", [])
            if weekday < len(days):
                day = days[weekday]
                exercises = [ex.get("name") for ex in day.get("exercises", [])]
                ex_str = ", ".join(exercises[:3]) if exercises else "custom exercises"
                summary = (
                    f"Good morning! Today's planned focus is {day.get('focus', 'Workout')} "
                    f"({day.get('name', 'Day')}). Target exercises: {ex_str}. Stay hydrated and focus on proper form!"
                )
            else:
                summary = (
                    "Good morning! Today is scheduled as a rest and recovery day. "
                    "Focus on mobility, hydration, and nutrition so you can recharge for your next session."
                )
        else:
            summary = "Good morning! Stay active and keep moving toward your fitness goals today!"
    else:
        summary = (
            "Good morning! You don't have an active workout plan yet. "
            "Generate a personalized multi-week plan to reach your goals faster!"
        )

    briefing = Briefing(
        user_id=user_id,
        date=target_date,
        summary=summary,
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing


@celery_app.task(name="app.worker.generate_daily_briefings")
def generate_daily_briefings(target_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Periodic task (scheduled daily at 07:00 UTC) that iterates through users
    and generates daily workout briefings.
    """
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = date.today()

    db = SessionLocal()
    created_count = 0
    try:
        users = db.query(User).all()
        logger.info(f"Generating daily briefings for {len(users)} users for {target_date}")
        for user in users:
            generate_briefing_for_user(db, user_id=user.id, target_date=target_date)
            created_count += 1
        return {
            "status": "success",
            "users_processed": created_count,
            "date": target_date.isoformat(),
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Error in generate_daily_briefings: {exc}")
        raise exc
    finally:
        db.close()
