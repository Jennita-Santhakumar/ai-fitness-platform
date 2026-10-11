from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.exercise import ExerciseRead


class WorkoutBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Workout title")
    notes: Optional[str] = Field(None, description="Optional workout description or notes")


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    notes: Optional[str] = None


class WorkoutRead(WorkoutBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkoutDetailRead(WorkoutRead):
    exercises: List[ExerciseRead] = []
