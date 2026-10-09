from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.workout import Workout


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    workout: Mapped["Workout"] = relationship("Workout", back_populates="exercises")

    def __repr__(self) -> str:
        return f"<Exercise id={self.id} name={self.name} sets={self.sets} reps={self.reps}>"
