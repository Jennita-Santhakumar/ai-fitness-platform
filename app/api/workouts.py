from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Workout
from app.schemas.exercise import ExerciseCreate, ExerciseRead
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutRead,
    WorkoutDetailRead,
)

router = APIRouter(prefix="/workouts", tags=["Workouts"])


# --- Workouts CRUD ---

@router.post(
    "",
    response_model=WorkoutRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workout routine",
)
def create_workout(
    workout_in: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = Workout(
        user_id=current_user.id,
        title=workout_in.title,
        notes=workout_in.notes,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@router.get(
    "",
    response_model=List[WorkoutRead],
    summary="List all workout routines for the authenticated user",
)
def list_workouts(
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Items to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workouts = (
        db.query(Workout)
        .filter(Workout.user_id == current_user.id)
        .order_by(Workout.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return workouts


@router.get(
    "/{workout_id}",
    response_model=WorkoutDetailRead,
    summary="Get details of a specific workout including exercises",
)
def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )
    return workout


@router.patch(
    "/{workout_id}",
    response_model=WorkoutRead,
    summary="Update a workout routine",
)
def update_workout(
    workout_id: int,
    workout_in: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    update_data = workout_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    db.commit()
    db.refresh(workout)
    return workout


@router.delete(
    "/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout routine",
)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    db.delete(workout)
    db.commit()
    return None


# --- Exercises Sub-Resource CRUD ---

@router.post(
    "/{workout_id}/exercises",
    response_model=ExerciseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exercise to a workout",
)
def add_exercise(
    workout_id: int,
    exercise_in: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify workout ownership
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    exercise = Exercise(
        workout_id=workout.id,
        name=exercise_in.name,
        sets=exercise_in.sets,
        reps=exercise_in.reps,
        weight=exercise_in.weight,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get(
    "/{workout_id}/exercises",
    response_model=List[ExerciseRead],
    summary="List all exercises in a workout",
)
def list_exercises(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    return workout.exercises


@router.delete(
    "/{workout_id}/exercises/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an exercise from a workout",
)
def delete_exercise(
    workout_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify workout ownership
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    exercise = (
        db.query(Exercise)
        .filter(Exercise.id == exercise_id, Exercise.workout_id == workout.id)
        .first()
    )
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    db.delete(exercise)
    db.commit()
    return None
