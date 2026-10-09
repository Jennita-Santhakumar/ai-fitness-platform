from datetime import date, datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Date, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workout import Workout


class WorkoutSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workouts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    workout: Mapped[Optional["Workout"]] = relationship("Workout", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<WorkoutSession id={self.id} user_id={self.user_id} date={self.date}>"
