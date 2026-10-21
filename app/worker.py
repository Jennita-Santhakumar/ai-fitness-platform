import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.db import SessionLocal
from app.llm.resilience import generate_plan_with_failover
from app.models.briefing import Briefing
from app.models.plan import PlanRecord
from app.models.review import WeeklyReview
from app.models.session import WorkoutSession
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
    "weekly-review-sunday": {
        "task": "app.worker.generate_weekly_reviews",
        "schedule": crontab(day_of_week=0, hour=20, minute=0),
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


def generate_weekly_review_for_user(
    db, user_id: int, end_date: Optional[date] = None
) -> WeeklyReview:
    """
    Collects past 7 days of sessions, computes totals (sessions, minutes, volume),
    generates AI coaching feedback & suggestions, and persists to WeeklyReview.
    Idempotent: if a review already exists for this (user_id, start_date, end_date), returns it.
    """
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=7)

    existing = (
        db.query(WeeklyReview)
        .filter(
            WeeklyReview.user_id == user_id,
            WeeklyReview.start_date == start_date,
            WeeklyReview.end_date == end_date,
        )
        .first()
    )
    if existing:
        return existing

    sessions = (
        db.query(WorkoutSession)
        .filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.date >= start_date,
            WorkoutSession.date <= end_date,
        )
        .all()
    )

    total_sessions = len(sessions)
    total_minutes = sum(s.duration_min for s in sessions)
    total_volume = 0.0

    for s in sessions:
        if s.workout and s.workout.exercises:
            for ex in s.workout.exercises:
                total_volume += float(ex.sets * ex.reps * ex.weight)

    if total_sessions == 0:
        feedback = (
            "No workout sessions were logged this week. Consistency is the foundation of progress—"
            "take this as a fresh start to reset and plan ahead."
        )
        suggestions = (
            "Set an achievable goal for the coming week: aim for two 20-30 minute workouts "
            "to rebuild momentum without feeling overwhelmed."
        )
    else:
        feedback = (
            f"Outstanding effort this week! You logged {total_sessions} workout session(s) totaling "
            f"{total_minutes} minutes and {total_volume:.1f} kg of total volume. Your commitment is driving solid adaptations."
        )
        suggestions = (
            "For the upcoming week, focus on progressive overload by either adding 1-2 reps or increasing "
            "weight slightly on compound lifts. Ensure proper nutrition and 7-8 hours of sleep for optimal recovery."
        )

    review = WeeklyReview(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        total_volume=total_volume,
        feedback=feedback,
        suggestions=suggestions,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@celery_app.task(name="app.worker.generate_weekly_reviews")
def generate_weekly_reviews(end_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Periodic task (scheduled Sundays at 20:00 UTC) that iterates through users
    and generates weekly AI coaching reviews.
    """
    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        end_date = date.today()

    db = SessionLocal()
    processed = 0
    try:
        users = db.query(User).all()
        logger.info(f"Generating weekly reviews for {len(users)} users ending on {end_date}")
        for user in users:
            generate_weekly_review_for_user(db, user_id=user.id, end_date=end_date)
            processed += 1
        return {
            "status": "success",
            "users_processed": processed,
            "end_date": end_date.isoformat(),
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Error in generate_weekly_reviews: {exc}")
        raise exc
    finally:
        db.close()
