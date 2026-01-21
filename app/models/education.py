"""
Models for Module 4 - Preventive Education & Positive Mental Health.
Educational content, exercises, booklets, minigames, and daily messages.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Any

from sqlalchemy import BigInteger, String, Text, Boolean, Integer, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EducationContent(Base, TimestampMixin):
    """
    Educational content item.
    
    Types: EXERCISE, BOOKLET, VIDEO, ARTICLE, MINIGAME
    Topics: stress, anxiety, bullying, kindness, confidence, emotional_regulation
    """
    __tablename__ = "education_contents"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(50), nullable=False)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    questions: Mapped[list["ExerciseQuestion"]] = relationship(
        "ExerciseQuestion",
        back_populates="content",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<EducationContent(id={self.id}, type='{self.content_type}', title='{self.title}')>"


class ExerciseQuestion(Base):
    """
    Quiz question for EXERCISE type content.
    """
    __tablename__ = "exercise_questions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("education_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    content: Mapped["EducationContent"] = relationship(
        "EducationContent",
        back_populates="questions",
    )
    
    def __repr__(self) -> str:
        return f"<ExerciseQuestion(id={self.id}, content_id={self.content_id})>"


class ExerciseAttempt(Base):
    """
    Student's exercise completion record.
    """
    __tablename__ = "exercise_attempts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("education_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    content: Mapped["EducationContent"] = relationship("EducationContent", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ExerciseAttempt(id={self.id}, user_id={self.user_id}, score={self.score})>"


class BookletRead(Base):
    """
    Student's booklet reading progress.
    """
    __tablename__ = "booklet_reads"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("education_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    content: Mapped["EducationContent"] = relationship("EducationContent", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<BookletRead(id={self.id}, progress={self.progress_percent}%)>"


class MinigameResult(Base):
    """
    Minigame play result with gamification.
    """
    __tablename__ = "minigame_results"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("education_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    played_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    content: Mapped["EducationContent"] = relationship("EducationContent", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<MinigameResult(id={self.id}, score={self.score}, points={self.reward_points})>"


class DailyKindMessage(Base):
    """
    Daily positive message for students.
    """
    __tablename__ = "daily_kind_messages"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    active_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    responses: Mapped[list["DailyKindResponse"]] = relationship(
        "DailyKindResponse",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<DailyKindMessage(id={self.id}, date={self.active_date})>"


class DailyKindResponse(Base):
    """
    Student's response to daily kind message.
    """
    __tablename__ = "daily_kind_responses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("daily_kind_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    message: Mapped["DailyKindMessage"] = relationship(
        "DailyKindMessage",
        back_populates="responses",
    )
    
    def __repr__(self) -> str:
        return f"<DailyKindResponse(id={self.id}, user_id={self.user_id})>"
