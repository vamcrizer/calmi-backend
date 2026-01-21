"""
Chatbot Service với LangChain Conversation Memory.
Sử dụng conversation summary để nhớ lịch sử mà không lưu toàn bộ messages.
"""
from dataclasses import dataclass
from typing import Optional

from langchain_classic.chains import ConversationChain
from langchain_classic.memory import ConversationSummaryBufferMemory
from langchain_classic.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# LangChain imports - correct for latest version
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain_community.chat_models import ChatOpenAI

try:
    from langchain.memory import ConversationSummaryBufferMemory
except ImportError:
    from langchain_classic.memory import ConversationSummaryBufferMemory

try:
    from langchain.chains import ConversationChain
except ImportError:
    from langchain_classic.chains import ConversationChain

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_classic.prompts import PromptTemplate

from app.core.config import get_settings
from app.models.chat import ChatMessage, ChatSession
from app.services.risk_detector_service import RiskDetectionResult

settings = get_settings()


@dataclass
class ChatbotResponse:
    """Response from chatbot service."""
    ai_message: str
    recommended_actions: list[str]
    conversation_summary: Optional[str] = None  # Summary để lưu vào DB


# System prompt for the AI chatbot
CHATBOT_SYSTEM_PROMPT = """Bạn là Calmi, một trợ lý tâm lý thân thiện và hỗ trợ cho học sinh. 

QUY TẮC QUAN TRỌNG:
- Luôn đồng cảm và thấu hiểu
- Không bao giờ phán xét
- **Luôn trả lời câu hỏi của học sinh dựa trên lịch sử trò chuyện (nếu có)**
- Không đưa ra lời khuyên y tế/chẩn đoán bệnh, NHƯNG có thể cung cấp thông tin chung (ví dụ: dấu hiệu phổ biến) nếu được hỏi.
- Sử dụng ngôn ngữ nhẹ nhàng, phù hợp với học sinh
- Trả lời ngắn gọn (2-4 câu)

KHI PHÁT HIỆN RỦI RO CAO/KHẨN CẤP:
- Vẫn trả lời câu hỏi của học sinh (nếu có) nhưng kèm lời khuyên tìm trợ giúp
- Khuyến khích nói chuyện với người lớn tin tưởng
- Đề nghị gọi đường dây hỗ trợ
- KHÔNG hỏi thêm chi tiết về ý định tự hại
- Giữ bình tĩnh, không hoảng loạn

ĐIỀU CHỈNH TONE DỰA TRÊN NHẬT KÝ CẢM XÚC:
- Nếu học sinh đang trải qua nhiều ngày buồn/stress: mềm mại hơn, đồng cảm hơn, nhẹ nhàng hơn
- Nếu học sinh đang vui vẻ: tích cực, khuyến khích duy trì năng lượng tốt
- Nếu cảm xúc lên xuống thất thường: hỏi về nguyên nhân một cách nhẹ nhàng"""


class ChatbotService:
    """
    AI-powered chatbot với LangChain conversation memory.
    Sử dụng summary thay vì lưu toàn bộ messages.
    """
    
    def __init__(self):
        # Use ChatOpenAI with gpt-4.1-nano (stable and fast)
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        
        # Summary LLM cũng dùng gpt-4.1-nano
        self.summary_llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        
        # Cache của memory theo session_id
        self._memory_cache: dict[int, ConversationSummaryBufferMemory] = {}
    
    def _get_or_create_memory(
        self,
        session: ChatSession,
        history: list[ChatMessage]
    ) -> ConversationSummaryBufferMemory:
        """
        Get hoặc tạo conversation memory cho session.
        
        ConversationSummaryBufferMemory:
        - Giữ N messages gần nhất trong buffer
        - Tóm tắt messages cũ hơn thành summary
        - Tiết kiệm tokens nhưng vẫn nhớ context
        """
        session_id = session.id
        
        # Check cache
        if session_id in self._memory_cache:
            return self._memory_cache[session_id]
        
        # Create new memory
        memory = ConversationSummaryBufferMemory(
            llm=self.summary_llm,
            max_token_limit=256,  # Giữ ~500 tokens gần nhất
            return_messages=True,
            ai_prefix="Calmi",
            human_prefix="Học sinh"
        )
        
        # Load existing summary nếu có
        if session.conversation_summary:
            memory.moving_summary_buffer = session.conversation_summary
        
        # Load recent messages vào buffer
        for msg in history[-5:]:  # 5 messages gần nhất
            if msg.sender_type == "USER":
                memory.chat_memory.add_user_message(msg.content)
            else:
                memory.chat_memory.add_ai_message(msg.content)
        
        # Cache
        self._memory_cache[session_id] = memory
        return memory
    
    def _get_recommended_actions(self, risk_level: str, risk_type: str) -> list[str]:
        """Determine recommended actions based on risk assessment."""
        actions = []
        
        if risk_level == "CRITICAL":
            actions.append("OPEN_SOS_MODULE")
            actions.append("OPEN_REPORT_MODULE")
        elif risk_level == "HIGH":
            actions.append("OPEN_SOS_MODULE")
            actions.append("OPEN_REPORT_MODULE")
        elif risk_level == "MEDIUM":
            if risk_type == "BULLYING":
                actions.append("OPEN_REPORT_MODULE")
            actions.append("OPEN_EXERCISES")
            actions.append("OPEN_EMOTION_DIARY")
        else:
            actions.append("OPEN_EXERCISES")
            actions.append("OPEN_EMOTION_DIARY")
        
        return actions
    
    def _get_risk_instruction(self, risk_level: str, risk_type: str) -> str:
        """Get specific instruction based on risk level."""
        if risk_level == "CRITICAL":
            return """HƯỚNG DẪN TRẢ LỜI:
- Trước hết, hãy trả lời câu hỏi của học sinh (nếu có context) một cách ngắn gọn.
- Sau đó, bày tỏ sự quan tâm và lo lắng.
- Khuyến khích gọi ngay đường dây hỗ trợ 1800-599-964 (miễn phí) hoặc nói chuyện với người lớn."""
        
        elif risk_level == "HIGH":
            return """HƯỚNG DẪN TRẢ LỜI:
- Trả lời câu hỏi của học sinh dựa trên context (nếu phù hợp).
- Thể hiện sự lo lắng và quan tâm an toàn.
- Khuyến khích báo cáo hoặc nói với người lớn.
- Đề cập đến nút SOS nếu cần."""
        
        elif risk_level == "MEDIUM":
            if risk_type == "BULLYING":
                return """HƯỚNG DẪN TRẢ LỜI:
- Trả lời thắc mắc của học sinh.
- Công nhận cảm xúc.
- Đề nghị ghi lại và báo cáo để được hỗ trợ."""
            return """HƯỚNG DẪN TRẢ LỜI:
- Trả lời câu hỏi của học sinh (như về triệu chứng, cảm xúc...).
- Đồng cảm và gợi ý các bài tập thư giãn."""
        
        else:
            return """HƯỚNG DẪN TRẢ LỜI:
- Trả lời tự nhiên theo dòng trò chuyện.
- Lắng nghe và đồng cảm.
- Gợi ý hoạt động tích cực."""
    
    def _format_mood_context(self, mood_history: list[dict] | None) -> str:
        """Format mood history into context string for AI."""
        if not mood_history:
            return "(Chưa có dữ liệu nhật ký cảm xúc)"
        
        # Map mood values to labels
        mood_labels = {
            100: "😊 Vui vẻ",
            80: "🙂 Bình thường",
            60: "😐 Buồn bực",
            40: "😟 Lo lắng",
            20: "😢 Rất buồn",
        }
        
        lines = []
        for entry in mood_history:
            date = entry.get("mood_date", "?")
            value = entry.get("mood_value", 0)
            note = entry.get("note", "")
            
            # Find closest mood label
            label = mood_labels.get(value, f"({value}/100)")
            day_str = f"- {date}: {label}"
            if note:
                day_str += f' - "{note}"'
            lines.append(day_str)
        
        if not lines:
            return "(Chưa có dữ liệu nhật ký cảm xúc)"
        
        # Calculate average mood
        values = [e.get("mood_value", 60) for e in mood_history]
        avg = sum(values) / len(values)
        
        trend = ""
        if avg >= 80:
            trend = "--> Nhìn chung học sinh đang có tâm trạng tốt 🌟"
        elif avg >= 60:
            trend = "--> Tâm trạng bình thường, có lúc vui có lúc buồn"
        elif avg >= 40:
            trend = "--> Học sinh có vẻ đang trải qua giai đoạn khó khăn 💖"
        else:
            trend = "--> Học sinh đang có dấu hiệu cần hỗ trợ nhiều hơn ❤️"
        
        return "\n".join(lines) + "\n" + trend
    
    def generate_reply(
        self,
        session: ChatSession,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
    ) -> ChatbotResponse:
        """
        Generate AI response sử dụng LangChain với conversation summary.
        
        Args:
            session: Chat session (để load/save summary)
            user_message: Current user message
            history: Previous messages for initial context
            risk_result: Risk detection result
            mood_history: Student's mood entries from last 5 days
            
        Returns:
            ChatbotResponse with AI message, actions, và summary
        """
        # Get conversation memory
        memory = self._get_or_create_memory(session, history)
        
        # Build risk instruction
        risk_instruction = self._get_risk_instruction(
            risk_result.risk_level,
            risk_result.risk_type,
        )
        
        # Format mood context
        mood_context = self._format_mood_context(mood_history)
        
        # Build prompt template
        # Note: {history} will be automatically injected by ConversationSummaryBufferMemory
        # We inject risk_level and risk_type directly into template (not as variables)
        # because ConversationChain only accepts memory variables + input
        template = f"""{CHATBOT_SYSTEM_PROMPT}

NHẬT KÝ CẢM XÚC 5 NGÀY GẦN NHẤT:
{mood_context}

ĐÁNH GIÁ RỦI RO: {risk_result.risk_level} - {risk_result.risk_type}

{risk_instruction}

Current conversation:
{{history}}

Học sinh: {{input}}
Calmi:"""

        prompt = PromptTemplate(
            input_variables=["input"],
            template=template
        )
        
        # Create conversation chain
        conversation = ConversationChain(
            llm=self.llm,
            memory=memory,
            prompt=prompt,
            verbose=False
        )
        
        try:
            # Generate response
            response = conversation.predict(input=user_message)

            
            ai_message = response.strip()
            
            # Get updated summary
            summary = memory.moving_summary_buffer if hasattr(memory, 'moving_summary_buffer') else None
            
        except Exception as e:
            print(f"[CHATBOT ERROR] {e}")
            ai_message = self._get_fallback_response(risk_result.risk_level)
            summary = None
        
        # Get recommended actions
        actions = self._get_recommended_actions(
            risk_result.risk_level,
            risk_result.risk_type,
        )
        
        return ChatbotResponse(
            ai_message=ai_message,
            recommended_actions=actions,
            conversation_summary=summary
        )
    
    async def generate_reply_stream(
        self,
        session: ChatSession,
        user_message: str,
        history: list[ChatMessage],
        risk_result: RiskDetectionResult,
        mood_history: list[dict] | None = None,
    ):
        """
        Generate AI response với streaming.
        Yields chunks of text as they arrive from OpenAI.
        
        Args:
            session: Chat session
            user_message: Current user message
            history: Previous messages
            risk_result: Risk detection result
            mood_history: Student's mood entries from last 5 days
            
        Yields:
            dict with 'type' and 'content' for each chunk
        """
        # Get conversation memory
        memory = self._get_or_create_memory(session, history)
        
        # Build risk instruction
        risk_instruction = self._get_risk_instruction(
            risk_result.risk_level,
            risk_result.risk_type,
        )
        
        # Format mood context
        mood_context = self._format_mood_context(mood_history)
        
        # Build prompt với memory history
        history_text = memory.load_memory_variables({}).get("history", "")
        
        full_prompt = f"""{CHATBOT_SYSTEM_PROMPT}

NHẬT KÝ CẢM XÚC 5 NGÀY GẦN NHẤT:
{mood_context}

ĐÁNH GIÁ RỦI RO: {risk_result.risk_level} - {risk_result.risk_type}

{risk_instruction}

Current conversation:
{history_text}

Học sinh: {user_message}
Calmi:"""
        
        full_response = ""
        
        try:
            # Stream response directly from LLM (ChatOpenAI)
            async for chunk in self.llm.astream(full_prompt):
                if chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "content": chunk.content}
            
            # Add to memory sau khi stream xong
            memory.chat_memory.add_user_message(user_message)
            memory.chat_memory.add_ai_message(full_response)
            
            # Get updated summary after streaming completes
            summary = memory.moving_summary_buffer if hasattr(memory, 'moving_summary_buffer') else None
            
            # Get recommended actions
            actions = self._get_recommended_actions(
                risk_result.risk_level,
                risk_result.risk_type,
            )
            
            # Send final metadata
            yield {
                "type": "done",
                "content": {
                    "full_text": full_response.strip(),
                    "actions": actions,
                    "summary": summary,
                }
            }
            
        except Exception as e:
            print(f"[CHATBOT STREAM ERROR] {e}")
            import traceback
            traceback.print_exc()
            fallback = self._get_fallback_response(risk_result.risk_level)
            # Stream fallback as tokens instead of error
            yield {"type": "token", "content": fallback}
            yield {
                "type": "done",
                "content": {
                    "full_text": fallback,
                    "actions": [],
                    "summary": None,
                }
            }


    
    def _get_fallback_response(self, risk_level: str) -> str:
        """Get fallback response when AI fails."""
        if risk_level == "CRITICAL":
            return (
                "Mình rất lo lắng cho em. Em không đơn độc. "
                "Hãy gọi ngay đường dây hỗ trợ 1800-599-964 (miễn phí) "
                "hoặc nói chuyện với người lớn mà em tin tưởng."
            )
        elif risk_level == "HIGH":
            return (
                "Mình hiểu em đang trải qua thời điểm khó khăn. "
                "Em có thể sử dụng nút SOS để được hỗ trợ ngay, "
                "hoặc báo cáo để thầy cô biết và giúp đỡ em."
            )
        elif risk_level == "MEDIUM":
            return (
                "Cảm ơn em đã chia sẻ. Mình hiểu cảm giác của em. "
                "Em có muốn kể thêm không? Hoặc em có thể viết nhật ký cảm xúc "
                "để giải tỏa."
            )
        else:
            return (
                "Mình ở đây để lắng nghe em. "
                "Em có thể thử các bài tập thư giãn hoặc viết nhật ký cảm xúc."
            )
    
    def clear_memory_cache(self, session_id: int):
        """Clear memory cache for a session (call when session ends)."""
        if session_id in self._memory_cache:
            del self._memory_cache[session_id]


# Singleton instance
_chatbot_service: ChatbotService | None = None


def get_chatbot_service() -> ChatbotService:
    """Get singleton chatbot service instance."""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
