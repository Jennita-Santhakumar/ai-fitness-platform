from datetime import date, timedelta
import pytest

from app.models.exercise import Exercise
from app.models.review import WeeklyReview
from app.models.session import WorkoutSession
from app.models.user import User
from app.models.workout import Workout
from app.worker import celery_app, generate_weekly_reviews, generate_weekly_review_for_user


def test_celery_beat_schedule_weekly_review():
    """Verify Celery Beat schedule contains the weekly Sunday 20:00 task."""
    assert "weekly-review-sunday" in celery_app.conf.beat_schedule
    schedule_entry = celery_app.conf.beat_schedule["weekly-review-sunday"]
    assert schedule_entry["task"] == "app.worker.generate_weekly_reviews"
    assert schedule_entry["schedule"].day_of_week == {0}
    assert schedule_entry["schedule"].hour == {20}
    assert schedule_entry["schedule"].minute == {0}


def test_generate_weekly_review_from_real_sessions(db_session):
    """Verify review computes accurate metrics (sessions, minutes, volume) from real session data."""
    today = date.today()

    # Create user
    user = User(email="athlete_review@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create workout with 2 exercises
    workout = Workout(user_id=user.id, title="Legs & Chest")
    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)

    # Squat: 3 sets * 10 reps * 100 kg = 3,000 kg
    ex1 = Exercise(workout_id=workout.id, name="Back Squat", sets=3, reps=10, weight=100.0)
    # Bench Press: 3 sets * 10 reps * 80 kg = 2,400 kg
    ex2 = Exercise(workout_id=workout.id, name="Bench Press", sets=3, reps=10, weight=80.0)
    db_session.add_all([ex1, ex2])
    db_session.commit()

    # Create 2 sessions within the last 7 days (total 110 mins, total volume 2 * 5,400 = 10,800 kg)
    session1 = WorkoutSession(
        user_id=user.id,
        workout_id=workout.id,
        date=today - timedelta(days=2),
        duration_min=50,
    )
    session2 = WorkoutSession(
        user_id=user.id,
        workout_id=workout.id,
        date=today - timedelta(days=4),
        duration_min=60,
    )
    db_session.add_all([session1, session2])
    db_session.commit()

    # Execute weekly review task
    result = generate_weekly_reviews(end_date_str=today.isoformat())
    assert result["status"] == "success"
    assert result["users_processed"] >= 1

    # Verify Review DB row
    review = (
        db_session.query(WeeklyReview)
        .filter(WeeklyReview.user_id == user.id, WeeklyReview.end_date == today)
        .first()
    )
    assert review is not None
    assert review.total_sessions == 2
    assert review.total_minutes == 110
    assert review.total_volume == 10800.0
    assert "2 workout session(s)" in review.feedback
    assert "10800.0 kg" in review.feedback
    assert len(review.suggestions) > 0


def test_generate_weekly_review_zero_sessions(db_session):
    """Verify appropriate feedback is generated when an athlete logs 0 sessions."""
    today = date.today()

    user = User(email="inactive_user@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    generate_weekly_reviews(end_date_str=today.isoformat())

    review = (
        db_session.query(WeeklyReview)
        .filter(WeeklyReview.user_id == user.id, WeeklyReview.end_date == today)
        .first()
    )
    assert review is not None
    assert review.total_sessions == 0
    assert review.total_minutes == 0
    assert review.total_volume == 0.0
    assert "No workout sessions were logged this week" in review.feedback
    assert "aim for two 20-30 minute workouts" in review.suggestions


def test_weekly_review_idempotency(db_session):
    """Verify running generate_weekly_reviews twice on the same period produces no duplicate rows."""
    today = date.today()

    user = User(email="idempotent_review_user@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    generate_weekly_reviews(end_date_str=today.isoformat())
    generate_weekly_reviews(end_date_str=today.isoformat())

    count = (
        db_session.query(WeeklyReview)
        .filter(WeeklyReview.user_id == user.id, WeeklyReview.end_date == today)
        .count()
    )
    assert count == 1


def test_get_latest_review_endpoint_flow(client, auth_headers, db_session):
    """Verify GET /reviews/latest returns 404 initially, then 200 after generation."""
    headers = auth_headers("review_api_user@example.com")
    today = date.today()

    # 1. Before generation -> 404
    res_before = client.get("/reviews/latest", headers=headers)
    assert res_before.status_code == 404
    assert res_before.json()["detail"] == "No weekly review found"

    # 2. Run background task
    generate_weekly_reviews(end_date_str=today.isoformat())

    # 3. After generation -> 200
    res_after = client.get("/reviews/latest", headers=headers)
    assert res_after.status_code == 200
    data = res_after.json()
    assert data["end_date"] == today.isoformat()
    assert "total_sessions" in data
    assert "feedback" in data
    assert "suggestions" in data


def test_get_latest_review_ownership_isolation(client, auth_headers, db_session):
    """Verify User B cannot see User A's weekly review."""
    headers_a = auth_headers("athlete_a_rev@example.com")
    headers_b = auth_headers("athlete_b_rev@example.com")
    today = date.today()

    user_a = db_session.query(User).filter(User.email == "athlete_a_rev@example.com").first()

    # Create review for User A only
    review_a = WeeklyReview(
        user_id=user_a.id,
        start_date=today - timedelta(days=7),
        end_date=today,
        total_sessions=3,
        total_minutes=135,
        total_volume=4500.0,
        feedback="Athlete A exclusive feedback",
        suggestions="Athlete A exclusive suggestions",
    )
    db_session.add(review_a)
    db_session.commit()

    # User A gets their review -> 200
    res_a = client.get("/reviews/latest", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["feedback"] == "Athlete A exclusive feedback"

    # User B gets 404
    res_b = client.get("/reviews/latest", headers=headers_b)
    assert res_b.status_code == 404


def test_get_latest_review_unauthenticated(client):
    """Verify unauthenticated requests return 401."""
    res = client.get("/reviews/latest")
    assert res.status_code == 401
