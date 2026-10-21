from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.briefing import Briefing
from app.models.user import User
from app.schemas.briefing import BriefingRead

router = APIRouter(prefix="/briefings", tags=["Daily Briefings"])


@router.get(
    "/today",
    response_model=BriefingRead,
    summary="Get today's workout briefing",
    description="Returns today's personalized workout briefing for the authenticated user.",
)
def get_today_briefing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves today's briefing for the current authenticated user.
    Returns 404 if the morning scheduled briefing task has not run yet.
    """
    today = date.today()
    briefing = (
        db.query(Briefing)
        .filter(Briefing.user_id == current_user.id, Briefing.date == today)
        .first()
    )
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No briefing generated for today yet",
        )

    return briefing
