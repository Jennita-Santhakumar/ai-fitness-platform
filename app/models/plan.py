from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class PlanRecord(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    plan: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="plans")

    def __repr__(self) -> str:
        return f"<PlanRecord id={self.id} user_id={self.user_id} provider={self.provider}>"
