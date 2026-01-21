"""
Models for Module 3 - AI Psychological Chatbot.
Chat sessions and messages with risk detection metadata.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ChatSession(Base, TimestampMixin):
    """
    Chat session between a student and the AI chatbot.
    
    Attributes:
        id: Primary key
        user_id: Student who owns this session
        school_id: Student's school (optional, for context)
        status: ACTIVE or ENDED
        started_at: When session started
        ended_at: When session ended (null if active)
        last_risk_level: Cached risk level from latest message
        last_risk_type: Cached risk type from latest message
        last_escalation_action: Last recommended action
    """
    __tablename__ = "chat_sessions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    school_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
    )
    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_risk_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_escalation_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # LangChain conversation summary (thay vì lưu hết messages)
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions", lazy="selectin")
    school: Mapped["School | None"] = relationship("School", lazy="selectin")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class ChatMessage(Base):
    """
    Individual message in a chat session.
    
    Attributes:
        id: Primary key
        session_id: Parent chat session
        sender_type: USER or AI
        sender_user_id: User ID if sender is USER
        content: Message text content
        risk_level: Detected risk level (LOW/MEDIUM/HIGH/CRITICAL)
        risk_type: Type of risk (EMOTIONAL/BULLYING/SELF_HARM/OTHER)
        is_sensitive: Flag for sensitive content
        signals: JSON of matched risk patterns for audit
        created_at: When message was created
    """
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # USER, AI
    sender_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    sender: Mapped["User | None"] = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, sender_type='{self.sender_type}', risk_level='{self.risk_level}')>"
