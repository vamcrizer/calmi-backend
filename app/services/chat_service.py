"""
Chat Service - Orchestrator for chat functionality.
Coordinates sessions, messages, risk detection, and AI responses.
"""
from sqlalchemy import text
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

# Use AI-powered risk detector instead of keyword-based
from app.services.ai_risk_detector_service import (
    RiskDetectionResult,
    get_ai_risk_detector,
)
from app.services.chatbot_service import ChatbotResponse, get_chatbot_service


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


class ChatService:
    """
    Orchestrator service for chat functionality.
    Handles the flow: message -> risk detection -> AI response -> persist.
    """
    
    def __init__(self, session: AsyncSession):
        self.db = session
        self.session_repo = ChatSessionRepository(session)
        self.message_repo = ChatMessageRepository(session)
        self.mood_repo = MoodRepository(session)  # For mood history context
        self.risk_detector = get_ai_risk_detector()  # Use AI-powered detector
        self.chatbot = get_chatbot_service()
    
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
    
    async def send_message(
        self,
        session_id: int,
        user: User,
        content: str,
    ) -> MessageCreateResponse:
        """
        Process a user message and generate AI response.
        
        Flow:
        1. Validate session ownership and status
        2. Save user message
        3. Run risk detection
        4. Get recent messages for context
        5. Generate AI response
        6. Save AI message
        7. Update session with risk info
        8. Return response
        """
        # 1. Validate session
        chat_session = await self.session_repo.get_session_by_id(session_id)
        
        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")
        
        if chat_session.status == "ENDED":
            raise SessionEndedError("Cannot send message to ended session")
        
        # 2. Run risk detection WITH conversation context
        risk_result = self.risk_detector.analyze(
            text=content,
            conversation_summary=chat_session.conversation_summary,
            last_risk_level=chat_session.last_risk_level,
            last_risk_type=chat_session.last_risk_type,
        )
        
        # 3. Save user message
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
        
        # 4. Get context from history
        history = await self.message_repo.get_recent_messages(session_id, limit=10)
        
        # 4.5. Get mood history for last 5 days (for AI to adjust tone)
        mood_entries = await self.mood_repo.get_last_n_days(user.id, 5)
        mood_history = [
            {
                "mood_date": str(entry.mood_date),
                "mood_value": entry.mood_value,
                "note": entry.note,
            }
            for entry in mood_entries
        ] if mood_entries else None
        
        # 5. Generate AI response với LangChain memory (OPTIMIZED: async)
        chatbot_response = await self.chatbot.generate_reply(
            session=chat_session,  # Pass session cho LangChain memory
            user_message=content,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
        )
        
        # 6. Save AI message
        ai_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="AI",
            sender_user_id=None,
            content=chatbot_response.ai_message,
            risk_level=risk_result.risk_level,
            risk_type=risk_result.risk_type,
            is_sensitive=risk_result.is_sensitive,
        )
        
        # 7. Update session với risk info VÀ conversation summary
        escalation_action = chatbot_response.recommended_actions[0] if chatbot_response.recommended_actions else None
        await self.session_repo.update_session_risk(
            session_id=session_id,
            last_risk_level=risk_result.risk_level,
            last_risk_type=risk_result.risk_type,
            last_escalation_action=escalation_action,
        )
        
        # Save conversation summary nếu có
        if chatbot_response.conversation_summary:
            await self.db.execute(
                text("UPDATE chat_sessions SET conversation_summary = :summary WHERE id = :id"),
                {"summary": chatbot_response.conversation_summary, "id": session_id}
            )
            await self.db.commit()
        
        # 8. Return response - Use AI-determined actions
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
    
    async def send_message_stream(
        self,
        session_id: int,
        user: User,
        content: str,
    ):
        """
        OPTIMIZED: Process user message và stream AI response với parallel processing.
        
        Optimizations:
        1. Risk detection chạy ASYNC song song với AI streaming
        2. Mood history được fetch song song
        3. User nhận token đầu tiên nhanh hơn ~2-3 giây
        
        Yields dict with 'type' and 'content'.
        """
        import asyncio
        
        # 1. Validate session (fast - from cache/DB)
        chat_session = await self.session_repo.get_session_by_id(session_id)
        
        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")
        
        if chat_session.status == "ENDED":
            raise SessionEndedError("Cannot send message to ended session")
        
        # 2. PARALLEL: Start risk detection as background task (ASYNC - non-blocking!)
        risk_task = asyncio.create_task(
            self.risk_detector.analyze_async(
                text=content,
                conversation_summary=chat_session.conversation_summary,
                last_risk_level=chat_session.last_risk_level,
                last_risk_type=chat_session.last_risk_type,
            )
        )
        
        # 3. PARALLEL: Fetch mood history and message history concurrently
        history_task = asyncio.create_task(
            self.message_repo.get_recent_messages(session_id, limit=10)
        )
        mood_task = asyncio.create_task(
            self.mood_repo.get_last_n_days(user.id, 5)
        )
        
        # 4. Wait for history and mood (usually fast - DB queries)
        history, mood_entries = await asyncio.gather(history_task, mood_task)
        
        mood_history = [
            {
                "mood_date": str(entry.mood_date),
                "mood_value": entry.mood_value,
                "note": entry.note,
            }
            for entry in mood_entries
        ] if mood_entries else None
        
        # 5. Create OPTIMISTIC risk result for immediate streaming
        # Use session's last risk level as initial guess (faster perceived response)
        optimistic_risk = RiskDetectionResult(
            risk_level=chat_session.last_risk_level or "LOW",
            risk_type=chat_session.last_risk_type or "OTHER",
            signals=[],
            is_sensitive=False,
            recommended_actions=["OPEN_EXERCISES", "OPEN_EMOTION_DIARY"],
        )
        
        # 6. Save user message with optimistic risk (will update later if needed)
        user_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="USER",
            sender_user_id=user.id,
            content=content,
            risk_level=optimistic_risk.risk_level,
            risk_type=optimistic_risk.risk_type,
            is_sensitive=optimistic_risk.is_sensitive,
            signals=None,
        )
        
        # Send user message ID immediately
        yield {
            "type": "user_message_saved",
            "content": {"user_message_id": user_message.id}
        }
        
        # 7. Start AI streaming IMMEDIATELY with optimistic risk
        # (Don't wait for risk detection to complete!)
        full_ai_text = ""
        summary = None
        actual_risk_result = None
        risk_completed = False
        
        async for chunk in self.chatbot.generate_reply_stream(
            session=chat_session,
            user_message=content,
            history=history,
            risk_result=optimistic_risk,  # Use optimistic first
            mood_history=mood_history,
        ):
            # Check if risk detection completed (non-blocking)
            if not risk_completed and risk_task.done():
                actual_risk_result = risk_task.result()
                risk_completed = True
                
                # If risk level changed significantly, notify frontend
                if actual_risk_result.risk_level != optimistic_risk.risk_level:
                    yield {
                        "type": "risk_update",
                        "content": {
                            "risk_level": actual_risk_result.risk_level,
                            "risk_type": actual_risk_result.risk_type,
                            "recommended_actions": actual_risk_result.recommended_actions,
                        }
                    }
            
            if chunk["type"] == "token":
                full_ai_text += chunk["content"]
                yield chunk
                
            elif chunk["type"] == "done":
                full_ai_text = chunk["content"]["full_text"]
                summary = chunk["content"].get("summary")
                
            elif chunk["type"] == "error":
                yield chunk
                # Cancel risk task if error
                if not risk_task.done():
                    risk_task.cancel()
                return
        
        # 8. Ensure risk detection is complete before saving
        if not risk_completed:
            try:
                actual_risk_result = await asyncio.wait_for(risk_task, timeout=5.0)
            except asyncio.TimeoutError:
                print("[WARN] Risk detection timed out, using optimistic result")
                actual_risk_result = optimistic_risk
        
        # Use actual risk result for saving
        final_risk = actual_risk_result or optimistic_risk
        actions = final_risk.recommended_actions
        
        # 9. Update user message with actual risk (if different)
        if final_risk.risk_level != optimistic_risk.risk_level:
            await self.db.execute(
                text("""
                    UPDATE chat_messages 
                    SET risk_level = :risk_level, 
                        risk_type = :risk_type,
                        is_sensitive = :is_sensitive,
                        signals = :signals
                    WHERE id = :msg_id
                """),
                {
                    "risk_level": final_risk.risk_level,
                    "risk_type": final_risk.risk_type,
                    "is_sensitive": final_risk.is_sensitive,
                    "signals": {"matched": final_risk.signals} if final_risk.signals else None,
                    "msg_id": user_message.id,
                }
            )
        
        # 10. Save AI message to DB
        ai_message = await self.message_repo.create_message(
            session_id=session_id,
            sender_type="AI",
            sender_user_id=None,
            content=full_ai_text,
            risk_level=final_risk.risk_level,
            risk_type=final_risk.risk_type,
            is_sensitive=final_risk.is_sensitive,
        )
        
        # 11. Update session
        escalation_action = actions[0] if actions else None
        await self.session_repo.update_session_risk(
            session_id=session_id,
            last_risk_level=final_risk.risk_level,
            last_risk_type=final_risk.risk_type,
            last_escalation_action=escalation_action,
        )
        
        # Save conversation summary
        if summary:
            await self.db.execute(
                text("UPDATE chat_sessions SET conversation_summary = :summary WHERE id = :id"),
                {"summary": summary, "id": session_id}
            )
        
        await self.db.commit()
        
        # 12. Send final response with ACTUAL risk metadata
        yield {
            "type": "done",
            "content": {
                "ai_message_id": ai_message.id,
                "risk_level": final_risk.risk_level,
                "risk_type": final_risk.risk_type,
                "recommended_actions": actions,
            }
        }

    
    async def list_messages(
        self,
        session_id: int,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageListResponse:
        """List messages in a session."""
        # Validate ownership
        chat_session = await self.session_repo.get_session_by_id(session_id)
        
        if not chat_session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if chat_session.user_id != user.id:
            raise SessionNotOwnedError("Session does not belong to this user")
        
        # Get messages
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
