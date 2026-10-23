from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.workout import Workout
    from app.models.session import WorkoutSession
    from app.models.plan import PlanRecord


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Strava OAuth 2.0 Credentials (Day 20)
    strava_athlete_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    strava_access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    strava_refresh_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    strava_expires_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    strava_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    workouts: Mapped[List["Workout"]] = relationship(
        "Workout", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["WorkoutSession"]] = relationship(
        "WorkoutSession", back_populates="user", cascade="all, delete-orphan"
    )
    plans: Mapped[List["PlanRecord"]] = relationship(
        "PlanRecord", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
