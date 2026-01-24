"""
Voice Chat Router - WebSocket relay and WebRTC SDP proxy for OpenAI Realtime API.
Enables real-time voice conversations with AI chatbot.
"""
import asyncio
import base64
import json
import os
from typing import Annotated

import httpx
import websockets
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.chat import ChatSession
from app.models.user import User
from app.repositories.chat_repository import ChatSessionRepository

router = APIRouter(prefix="/voice-chat", tags=["Voice Chat"])
settings = get_settings()

# OpenAI Realtime API configuration
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
OPENAI_REALTIME_HTTP_URL = "https://api.openai.com/v1/realtime"
OPENAI_MODEL = "gpt-4o-realtime-preview-2024-12-17"  # WebRTC compatible model


async def get_chat_session(session_id: int, user: User, db: AsyncSession) -> ChatSession:
    """Verify session exists and belongs to user."""
    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    return session


@router.websocket("/ws/{session_id}")
async def voice_chat_websocket(
    websocket: WebSocket,
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for voice chat.
    
    Relay between client browser and OpenAI Realtime API.
    
    Flow:
    1. Client connects
    2. Server authenticates via token in query params
    3. Server connects to OpenAI
    4. Bidirectional relay: Client ↔ Server ↔ OpenAI
    """
    await websocket.accept()
    
    # Get token from query params (WebSocket can't use headers easily)
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return
    
    # Authenticate user
    try:
        from app.core.deps_ws import get_current_user_from_token
        user = await get_current_user_from_token(token, db)
        
        # Verify student role
        if not user.role or user.role.code != "STUDENT":
            await websocket.close(code=4003, reason="Only students can use voice chat")
            return
        
        # Verify session ownership
        session = await get_chat_session(session_id, user, db)
        
    except Exception as e:
        await websocket.close(code=4001, reason=f"Auth failed: {str(e)}")
        return
    
    # Connect to OpenAI Realtime API
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
    
    openai_url = f"{OPENAI_REALTIME_URL}?model={OPENAI_MODEL}"
    
    try:
        async with websockets.connect(openai_url, extra_headers=headers) as openai_ws:
            print(f"✅ Voice chat connected: session={session_id}, user={user.id}")
            
            # Send initial session configuration (following OpenAI docs)
            session_config = {
                "type": "session.update",
                "session": {
                    "type": "realtime",  # Required for speech-to-speech
                    "model": "gpt-realtime-mini",
                    "output_modalities": ["audio", "text"],  # Both audio and text
                    "audio": {
                        "input": {
                            "format": {
                                "type": "audio/pcm",
                                "rate": 24000  # 24kHz
                            },
                            "turn_detection": {
                                "type": "semantic_vad"  # Semantic Voice Activity Detection
                            }
                        },
                        "output": {
                            "format": {
                                "type": "audio/pcm",  # PCM format
                                "rate": 24000
                            },
                            "voice": "marin"  # Best voice for natural conversation
                        }
                    },
                    # Structured prompt following best practices
                    "instructions": """# Role & Objective
Bạn là Calmi, trợ lý tâm lý AI cho học sinh Việt Nam.
Mục tiêu: Lắng nghe, thấu hiểu, và hỗ trợ sức khỏe tinh thần học sinh một cách an toàn và chuyên nghiệp.

# Personality & Tone
- Thân thiện, ấm áp, dễ gần
- Tôn trọng, không phán xét
- Tích cực nhưng thực tế
- Nói chuyện tự nhiên như người bạn đáng tin cậy

# Language
- LUÔN trả lời bằng tiếng Việt
- Dùng ngôn ngữ đơn giản, dễ hiểu
- Tránh thuật ngữ y khoa phức tạp
- Giọng điệu phù hợp với học sinh (12-18 tuổi)

# Unclear Audio
- Chỉ phản hồi với audio/text rõ ràng
- NẾU audio không rõ (nhiễu, im lặng, khó nghe):
  * "Xin lỗi em, anh/chị không nghe rõ. Em nói lại được không?"
  * "Có vẻ có tiếng ồn quanh em. Em thử nói lại nhé?"
- KHÔNG đoán hoặc tiếp tục khi không chắc chắn

# Conversation Rules
- Luôn xác nhận đã hiểu trước khi đưa lời khuyên
- Đặt câu hỏi mở để học sinh chia sẻ sâu hơn
- Thừa nhận cảm xúc: "Anh/chị hiểu em đang cảm thấy..."
- Khuyến khích hành động tích cực nhỏ, thực tế
- KHÔNG hứa hẹn giải quyết ngay, đưa ra cam kết

# Safety & Escalation
NẾU phát hiện dấu hiệu nguy hiểm (tự tử, bạo lực, tự hại):
- NGAY LẬP TỨC đề xuất liên hệ người lớn tin cậy
- Khuyến khích dùng tính năng SOS trong app
- Cung cấp số hotline khẩn cấp: 18001567 (tâm lý học đường Việt Nam)
- GIỮ học sinh trong cuộc trò chuyện, KHÔNG kết thúc đột ngột

# Response Format
- Giữ câu trả lời ngắn gọn (2-3 câu)
- Một ý chính mỗi lượt
- Tránh lặp lại cụm từ
- Biến đổi cách diễn đạt để tự nhiên

# Example Phrases
"Em có thể kể thêm về điều đó không?"
"Nghe có vẻ em đang trải qua giai đoạn khó khăn nhỉ."
"Anh/chị ở đây lắng nghe em."
"Em đã thử cách nào để cảm thấy tốt hơn chưa?"
"""
                }
            }
            await openai_ws.send(json.dumps(session_config))
            
            # Bidirectional relay tasks
            async def client_to_openai():
                """Forward messages from client to OpenAI."""
                try:
                    while True:
                        message = await websocket.receive_text()
                        await openai_ws.send(message)
                except WebSocketDisconnect:
                    print(f"Client disconnected: session={session_id}")
                except Exception as e:
                    print(f"Error client→openai: {e}")
            
            async def openai_to_client():
                """Forward messages from OpenAI to client."""
                try:
                    async for message in openai_ws:
                        await websocket.send_text(message)
                except Exception as e:
                    print(f"Error openai→client: {e}")
            
            # Run both directions concurrently
            await asyncio.gather(
                client_to_openai(),
                openai_to_client(),
                return_exceptions=True
            )
            
    except websockets.exceptions.WebSocketException as e:
        error_msg = f"OpenAI connection error: {str(e)}"
        print(f"❌ {error_msg}")
        await websocket.close(code=1011, reason=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        await websocket.close(code=1011, reason=error_msg)
    finally:
        await websocket.close()
        print(f"🔌 Voice chat closed: session={session_id}")


# =============================================================================
# WebRTC SDP Proxy Endpoint - For browser WebRTC connections
# =============================================================================

@router.post(
    "/rtc/offer",
    response_class=PlainTextResponse,
    summary="Proxy WebRTC SDP offer to OpenAI",
    description="""
    Securely proxy WebRTC SDP negotiation to OpenAI Realtime API.
    
    Frontend sends SDP offer -> Backend forwards to OpenAI -> Returns SDP answer.
    
    This prevents:
    - CORS issues (OpenAI doesn't allow direct browser calls)
    - API key exposure in frontend
    """,
)
async def proxy_webrtc_offer(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Proxy WebRTC SDP offer to OpenAI and return SDP answer.
    
    Request body: Raw SDP offer text
    Response: Raw SDP answer text
    """
    # Verify student role
    if not current_user.role or current_user.role.code != "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can use voice chat"
        )
    
    # Get raw SDP offer from request body
    sdp_offer = await request.body()
    sdp_offer_text = sdp_offer.decode("utf-8")
    
    if not sdp_offer_text or not sdp_offer_text.startswith("v="):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid SDP offer format"
        )
    
    print(f"[VoiceChat RTC] User {current_user.id} sending SDP offer to OpenAI...")
    
    # Forward to OpenAI Realtime API
    openai_url = f"{OPENAI_REALTIME_HTTP_URL}?model={OPENAI_MODEL}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                openai_url,
                content=sdp_offer_text,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/sdp",
                },
            )
            
            if response.status_code != 200 and response.status_code != 201:
                error_text = response.text
                print(f"[VoiceChat RTC] OpenAI error: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"OpenAI API error: {response.status_code}"
                )
            
            sdp_answer = response.text
            print(f"[VoiceChat RTC] ✅ Got SDP answer from OpenAI")
            
            return PlainTextResponse(
                content=sdp_answer,
                media_type="application/sdp"
            )
            
    except httpx.TimeoutException:
        print("[VoiceChat RTC] ❌ OpenAI request timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenAI API timeout"
        )
    except httpx.RequestError as e:
        print(f"[VoiceChat RTC] ❌ Request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to OpenAI: {str(e)}"
        )


@router.get("/rtc/health")
async def rtc_health_check():
    """Health check for WebRTC proxy."""
    return {
        "status": "ok",
        "model": OPENAI_MODEL,
        "api_configured": bool(settings.OPENAI_API_KEY),
    }
