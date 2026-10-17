from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExerciseItem(BaseModel):
    """Individual exercise inside a planned workout day."""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the exercise")
    sets: int = Field(..., gt=0, description="Number of sets (must be > 0)")
    reps: int = Field(..., gt=0, description="Target repetitions per set (must be > 0)")
    rest_sec: int = Field(default=60, ge=0, description="Rest period between sets in seconds")
    notes: Optional[str] = Field(None, description="Coaching cues, tempo, or target RPE")


class Day(BaseModel):
    """A single day's workout within a week."""
    name: str = Field(..., min_length=1, max_length=100, description="Day name, e.g. 'Day 1' or 'Monday'")
    focus: str = Field(..., min_length=1, max_length=255, description="Main training focus, e.g. 'Push Power' or 'Lower Hypertrophy'")
    exercises: List[ExerciseItem] = Field(..., min_length=1, description="List of planned exercises for this day")


class Week(BaseModel):
    """A training week containing planned workout days."""
    number: int = Field(..., ge=1, le=12, description="Week sequence number (1-12)")
    days: List[Day] = Field(..., min_length=1, max_length=7, description="Workout days in this week (1-7 days)")


class Plan(BaseModel):
    """
    Root multi-week workout plan schema.
    Validated strictly against LLM generation output.
    """
    goal: str = Field(..., min_length=1, max_length=255, description="Primary fitness objective (e.g., Hypertrophy, Strength, Fat Loss)")
    level: str = Field(..., min_length=1, max_length=100, description="Experience level (Beginner, Intermediate, Advanced)")
    weeks: List[Week] = Field(..., min_length=1, max_length=12, description="List of multi-week training schedules (1-12 weeks)")

    @field_validator("weeks")
    @classmethod
    def validate_weeks_non_empty(cls, v: List[Week]) -> List[Week]:
        if not (1 <= len(v) <= 12):
            raise ValueError("Plan must contain between 1 and 12 weeks.")
        return v
