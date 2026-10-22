from datetime import date
from unittest.mock import patch, MagicMock
import pytest

from app.models.plan import PlanRecord
from app.models.user import User
from app.schemas.plan import Plan
from app.worker import (
    celery_app,
    generate_plan_task,
    generate_daily_briefings,
    generate_weekly_reviews,
    DEAD_LETTER_LOG,
)


def sample_plan_obj():
    return Plan.model_validate({
        "goal": "Endurance",
        "level": "Intermediate",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Running",
                        "exercises": [{"name": "Intervals", "sets": 4, "reps": 400}],
                    }
                ],
            }
        ],
    })


def test_task_autoretry_transient_failure_then_succeeds(eager_celery, db_session):
    """Verify Celery task retries upon encountering transient failures and succeeds."""
    user = User(email="transient_retry@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    call_count = [0]

    def flaky_generator(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("Transient Redis/Network timeout")
        return sample_plan_obj(), "groq", 0

    with patch("app.worker.generate_plan_with_failover", side_effect=flaky_generator):
        async_result = generate_plan_task.delay(
            user_id=user.id,
            inputs={"goal": "Endurance", "level": "Intermediate"},
        )

    assert async_result.state == "SUCCESS"
    assert call_count[0] == 3
    assert async_result.result["plan_id"] is not None


def test_task_exhausts_retries_and_logs_to_dead_letter(eager_celery, db_session):
    """Verify Celery task logs structured context to dead-letter storage when all retries fail."""
    DEAD_LETTER_LOG.clear()

    user = User(email="permanent_fail@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with patch(
        "app.worker.generate_plan_with_failover",
        side_effect=RuntimeError("Unrecoverable database corruption"),
    ):
        async_result = generate_plan_task.delay(
            user_id=user.id,
            inputs={"goal": "Strength", "level": "Beginner"},
        )

    assert async_result.state == "FAILURE"
    assert "Unrecoverable database corruption" in str(async_result.result)

    # Verify dead-letter logging caught the exhausted failure
    assert len(DEAD_LETTER_LOG) >= 1
    dlq_entry = DEAD_LETTER_LOG[-1]
    assert dlq_entry["task_name"] == "app.worker.generate_plan_task"
    assert dlq_entry["exception_type"] == "RuntimeError"
    assert "Unrecoverable database corruption" in dlq_entry["exception_message"]
    assert str(user.id) in str(dlq_entry["kwargs"])


def test_plan_generation_idempotency_key_prevents_duplicate_records(eager_celery, db_session):
    """Verify re-running a plan generation task with the same idempotency key returns cached record."""
    user = User(email="idempotent_plan@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    inputs = {
        "goal": "Hypertrophy",
        "level": "Advanced",
        "idempotency_key": "unique-client-key-999",
    }

    with patch("app.worker.generate_plan_with_failover", return_value=(sample_plan_obj(), "gemini", 0)):
        # First execution: creates new record
        res1 = generate_plan_task.delay(user_id=user.id, inputs=inputs)
        assert res1.state == "SUCCESS"
        plan_id_1 = res1.result["plan_id"]
        assert "cached" not in res1.result

        # Second execution (e.g. network retry from client): should return existing record
        res2 = generate_plan_task.delay(user_id=user.id, inputs=inputs)
        assert res2.state == "SUCCESS"
        assert res2.result["plan_id"] == plan_id_1
        assert res2.result.get("cached") is True

    # Confirm only 1 PlanRecord exists in database
    total_plans = (
        db_session.query(PlanRecord)
        .filter(PlanRecord.user_id == user.id)
        .count()
    )
    assert total_plans == 1


def test_daily_briefings_and_weekly_reviews_leave_clean_idempotent_state(eager_celery, db_session):
    """Verify executing daily and weekly batch jobs repeatedly leaves clean state with no duplicates."""
    today = date.today()
    user = User(email="batch_idempotent@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    # Run daily briefings 3 times
    generate_daily_briefings(target_date_str=today.isoformat())
    generate_daily_briefings(target_date_str=today.isoformat())
    generate_daily_briefings(target_date_str=today.isoformat())

    # Run weekly reviews 3 times
    generate_weekly_reviews(end_date_str=today.isoformat())
    generate_weekly_reviews(end_date_str=today.isoformat())
    generate_weekly_reviews(end_date_str=today.isoformat())

    # Verify no unhandled exceptions and exactly 1 record each
    from app.models.briefing import Briefing
    from app.models.review import WeeklyReview

    assert db_session.query(Briefing).filter(Briefing.user_id == user.id, Briefing.date == today).count() == 1
    assert db_session.query(WeeklyReview).filter(WeeklyReview.user_id == user.id, WeeklyReview.end_date == today).count() == 1
