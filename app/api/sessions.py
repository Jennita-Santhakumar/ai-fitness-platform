from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.session import WorkoutSession
from app.models.user import User
from app.models.workout import Workout
from app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionRead,
)

router = APIRouter(prefix="/sessions", tags=["Workout Sessions"])


@router.post(
    "",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a completed workout session",
)
def create_session(
    session_in: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # If a workout_id is specified, verify it belongs to this user
    if session_in.workout_id:
        workout = (
            db.query(Workout)
            .filter(Workout.id == session_in.workout_id, Workout.user_id == current_user.id)
            .first()
        )
        if not workout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced workout does not exist",
            )

    session = WorkoutSession(
        user_id=current_user.id,
        workout_id=session_in.workout_id,
        date=session_in.date,
        duration_min=session_in.duration_min,
        notes=session_in.notes,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "",
    response_model=List[SessionRead],
    summary="List all logged workout sessions for the authenticated user",
)
def list_sessions(
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Items to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.user_id == current_user.id)
        .order_by(WorkoutSession.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return sessions


@router.get(
    "/{session_id}",
    response_model=SessionRead,
    summary="Get details of a logged session",
)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.id == session_id, WorkoutSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


@router.patch(
    "/{session_id}",
    response_model=SessionRead,
    summary="Update a logged session",
)
def update_session(
    session_id: int,
    session_in: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.id == session_id, WorkoutSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # If updating workout_id, verify ownership of the new workout
    if session_in.workout_id:
        workout = (
            db.query(Workout)
            .filter(Workout.id == session_in.workout_id, Workout.user_id == current_user.id)
            .first()
        )
        if not workout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced workout does not exist",
            )

    update_data = session_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a logged session",
)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.id == session_id, WorkoutSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    db.delete(session)
    db.commit()
    return None
