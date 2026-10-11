from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ExerciseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the exercise")
    sets: int = Field(default=3, ge=1, description="Number of sets")
    reps: int = Field(default=10, ge=1, description="Number of repetitions per set")
    weight: float = Field(default=0.0, ge=0.0, description="Weight used in kg or lbs")


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sets: Optional[int] = Field(None, ge=1)
    reps: Optional[int] = Field(None, ge=1)
    weight: Optional[float] = Field(None, ge=0.0)


class ExerciseRead(ExerciseBase):
    id: int
    workout_id: int

    model_config = ConfigDict(from_attributes=True)
