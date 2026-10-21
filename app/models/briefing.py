from datetime import datetime, date
from sqlalchemy import Column, Integer, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Briefing(Base):
    """
    Stores generated daily workout briefings for users.
    Each user has at most one briefing per calendar date (enforced by unique constraint).
    """
    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="briefings")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_briefing_date"),
    )
