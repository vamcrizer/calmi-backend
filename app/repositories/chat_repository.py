"""
Repositories for Module 3 - Chat.
Data access layer for chat sessions and messages.
"""
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession, ChatMessage
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """Repository for chat sessions."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ChatSession, session)
    
    async def create_session(
        self,
        user_id: int,
        school_id: int | None = None,
    ) -> ChatSession:
        """Create a new chat session."""
        return await self.create({
            "user_id": user_id,
            "school_id": school_id,
            "status": "ACTIVE",
            "started_at": datetime.utcnow(),
        })
    
    async def list_sessions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChatSession]:
        """List sessions for a user, ordered by started_at descending."""
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.started_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_sessions(self, user_id: int) -> int:
        """Count total sessions for a user."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(ChatSession.id))
            .where(ChatSession.user_id == user_id)
        )
        return result.scalar() or 0
    
    async def get_session_by_id(self, session_id: int) -> ChatSession | None:
        """Get session by ID with messages loaded."""
        result = await self.session.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def end_session(self, session_id: int) -> ChatSession | None:
        """Mark session as ended."""
        session = await self.get_by_id(session_id)
        if session:
            session.status = "ENDED"
            session.ended_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session
    
    async def update_session_risk(
        self,
        session_id: int,
        last_risk_level: str,
        last_risk_type: str,
        last_escalation_action: str | None = None,
    ) -> ChatSession | None:
        """Update cached risk info on session."""
        session = await self.get_by_id(session_id)
        if session:
            session.last_risk_level = last_risk_level
            session.last_risk_type = last_risk_type
            session.last_escalation_action = last_escalation_action
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for chat messages."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ChatMessage, session)
    
    async def create_message(
        self,
        session_id: int,
        sender_type: str,
        content: str,
        sender_user_id: int | None = None,
        risk_level: str | None = None,
        risk_type: str | None = None,
        is_sensitive: bool = False,
        signals: dict | None = None,
    ) -> ChatMessage:
        """Create a new message."""
        return await self.create({
            "session_id": session_id,
            "sender_type": sender_type,
            "sender_user_id": sender_user_id,
            "content": content,
            "risk_level": risk_level,
            "risk_type": risk_type,
            "is_sensitive": is_sensitive,
            "signals": signals,
        })
    
    async def list_messages(
        self,
        session_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """List messages in a session, ordered by created_at."""
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_messages(self, session_id: int) -> int:
        """Count total messages in a session."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.session_id == session_id)
        )
        return result.scalar() or 0
    
    async def get_recent_messages(
        self,
        session_id: int,
        limit: int = 10,
    ) -> list[ChatMessage]:
        """Get most recent messages for context."""
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        # Return in chronological order
        return list(reversed(messages))
