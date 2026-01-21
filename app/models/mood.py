"""
Models for Student Mood Tracking (Emotion Diary).
Tracks daily mood check-ins with notes.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class MoodEntry(Base):
    """
    Daily mood entry from student.
    
    Stores mood value (20-100) with optional notes.
    Used for emotion tracking and analytics.
    """
    __tablename__ = "mood_entries"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Mood value: 20 (angry) to 100 (great)
    mood_value: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Optional note from student
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Date of mood (YYYY-MM-DD) - for querying
    mood_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<MoodEntry(user_id={self.user_id}, mood={self.mood_value}, date={self.mood_date})>"
