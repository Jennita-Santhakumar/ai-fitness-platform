from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exercise import Exercise
    from app.models.session import WorkoutSession


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="workouts")
    exercises: Mapped[List["Exercise"]] = relationship(
        "Exercise", back_populates="workout", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["WorkoutSession"]] = relationship(
        "WorkoutSession", back_populates="workout"
    )

    def __repr__(self) -> str:
        return f"<Workout id={self.id} title={self.title} user_id={self.user_id}>"
