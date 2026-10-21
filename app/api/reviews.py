from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.review import WeeklyReview
from app.models.user import User
from app.schemas.review import WeeklyReviewRead

router = APIRouter(prefix="/reviews", tags=["Weekly Reviews"])


@router.get(
    "/latest",
    response_model=WeeklyReviewRead,
    summary="Get the latest weekly review for the authenticated user",
    description="Returns the most recent weekly performance review and AI coaching suggestions.",
)
def get_latest_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the most recent weekly coaching review for the current user.
    Returns 404 if no weekly reviews have been generated yet.
    """
    review = (
        db.query(WeeklyReview)
        .filter(WeeklyReview.user_id == current_user.id)
        .order_by(WeeklyReview.created_at.desc())
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly review found",
        )
    return review
