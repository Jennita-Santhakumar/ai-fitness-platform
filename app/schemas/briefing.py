from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class BriefingRead(BaseModel):
    """Schema for returning daily workout briefings."""
    id: int
    user_id: int
    date: date
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
