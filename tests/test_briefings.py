from datetime import date
import pytest
from app.models.briefing import Briefing
from app.models.plan import PlanRecord
from app.models.user import User
from app.worker import celery_app, generate_daily_briefings, generate_briefing_for_user


def test_celery_beat_schedule_configured():
    """Verify Celery Beat schedule contains the daily 07:00 briefing task."""
    assert "daily-morning-briefing" in celery_app.conf.beat_schedule
    schedule_entry = celery_app.conf.beat_schedule["daily-morning-briefing"]
    assert schedule_entry["task"] == "app.worker.generate_daily_briefings"
    assert schedule_entry["schedule"].hour == {7}
    assert schedule_entry["schedule"].minute == {0}


def test_generate_daily_briefings_task_creates_row(db_session):
    """Verify generate_daily_briefings creates a briefing record for users with active plans."""
    today = date.today()

    # Create user
    user = User(email="athlete_briefing@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create active plan
    plan_record = PlanRecord(
        user_id=user.id,
        inputs={"goal": "Hypertrophy", "level": "Intermediate"},
        plan={
            "goal": "Hypertrophy",
            "level": "Intermediate",
            "weeks": [
                {
                    "number": 1,
                    "days": [
                        {
                            "name": "Day 1",
                            "focus": "Chest & Triceps",
                            "exercises": [{"name": "Barbell Bench Press", "sets": 3, "reps": 10}],
                        }
                    ],
                }
            ],
        },
        provider="groq",
        is_active=True,
    )
    db_session.add(plan_record)
    db_session.commit()

    # Execute task
    result = generate_daily_briefings(target_date_str=today.isoformat())
    assert result["status"] == "success"
    assert result["users_processed"] >= 1

    # Verify DB row
    briefing = (
        db_session.query(Briefing)
        .filter(Briefing.user_id == user.id, Briefing.date == today)
        .first()
    )
    assert briefing is not None
    assert briefing.user_id == user.id
    assert briefing.date == today
    assert "Good morning!" in briefing.summary


def test_generate_daily_briefings_idempotency(db_session):
    """Verify running generate_daily_briefings multiple times on the same date produces no duplicates."""
    today = date.today()

    user = User(email="idempotent_briefing@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # First run
    generate_daily_briefings(target_date_str=today.isoformat())

    # Second run on the exact same date
    generate_daily_briefings(target_date_str=today.isoformat())

    # Count rows for user and date
    count = (
        db_session.query(Briefing)
        .filter(Briefing.user_id == user.id, Briefing.date == today)
        .count()
    )
    assert count == 1


def test_get_today_briefing_endpoint_flow(client, auth_headers, db_session):
    """Verify full flow: 404 before briefing task runs -> task runs -> 200 returned."""
    headers = auth_headers("briefing_endpoint_user@example.com")
    today = date.today()

    # 1. Before task runs: returns 404
    res_before = client.get("/briefings/today", headers=headers)
    assert res_before.status_code == 404
    assert res_before.json()["detail"] == "No briefing generated for today yet"

    # 2. Run background task
    generate_daily_briefings(target_date_str=today.isoformat())

    # 3. After task runs: returns 200
    res_after = client.get("/briefings/today", headers=headers)
    assert res_after.status_code == 200
    briefing_data = res_after.json()
    assert briefing_data["date"] == today.isoformat()
    assert len(briefing_data["summary"]) > 0
    assert "id" in briefing_data


def test_get_today_briefing_ownership_isolation(client, auth_headers, db_session):
    """Verify User B cannot see User A's briefing."""
    headers_a = auth_headers("user_a_briefing@example.com")
    headers_b = auth_headers("user_b_briefing@example.com")
    today = date.today()

    user_a = db_session.query(User).filter(User.email == "user_a_briefing@example.com").first()

    # Manually create a briefing for User A only
    briefing_a = Briefing(
        user_id=user_a.id,
        date=today,
        summary="User A's specific custom morning briefing",
    )
    db_session.add(briefing_a)
    db_session.commit()

    # User A accesses today's briefing -> 200
    res_a = client.get("/briefings/today", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["summary"] == "User A's specific custom morning briefing"

    # User B accesses today's briefing -> 404
    res_b = client.get("/briefings/today", headers=headers_b)
    assert res_b.status_code == 404


def test_get_today_briefing_unauthenticated(client):
    """Verify unauthenticated requests return 401."""
    res = client.get("/briefings/today")
    assert res.status_code == 401
