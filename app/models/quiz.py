"""
Model Quiz - He thong quiz kieu Candy Crush.
Mo khoa tuan tu, danh gia sao, theo doi tien do.

DB columns mapping (match Supabase schema):
- quiz_level_progress: attempts, is_completed, completed_at, last_played_at
- quiz_attempts: correct_answers, completed_at
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QuizLevel(Base, TimestampMixin):
    """
    Bang quiz_levels - Moi level la mot man choi (nhu Candy Crush).
    """
    __tablename__ = "quiz_levels"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    set_title: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSONB, default=[])
    unlock_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    
    # Relationships
    questions: Mapped[list["QuizQuestion"]] = relationship(
        "QuizQuestion",
        back_populates="level",
        lazy="selectin",
        order_by="QuizQuestion.order_index",
    )
    
    def __repr__(self) -> str:
        return f"<QuizLevel(id={self.id}, file_id='{self.file_id}')>"


class QuizQuestion(Base, TimestampMixin):
    """
    Bang quiz_questions - Cau hoi trong moi level.
    """
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("level_id", "question_id", name="uq_quiz_questions_level_question"),
    )
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("quiz_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[str] = mapped_column(String(50), nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB, default=[])
    correct_option_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    correct_option_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    interaction: Mapped[dict | None] = mapped_column(JSONB, default={})
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Relationships
    level: Mapped["QuizLevel"] = relationship(
        "QuizLevel",
        back_populates="questions",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<QuizQuestion(id={self.id}, qid='{self.question_id}')>"


class QuizLevelProgress(Base, TimestampMixin):
    """
    Bang quiz_level_progress - Tien do cua hoc sinh tren tung level.
    
    DB columns: id, user_id, level_id, is_unlocked, is_completed,
                best_score, stars, attempts, last_played_at, completed_at,
                created_at, updated_at, first_completed_at, last_attempted_at
    """
    __tablename__ = "quiz_level_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "level_id", name="uq_quiz_progress_user_level"),
    )
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("quiz_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    best_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stars: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_played_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    first_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<QuizLevelProgress(user={self.user_id}, level={self.level_id}, stars={self.stars})>"


class QuizAttempt(Base):
    """
    Bang quiz_attempts - Moi lan lam quiz.
    
    DB columns: id, user_id, level_id, score, stars,
                total_questions, correct_answers, duration_seconds,
                answers, completed_at, attempted_at
    """
    __tablename__ = "quiz_attempts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("quiz_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    stars: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answers: Mapped[dict | None] = mapped_column(JSONB, default={})
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<QuizAttempt(id={self.id}, user={self.user_id}, score={self.score})>"
