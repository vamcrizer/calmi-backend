"""
Chatbot Service V2 - Optimized với AsyncOpenAI trực tiếp.
Không dùng LangChain để giảm overhead và latency.

OPTIMIZATIONS:
1. Dùng AsyncOpenAI SDK trực tiếp (không qua LangChain)
2. Streaming ngay lập tức từ OpenAI → User
3. Conversation context: 5 messages gần nhất + summary của messages cũ hơn
4. Prompt rút gọn để giảm tokens
5. Summary được tạo async sau khi stream xong (không block user)
6. HTTP/2 với connection pooling để giảm latency

MEMORY STRATEGY:
- Giữ 5 messages gần nhất trong context (đầy đủ)
- Tóm tắt messages cũ hơn thành 1-2 câu (tiết kiệm tokens)
- Summary được lưu trong DB field `conversation_summary`
"""
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.models.chat import ChatMessage, ChatSession
from app.services.risk_detector_service import RiskDetectionResult

settings = get_settings()

# Số messages gần nhất giữ đầy đủ trong context
RECENT_MESSAGES_LIMIT = 5

# Threshold để tạo summary mới (khi có nhiều hơn N messages)
SUMMARY_THRESHOLD = 8

# Shared HTTP client với HTTP/2 và connection pooling
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Get shared httpx client with HTTP/2 support."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            http2=True,  # HTTP/2 multiplexing
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=60.0,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=60.0,  # Longer for streaming
                write=10.0,
                pool=10.0,
            ),
        )
    return _http_client


@dataclass
class ChatbotResponse:
    """Response from chatbot service."""
    ai_message: str
    recommended_actions: list[str]
    conversation_summary: Optional[str] = None


# System prompt rút gọn tối đa
SYSTEM_PROMPT = """Bạn là Calmi - trợ lý tâm lý cho học sinh Việt Nam.

NGUYÊN TẮC:
• Đồng cảm, không phán xét
• Trả lời ngắn gọn 2-3 câu
• Ngôn ngữ nhẹ nhàng, thân thiện

RỦI RO CAO: Khuyến khích tìm người lớn hỗ trợ hoặc gọi 1800-599-964."""


class ChatbotServiceV2:
    """
    Optimized chatbot service using AsyncOpenAI directly.

    Benefits:
    - No LangChain overhead
    - Direct streaming from OpenAI
    - Faster first token latency
    """

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy init AsyncOpenAI client với HTTP/2."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=_get_http_client(),  # HTTP/2 + connection pooling
                timeout=60.0,
                max_retries=1,  # Giảm retry để không chậm thêm
            )
        return self._client

    def _build_messages(
        self,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
        conversation_summary: str | None = None,
    ) -> list[dict]:
        """Build messages array for OpenAI API."""
        messages = []

        # System message với context
        system_content = SYSTEM_PROMPT

        # Thêm mood context nếu có
        if mood_history:
            mood_text = self._format_mood_brief(mood_history)
            system_content += f"\n\nCẢM XÚC GẦN ĐÂY: {mood_text}"

        # Thêm risk context
        if risk_result.risk_level in ("HIGH", "CRITICAL"):
            system_content += f"\n\n⚠️ CẢNH BÁO: Phát hiện {risk_result.risk_type}. Hãy thể hiện sự quan tâm và khuyến khích tìm hỗ trợ."

        messages.append({"role": "system", "content": system_content})

        # Thêm conversation summary nếu có (thay cho full history)
        if conversation_summary:
            messages.append({
                "role": "system",
                "content": f"Tóm tắt cuộc trò chuyện trước: {conversation_summary}"
            })

        # Thêm 5 messages gần nhất (đủ context, không quá nhiều tokens)
        recent_history = history[-5:] if history else []
        for msg in recent_history:
            role = "user" if msg.sender_type == "USER" else "assistant"
            messages.append({"role": role, "content": msg.content})

        # User message hiện tại
        messages.append({"role": "user", "content": user_message})

        return messages

    def _format_mood_brief(self, mood_history: list[dict]) -> str:
        """Format mood history thành text ngắn gọn."""
        if not mood_history:
            return "Chưa có dữ liệu"

        mood_labels = {
            100: "vui", 80: "bình thường", 60: "buồn",
            40: "lo lắng", 20: "rất buồn"
        }

        # Chỉ lấy 3 ngày gần nhất
        recent = mood_history[:3]
        parts = []
        for entry in recent:
            value = entry.get("mood_value", 60)
            label = mood_labels.get(value, f"{value}/100")
            parts.append(label)

        return ", ".join(parts)

    def _get_recommended_actions(self, risk_level: str, risk_type: str) -> list[str]:
        """Determine recommended actions based on risk."""
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

    async def generate_reply_stream(
        self,
        session: ChatSession,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream AI response trực tiếp từ OpenAI.

        Yields:
            dict with 'type' ('token', 'done', 'error') and 'content'
        """
        # Build messages
        messages = self._build_messages(
            user_message=user_message,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
            conversation_summary=session.conversation_summary,
        )

        full_response = ""

        try:
            # Stream trực tiếp từ OpenAI
            stream = await self.client.chat.completions.create(
                model="gpt-4.1-nano",  # Fastest model
                messages=messages,
                max_tokens=300,  # Giới hạn response ngắn
                temperature=0.7,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield {"type": "token", "content": token}

            # Done - gửi metadata
            actions = self._get_recommended_actions(
                risk_result.risk_level,
                risk_result.risk_type,
            )

            yield {
                "type": "done",
                "content": {
                    "full_text": full_response.strip(),
                    "actions": actions,
                    "summary": None,  # Có thể tạo summary sau nếu cần
                }
            }

        except Exception as e:
            print(f"[CHATBOT V2 ERROR] {e}")
            import traceback
            traceback.print_exc()

            fallback = self._get_fallback_response(risk_result.risk_level)
            yield {"type": "token", "content": fallback}
            yield {
                "type": "done",
                "content": {
                    "full_text": fallback,
                    "actions": [],
                    "summary": None,
                }
            }

    async def generate_reply(
        self,
        session: ChatSession,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
    ) -> ChatbotResponse:
        """Non-streaming version (for backwards compatibility)."""
        messages = self._build_messages(
            user_message=user_message,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
            conversation_summary=session.conversation_summary,
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )

            ai_message = response.choices[0].message.content or ""
            actions = self._get_recommended_actions(
                risk_result.risk_level,
                risk_result.risk_type,
            )

            return ChatbotResponse(
                ai_message=ai_message.strip(),
                recommended_actions=actions,
                conversation_summary=None,
            )

        except Exception as e:
            print(f"[CHATBOT V2 ERROR] {e}")
            return ChatbotResponse(
                ai_message=self._get_fallback_response(risk_result.risk_level),
                recommended_actions=[],
                conversation_summary=None,
            )

    def _get_fallback_response(self, risk_level: str) -> str:
        """Fallback response khi API lỗi."""
        if risk_level in ("CRITICAL", "HIGH"):
            return (
                "Mình rất lo lắng cho em. Em không đơn độc. "
                "Hãy gọi đường dây hỗ trợ 1800-599-964 (miễn phí) "
                "hoặc nói chuyện với người lớn mà em tin tưởng."
            )
        return (
            "Mình ở đây để lắng nghe em. "
            "Em có thể chia sẻ thêm không?"
        )

    async def generate_conversation_summary(
        self,
        history: list[ChatMessage],
        existing_summary: str | None = None,
    ) -> str | None:
        """
        Tạo summary của cuộc hội thoại (chạy async, không block streaming).

        Chỉ tạo summary khi:
        - Có nhiều hơn SUMMARY_THRESHOLD messages
        - Hoặc cần cập nhật summary cũ

        Returns:
            New summary string hoặc None nếu không cần tạo
        """
        if len(history) < SUMMARY_THRESHOLD:
            return existing_summary  # Chưa cần summary

        # Lấy messages cần tóm tắt (bỏ 5 messages gần nhất - đã có trong context)
        messages_to_summarize = history[:-RECENT_MESSAGES_LIMIT]

        if not messages_to_summarize:
            return existing_summary

        # Build conversation text
        conv_parts = []
        for msg in messages_to_summarize[-10:]:  # Chỉ lấy 10 messages gần nhất để tóm tắt
            role = "Học sinh" if msg.sender_type == "USER" else "Calmi"
            conv_parts.append(f"{role}: {msg.content}")

        conversation_text = "\n".join(conv_parts)

        # Thêm existing summary nếu có
        context = ""
        if existing_summary:
            context = f"Tóm tắt trước đó: {existing_summary}\n\n"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {
                        "role": "system",
                        "content": "Tóm tắt cuộc trò chuyện sau thành 1-2 câu ngắn gọn. Giữ lại thông tin quan trọng về cảm xúc và vấn đề của học sinh."
                    },
                    {
                        "role": "user",
                        "content": f"{context}Cuộc trò chuyện:\n{conversation_text}"
                    }
                ],
                max_tokens=100,
                temperature=0.5,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[SUMMARY ERROR] {e}")
            return existing_summary

    async def generate_reply_stream_with_memory(
        self,
        session: ChatSession,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream AI response VÀ cập nhật conversation summary.

        Flow:
        1. Stream response ngay lập tức
        2. Sau khi stream xong, tạo summary mới (async, không block)
        3. Trả về summary trong 'done' event

        Yields:
            dict with 'type' ('token', 'done', 'error') and 'content'
        """
        import time
        start_time = time.time()

        # Build messages với summary cũ
        messages = self._build_messages(
            user_message=user_message,
            history=history,
            risk_result=risk_result,
            mood_history=mood_history,
            conversation_summary=session.conversation_summary,
        )

        full_response = ""
        first_token_time = None

        try:
            # Stream trực tiếp từ OpenAI
            stream = await self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                stream=True,
            )

            print(f"[STREAM] OpenAI stream created in {time.time() - start_time:.2f}s")

            token_count = 0
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    token_count += 1

                    if first_token_time is None:
                        first_token_time = time.time()
                        print(f"[STREAM] First token received in {first_token_time - start_time:.2f}s")

                    # Yield NGAY LẬP TỨC mỗi token
                    yield {"type": "token", "content": token}

            print(f"[STREAM] Total {token_count} tokens in {time.time() - start_time:.2f}s")

            # Tạo summary mới nếu cần (không block - chạy nhanh)
            new_summary = None
            if len(history) >= SUMMARY_THRESHOLD:
                new_summary = await self.generate_conversation_summary(
                    history=history,
                    existing_summary=session.conversation_summary,
                )

            # Done - gửi metadata với summary
            actions = self._get_recommended_actions(
                risk_result.risk_level,
                risk_result.risk_type,
            )

            yield {
                "type": "done",
                "content": {
                    "full_text": full_response.strip(),
                    "actions": actions,
                    "summary": new_summary,  # Để lưu vào DB
                }
            }

        except Exception as e:
            print(f"[CHATBOT V2 ERROR] {e}")
            import traceback
            traceback.print_exc()

            fallback = self._get_fallback_response(risk_result.risk_level)
            yield {"type": "token", "content": fallback}
            yield {
                "type": "done",
                "content": {
                    "full_text": fallback,
                    "actions": [],
                    "summary": None,
                }
            }


# Singleton instance
_chatbot_service_v2: ChatbotServiceV2 | None = None


def get_chatbot_service_v2() -> ChatbotServiceV2:
    """Get singleton chatbot service V2 instance."""
    global _chatbot_service_v2
    if _chatbot_service_v2 is None:
        _chatbot_service_v2 = ChatbotServiceV2()
    return _chatbot_service_v2
