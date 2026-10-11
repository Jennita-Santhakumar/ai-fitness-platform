from datetime import date as dt_date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SessionBase(BaseModel):
    workout_id: Optional[int] = Field(None, description="Optional ID of associated workout routine")
    date: dt_date = Field(default_factory=dt_date.today, description="Date session took place")
    duration_min: int = Field(default=45, ge=1, le=1440, description="Duration in minutes")
    notes: Optional[str] = Field(None, description="Training feedback or notes")


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    workout_id: Optional[int] = None
    date: Optional[dt_date] = None
    duration_min: Optional[int] = Field(None, ge=1, le=1440)
    notes: Optional[str] = None


class SessionRead(SessionBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
