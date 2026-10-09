import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.user import User
from app.models.workout import Workout
from app.models.exercise import Exercise
from app.models.session import WorkoutSession


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for model testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_create_user_and_cascade_relationships(db_session):
    # 1. Create User
    user = User(email="athlete@example.com", hashed_password="secure_hashed_password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "athlete@example.com"
    assert user.is_active is True

    # 2. Create Workout with Exercises
    workout = Workout(user_id=user.id, title="Leg Day Power", notes="Heavy squats focus")
    exercise_1 = Exercise(name="Barbell Back Squat", sets=4, reps=8, weight=100.0)
    exercise_2 = Exercise(name="Romanian Deadlift", sets=3, reps=10, weight=80.0)
    workout.exercises.extend([exercise_1, exercise_2])

    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)

    assert len(workout.exercises) == 2
    assert workout.exercises[0].workout_id == workout.id
    assert workout.user.email == "athlete@example.com"

    # 3. Log a Session
    session = WorkoutSession(
        user_id=user.id,
        workout_id=workout.id,
        date=date(2026, 10, 8),
        duration_min=50,
        notes="Felt energetic, hit all reps",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user.id == user.id
    assert session.workout.title == "Leg Day Power"

    # 4. Verify Cascade: Deleting Workout removes attached Exercises
    db_session.delete(workout)
    db_session.commit()

    remaining_exercises = db_session.query(Exercise).all()
    assert len(remaining_exercises) == 0
