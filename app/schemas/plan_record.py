from datetime import date, datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class PlanGenerateRequest(BaseModel):
    """Input payload for generating a multi-week workout plan."""
    goal: str = Field(..., min_length=1, max_length=100, description="Primary goal (e.g. Strength, Fat Loss)")
    level: str = Field("Intermediate", min_length=1, max_length=50, description="Experience level")
    equipment: str = Field("Full Gym", min_length=1, max_length=200, description="Available workout equipment")
    days_per_week: int = Field(3, ge=1, le=7, description="Target training days per week (1-7)")
    weeks: int = Field(4, ge=1, le=12, description="Target duration in weeks (1-12)")
    injuries: Optional[str] = Field("None", max_length=500, description="Injuries or physical constraints")


class PlanRecordRead(BaseModel):
    """Response representation of a persisted PlanRecord."""
    id: int
    user_id: int
    inputs: Dict[str, Any]
    plan: Dict[str, Any]
    provider: str
    is_active: bool
    start_date: Optional[date]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
