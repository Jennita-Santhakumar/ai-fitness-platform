from datetime import date, datetime
from sqlalchemy import Column, Integer, Float, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class WeeklyReview(Base):
    """
    Stores weekly AI performance summaries and coaching reviews.
    Aggregates completed sessions over a 7-day period with AI feedback and actionable suggestions.
    """
    __tablename__ = "weekly_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False, index=True)
    total_sessions = Column(Integer, nullable=False, default=0)
    total_minutes = Column(Integer, nullable=False, default=0)
    total_volume = Column(Float, nullable=False, default=0.0)
    feedback = Column(Text, nullable=False)
    suggestions = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="weekly_reviews")

    __table_args__ = (
        UniqueConstraint("user_id", "start_date", "end_date", name="uq_user_weekly_review_period"),
    )
