from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class WeeklyReviewRead(BaseModel):
    """Schema for returning weekly AI coaching summaries."""
    id: int
    user_id: int
    start_date: date
    end_date: date
    total_sessions: int
    total_minutes: int
    total_volume: float
    feedback: str
    suggestions: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
