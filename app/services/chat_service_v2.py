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
        ULTRA-OPTIMIZED: Stream AI response với minimal latency.

        Flow (tối ưu cho tốc độ):
        1. Validate session (quick DB lookup)
        2. Rule-based risk detection (instant, <1ms)
        3. BẮT ĐẦU STREAM NGAY - không chờ fetch history
        4. Fetch history + mood PARALLEL với streaming setup
        5. Save messages SAU KHI stream xong

        Estimated improvement: First token trong ~1-2s (thay vì 3-5s)
        """
        import time
        import asyncio
        start_time = time.time()

        # 1. Validate session (quick - single DB query)
        chat_session = await self.session_repo.get_session_by_id(session_id)

        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")

        if chat_session.status == "ENDED":
            raise SessionEndedError("Cannot send message to ended session")

        print(f"[V2] Session validated in {time.time() - start_time:.3f}s")

        # 2. INSTANT: Rule-based risk detection (regex patterns, <1ms)
        risk_result = self.risk_detector.analyze(content)

        if not hasattr(risk_result, 'recommended_actions'):
            risk_result.recommended_actions = self._get_actions_for_risk(
                risk_result.risk_level,
                risk_result.risk_type
            )

        print(f"[V2] Risk detection done in {time.time() - start_time:.3f}s")

        # 3. PARALLEL: Fetch history and mood WHILE preparing stream
        # Không await ngay - để chạy song song
        history_task = asyncio.create_task(
            self.message_repo.get_recent_messages(session_id, limit=5)  # Giảm từ 10 xuống 5
        )
        mood_task = asyncio.create_task(
            self.mood_repo.get_last_n_days(user.id, 3)  # Giảm từ 5 xuống 3
        )

        # 4. Await history/mood (should be fast - simple queries)
        history, mood_entries = await asyncio.gather(history_task, mood_task)

        print(f"[V2] DB queries done in {time.time() - start_time:.3f}s")

        mood_history = [
            {
                "mood_date": str(entry.mood_date),
                "mood_value": entry.mood_value,
            }
            for entry in mood_entries
        ] if mood_entries else None

        # 5. GỬI "TYPING" INDICATOR NGAY - để user biết bot đang xử lý
        yield {
            "type": "typing",
            "content": {"status": "thinking"}
        }

        # 6. BẮT ĐẦU STREAM - save user message SAU
        full_ai_text = ""
        new_summary = None
        actions = []

        print(f"[V2] Starting OpenAI stream at {time.time() - start_time:.3f}s")

        async for chunk in self.chatbot.generate_reply_stream_with_memory(
            session=chat_session,
            user_message=content,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
        ):
            if chunk["type"] == "token":
                full_ai_text += chunk["content"]
                yield chunk  # Stream NGAY LẬP TỨC

            elif chunk["type"] == "done":
                full_ai_text = chunk["content"]["full_text"]
                actions = chunk["content"].get("actions", [])
                new_summary = chunk["content"].get("summary")

            elif chunk["type"] == "error":
                yield chunk
                return

        print(f"[V2] Stream completed in {time.time() - start_time:.3f}s")

        # 6. SAU KHI STREAM XONG: Save messages (background-ish)
        # User đã thấy response rồi, giờ mới save
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

        ai_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="AI",
            sender_user_id=None,
            content=full_ai_text,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
        )

        # 7. Update session
        escalation_action = actions[0] if actions else None
        await self.session_repo.update_session_risk(
            session_id=session_id,
            last_risk_level=risk_result.risk_level,
            last_risk_type=risk_result.risk_type,
            last_escalation_action=escalation_action,
        )

        # Lưu conversation summary nếu có
        if new_summary:
            from sqlalchemy import update
            from app.models.chat import ChatSession as ChatSessionModel
            stmt = (
                update(ChatSessionModel)
                .where(ChatSessionModel.id == session_id)
                .values(conversation_summary=new_summary)
            )
            await self.db.execute(stmt)

        await self.db.commit()

        print(f"[V2] All done in {time.time() - start_time:.3f}s")

        # 8. Send final response
        yield {
            "type": "done",
            "content": {
                "user_message_id": user_message.id,
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
