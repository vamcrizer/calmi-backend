"""
Chat Router - API endpoints for Module 3 AI Psychological Chatbot.
Only authenticated students can access these endpoints.
"""
import json
import sys
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User
from app.schemas.chat import (
    EndSessionResponse,
    MessageCreateRequest,
    MessageCreateResponse,
    MessageListResponse,
    SessionCreateResponse,
    SessionListResponse,
)
from app.schemas.common import api_error, api_response
from app.services.chat_service import (
    ChatService,
    SessionEndedError,
    SessionNotFoundError,
    SessionNotOwnedError,
)
from app.services.chat_service_v2 import (
    ChatServiceV2,
    SessionEndedError as SessionEndedErrorV2,
    SessionNotFoundError as SessionNotFoundErrorV2,
    SessionNotOwnedError as SessionNotOwnedErrorV2,
)

router = APIRouter(prefix="/chat", tags=["Chat - AI Psychological Chatbot"])


# Dependency to get student user only
StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]


# ==========================================
# SESSION ENDPOINTS
# ==========================================

@router.post(
    "/sessions",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phiên chat mới",
    description="Tạo một phiên chat mới với AI chatbot tâm lý.",
)
async def create_session(
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo phiên chat mới cho học sinh.
    
    - Chỉ học sinh được phép sử dụng
    - Mỗi học sinh có thể có nhiều phiên chat
    """
    service = ChatService(db)
    result = await service.create_session(current_user)
    
    return api_response(
        data={
            "session_id": result.session_id,
            "started_at": result.started_at.isoformat(),
            "status": result.status.value,
        },
        message="Đã tạo phiên chat mới",
    )


@router.get(
    "/sessions",
    response_model=dict,
    summary="Danh sách phiên chat",
    description="Lấy danh sách các phiên chat của học sinh.",
)
async def list_sessions(
    current_user: StudentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách phiên chat của học sinh. (Cached 2 min)"""
    from app.core.cache import cache
    cache_key = f"chat:{current_user.id}:sessions:{limit}:{offset}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = ChatService(db)
    result = await service.list_sessions(current_user, limit, offset)
    
    sessions_data = [
        {
            "id": s.id,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "status": s.status.value,
            "last_risk_level": s.last_risk_level.value if s.last_risk_level else None,
        }
        for s in result.sessions
    ]
    
    response = api_response(
        data={
            "sessions": sessions_data,
            "total": result.total,
        },
    )
    cache.set(cache_key, response, ttl=120)
    return response


# ==========================================
# MESSAGE ENDPOINTS
# ==========================================

@router.post(
    "/sessions/{session_id}/messages",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi tin nhắn",
    description="Gửi tin nhắn đến AI chatbot và nhận phản hồi.",
)
async def send_message(
    session_id: int,
    request: MessageCreateRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Gửi tin nhắn và nhận phản hồi từ AI.
    
    Flow:
    1. Lưu tin nhắn của học sinh
    2. Phân tích rủi ro
    3. Tạo phản hồi AI
    4. Trả về kết quả với các đề xuất hành động
    """
    service = ChatService(db)
    
    try:
        result = await service.send_message(
            session_id=session_id,
            user=current_user,
            content=request.content,
        )
        
        return api_response(
            data={
                "user_message_id": result.user_message_id,
                "ai_message_id": result.ai_message_id,
                "ai_message": result.ai_message,
                "risk_level": result.risk_level.value,
                "risk_type": result.risk_type.value,
                "recommended_actions": [a.value for a in result.recommended_actions],
            },
        )
    
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên chat",
        )
    except SessionNotOwnedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập phiên chat này",
        )
    except SessionEndedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên chat đã kết thúc, không thể gửi tin nhắn",
        )


@router.post(
    "/sessions/{session_id}/messages/stream",
    summary="Gửi tin nhắn (Streaming)",
    description="Gửi tin nhắn và nhận phản hồi từ AI theo realtime streaming.",
)
async def send_message_stream(
    session_id: int,
    request: MessageCreateRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Gửi tin nhắn và stream response từ AI.
    
    Response format: Server-Sent Events (SSE)
    - Mỗi chunk là JSON object với type và content
    - type=token: text chunk
    - type=done: metadata cuối cùng (actions, summary)
    - type=error: lỗi
    """
    service = ChatService(db)
    
    async def event_generator():
        try:
            async for chunk in service.send_message_stream(
                session_id=session_id,
                user=current_user,
                content=request.content,
            ):
                # Format as SSE
                yield f"data: {json.dumps(chunk)}\n\n"
        
        except SessionNotFoundError:
            error_data = {"type": "error", "content": "Session not found"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except SessionNotOwnedError:
            error_data = {"type": "error", "content": "Forbidden"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except SessionEndedError:
            error_data = {"type": "error", "content": "Session ended"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/sessions/{session_id}/messages/stream-v2",
    summary="Gửi tin nhắn (Streaming V2 - Optimized)",
    description="""
    **PHIÊN BẢN TỐI ƯU** - AI risk detection thông minh + streaming nhanh.

    Tối ưu:
    - AI risk detection (gpt-4.1-nano) - phân tích context thay vì keyword matching
    - AsyncOpenAI trực tiếp (không qua LangChain)
    - Streaming bắt đầu ngay lập tức
    - TRUE STREAMING: mỗi token được gửi ngay lập tức

    Response format: Server-Sent Events (SSE)
    - type=user_message_saved: user message ID đã lưu
    - type=token: text chunk từ AI
    - type=done: metadata cuối (actions, risk_level, ai_message_id)
    - type=error: lỗi
    """,
)
async def send_message_stream_v2(
    session_id: int,
    request: MessageCreateRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    OPTIMIZED: Gửi tin nhắn và stream response từ AI.

    Improvements over V1:
    - AI risk detection với gpt-4.1-nano (context-aware, không dùng keyword)
    - Direct OpenAI streaming (no LangChain overhead)
    - Conversation memory via DB summary (efficient)
    - TRUE token-by-token streaming with immediate flush
    """
    service = ChatServiceV2(db)

    async def event_generator():
        try:
            async for chunk in service.send_message_stream(
                session_id=session_id,
                user=current_user,
                content=request.content,
            ):
                # Format as SSE - mỗi chunk là 1 event riêng
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
                # Force flush by yielding empty string (signals to ASGI server)
                # This helps ensure each token is sent immediately

        except SessionNotFoundErrorV2:
            error_data = {"type": "error", "content": "Session not found"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except SessionNotOwnedErrorV2:
            error_data = {"type": "error", "content": "Forbidden"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except SessionEndedErrorV2:
            error_data = {"type": "error", "content": "Session ended"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_data = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Type": "text/event-stream; charset=utf-8",
        }
    )



@router.get(
    "/sessions/{session_id}/messages",
    response_model=dict,
    summary="Lịch sử tin nhắn",
    description="Lấy lịch sử tin nhắn trong phiên chat.",
)
async def list_messages(
    session_id: int,
    current_user: StudentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách tin nhắn trong phiên chat.
    
    - Chỉ chủ sở hữu phiên chat được phép xem
    - Có phân trang
    - Sắp xếp theo thời gian tạo
    """
    service = ChatService(db)
    
    try:
        result = await service.list_messages(
            session_id=session_id,
            user=current_user,
            limit=limit,
            offset=offset,
        )
        
        messages_data = [
            {
                "id": m.id,
                "sender_type": m.sender_type.value if hasattr(m.sender_type, 'value') else m.sender_type,
                "content": m.content,
                "risk_level": m.risk_level.value if m.risk_level else None,
                "risk_type": m.risk_type.value if m.risk_type else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in result.messages
        ]
        
        return api_response(
            data={
                "messages": messages_data,
                "total": result.total,
            },
        )
    
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên chat",
        )
    except SessionNotOwnedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập phiên chat này",
        )


# ==========================================
# SESSION MANAGEMENT
# ==========================================

@router.post(
    "/sessions/{session_id}/end",
    response_model=dict,
    summary="Kết thúc phiên chat",
    description="Đánh dấu phiên chat là đã kết thúc.",
)
async def end_session(
    session_id: int,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Kết thúc phiên chat.
    
    - Phiên chat sẽ được đánh dấu là ENDED
    - Không thể gửi thêm tin nhắn
    - Vẫn có thể xem lịch sử
    """
    service = ChatService(db)
    
    try:
        result = await service.end_session(
            session_id=session_id,
            user=current_user,
        )
        
        return api_response(
            data={
                "session_id": result.session_id,
                "status": result.status.value,
                "ended_at": result.ended_at.isoformat(),
            },
            message="Đã kết thúc phiên chat",
        )
    
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên chat",
        )
    except SessionNotOwnedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền kết thúc phiên chat này",
        )
    except SessionEndedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên chat đã được kết thúc trước đó",
        )
