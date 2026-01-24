"""
Chat Service V2 - Optimized for low latency.

OPTIMIZATIONS:
1. Dùng Rule-based Risk Detection (regex) thay vì AI (tiết kiệm 2-5s)
2. Dùng ChatbotServiceV2 với AsyncOpenAI trực tiếp
3. Parallel fetch cho history và mood (đã có)
4. Streaming bắt đầu NGAY LẬP TỨC, không chờ risk detection

Flow mới:
User gửi tin → Rule-based risk (instant) → Stream từ OpenAI ngay
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.repositories.chat_repository import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from app.repositories.mood_repository import MoodRepository
from app.schemas.chat import (
    EndSessionResponse,
    MessageCreateResponse,
    MessageListItem,
    MessageListResponse,
    RecommendedAction,
    RiskLevel,
    RiskType,
    SessionCreateResponse,
    SessionListItem,
    SessionListResponse,
    SessionStatus,
)

# Dùng Rule-based detector (FAST) thay vì AI detector (SLOW)
from app.services.risk_detector_service import (
    RiskDetectionResult,
    get_risk_detector,
)
from app.services.chatbot_service_v2 import get_chatbot_service_v2


class ChatServiceError(Exception):
    """Base exception for chat service errors."""
    pass


class SessionNotFoundError(ChatServiceError):
    """Session not found."""
    pass


class SessionNotOwnedError(ChatServiceError):
    """Session does not belong to the user."""
    pass


class SessionEndedError(ChatServiceError):
    """Session has already ended."""
    pass


class ChatServiceV2:
    """
    Optimized chat service with minimal latency.

    Key differences from V1:
    - Uses rule-based risk detection (instant) instead of AI (2-5s)
    - Uses AsyncOpenAI directly (no LangChain overhead)
    - Streaming starts immediately after user sends message
    """

    def __init__(self, session: AsyncSession):
        self.db = session
        self.session_repo = ChatSessionRepository(session)
        self.message_repo = ChatMessageRepository(session)
        self.mood_repo = MoodRepository(session)

        # FAST: Rule-based risk detector (regex patterns)
        self.risk_detector = get_risk_detector()

        # FAST: Direct OpenAI client (no LangChain)
        self.chatbot = get_chatbot_service_v2()

    async def create_session(self, user: User) -> SessionCreateResponse:
        """Create a new chat session for the user."""
        chat_session = await self.session_repo.create_session(
            user_id=user.id,
            school_id=user.school_id,
        )

        return SessionCreateResponse(
            session_id=chat_session.id,
            started_at=chat_session.started_at,
            status=SessionStatus.ACTIVE,
        )

    async def list_sessions(
        self,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> SessionListResponse:
        """List all sessions for the user."""
        sessions = await self.session_repo.list_sessions(user.id, limit, offset)
        total = await self.session_repo.count_sessions(user.id)

        items = [
            SessionListItem(
                id=s.id,
                started_at=s.started_at,
                ended_at=s.ended_at,
                status=SessionStatus(s.status),
                last_risk_level=RiskLevel(s.last_risk_level) if s.last_risk_level else None,
            )
            for s in sessions
        ]

        return SessionListResponse(sessions=items, total=total)

    async def send_message_stream(
        self,
        session_id: int,
        user: User,
        content: str,
    ):
        """
        OPTIMIZED: Stream AI response với minimal latency.

        Flow:
        1. Validate session (DB lookup - fast)
        2. Rule-based risk detection (regex - instant, <1ms)
        3. Parallel fetch: history + mood (DB queries)
        4. Start streaming from OpenAI IMMEDIATELY
        5. Save messages after streaming completes

        Estimated improvement: 2-5 seconds faster than V1
        """
        # 1. Validate session (fast - single DB query)
        chat_session = await self.session_repo.get_session_by_id(session_id)

        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")

        if chat_session.status == "ENDED":
            raise SessionEndedError("Cannot send message to ended session")

        # 2. INSTANT: Rule-based risk detection (regex patterns, <1ms)
        risk_result = self.risk_detector.analyze(content)

        # Add recommended_actions attribute if not present (compatibility)
        if not hasattr(risk_result, 'recommended_actions'):
            risk_result.recommended_actions = self._get_actions_for_risk(
                risk_result.risk_level,
                risk_result.risk_type
            )

        # 3. PARALLEL: Fetch history and mood concurrently
        history_task = asyncio.create_task(
            self.message_repo.get_recent_messages(session_id, limit=10)
        )
        mood_task = asyncio.create_task(
            self.mood_repo.get_last_n_days(user.id, 5)
        )

        history, mood_entries = await asyncio.gather(history_task, mood_task)

        mood_history = [
            {
                "mood_date": str(entry.mood_date),
                "mood_value": entry.mood_value,
                "note": entry.note,
            }
            for entry in mood_entries
        ] if mood_entries else None

        # 4. Save user message
        user_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="USER",
            sender_user_id=user.id,
            content=content,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
            signals={"matched": risk_result.signals} if risk_result.signals else None,
        )

        # Send user message ID immediately
        yield {
            "type": "user_message_saved",
            "content": {"user_message_id": user_message.id}
        }

        # 5. STREAM: Start AI response immediately (with memory support)
        full_ai_text = ""
        new_summary = None

        async for chunk in self.chatbot.generate_reply_stream_with_memory(
            session=chat_session,
            user_message=content,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
        ):
            if chunk["type"] == "token":
                full_ai_text += chunk["content"]
                yield chunk

            elif chunk["type"] == "done":
                full_ai_text = chunk["content"]["full_text"]
                actions = chunk["content"].get("actions", [])
                new_summary = chunk["content"].get("summary")  # Lấy summary mới

            elif chunk["type"] == "error":
                yield chunk
                return

        # 6. Save AI message after streaming completes
        ai_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="AI",
            sender_user_id=None,
            content=full_ai_text,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
        )

        # 7. Update session (bao gồm summary nếu có)
        escalation_action = actions[0] if actions else None
        await self.session_repo.update_session_risk(
            session_id=session_id,
            last_risk_level=risk_result.risk_level,
            last_risk_type=risk_result.risk_type,
            last_escalation_action=escalation_action,
        )

        # Lưu conversation summary nếu có
        if new_summary:
            from app.models.chat import ChatSession as ChatSessionModel
            stmt = (
                ChatSessionModel.__table__.update()
                .where(ChatSessionModel.id == session_id)
                .values(conversation_summary=new_summary)
            )
            await self.db.execute(stmt)

        await self.db.commit()

        # 8. Send final response
        yield {
            "type": "done",
            "content": {
                "ai_message_id": ai_message.id,
                "risk_level": risk_result.risk_level,
                "risk_type": risk_result.risk_type,
                "recommended_actions": actions,
            }
        }

    def _get_actions_for_risk(self, risk_level: str, risk_type: str) -> list[str]:
        """Get recommended actions based on risk level."""
        if risk_level == "CRITICAL":
            return ["OPEN_SOS_MODULE", "OPEN_REPORT_MODULE"]
        elif risk_level == "HIGH":
            return ["OPEN_SOS_MODULE", "OPEN_REPORT_MODULE"]
        elif risk_level == "MEDIUM":
            if risk_type == "BULLYING":
                return ["OPEN_REPORT_MODULE", "OPEN_EXERCISES"]
            return ["OPEN_EXERCISES", "OPEN_EMOTION_DIARY"]
        else:
            return ["OPEN_EXERCISES", "OPEN_EMOTION_DIARY"]

    async def send_message(
        self,
        session_id: int,
        user: User,
        content: str,
    ) -> MessageCreateResponse:
        """Non-streaming version (backwards compatibility)."""
        # Validate session
        chat_session = await self.session_repo.get_session_by_id(session_id)

        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")

        if chat_session.status == "ENDED":
            raise SessionEndedError("Cannot send message to ended session")

        # Rule-based risk detection (instant)
        risk_result = self.risk_detector.analyze(content)

        if not hasattr(risk_result, 'recommended_actions'):
            risk_result.recommended_actions = self._get_actions_for_risk(
                risk_result.risk_level,
                risk_result.risk_type
            )

        # Save user message
        user_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="USER",
            sender_user_id=user.id,
            content=content,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
            signals={"matched": risk_result.signals} if risk_result.signals else None,
        )

        # Get context
        history = await self.message_repo.get_recent_messages(session_id, limit=10)
        mood_entries = await self.mood_repo.get_last_n_days(user.id, 5)
        mood_history = [
            {
                "mood_date": str(entry.mood_date),
                "mood_value": entry.mood_value,
                "note": entry.note,
            }
            for entry in mood_entries
        ] if mood_entries else None

        # Generate AI response
        chatbot_response = await self.chatbot.generate_reply(
            session=chat_session,
            user_message=content,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
        )

        # Save AI message
        ai_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="AI",
            sender_user_id=None,
            content=chatbot_response.ai_message,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
        )

        # Update session
        await self.session_repo.update_session_risk(
            session_id=session_id,
            last_risk_level=risk_result.risk_level,
            last_risk_type=risk_result.risk_type,
            last_escalation_action=chatbot_response.recommended_actions[0] if chatbot_response.recommended_actions else None,
        )

        await self.db.commit()

        return MessageCreateResponse(
            user_message_id=user_message.id,
            ai_message_id=ai_message.id,
            ai_message=chatbot_response.ai_message,
            risk_level=RiskLevel(risk_result.risk_level),
            risk_type=RiskType(risk_result.risk_type),
            recommended_actions=[
                RecommendedAction(a) for a in risk_result.recommended_actions
            ],
        )

    async def list_messages(
        self,
        session_id: int,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageListResponse:
        """List messages in a session."""
        chat_session = await self.session_repo.get_session_by_id(session_id)

        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")

        messages = await self.message_repo.list_messages(session_id, limit, offset)
        total = await self.message_repo.count_messages(session_id)

        items = [
            MessageListItem(
                id=m.id,
                sender_type=m.sender_type,
                content=m.content,
                risk_level=RiskLevel(m.risk_level) if m.risk_level else None,
                risk_type=RiskType(m.risk_type) if m.risk_type else None,
                created_at=m.created_at,
            )
            for m in messages
        ]

        return MessageListResponse(messages=items, total=total)

    async def end_session(
        self,
        session_id: int,
        user: User,
    ) -> EndSessionResponse:
        """End a chat session."""
        chat_session = await self.session_repo.get_session_by_id(session_id)

        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")

        if chat_session.status == "ENDED":
            raise SessionEndedError("Session is already ended")

        updated_session = await self.session_repo.end_session(session_id)

        return EndSessionResponse(
            session_id=updated_session.id,
            status=SessionStatus.ENDED,
            ended_at=updated_session.ended_at,
        )
