"""
AI-Powered Risk Detector Service.
Uses OpenAI gpt-4.1-nano to analyze messages and determine risk levels + recommended actions.
"""
from dataclasses import dataclass
from typing import Optional
import json
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


@dataclass
class RiskDetectionResult:
    """Result from risk detection analysis."""
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_type: str   # EMOTIONAL, BULLYING, SELF_HARM, VIOLENCE, CYBER_BULLYING, OTHER
    signals: list[str]
    is_sensitive: bool
    recommended_actions: list[str]  # AI decides actions


# Pydantic model for structured output
class RiskAnalysis(BaseModel):
    risk_level: str = Field(description="Mức độ rủi ro: LOW, MEDIUM, HIGH, hoặc CRITICAL")
    risk_type: str = Field(description="Loại rủi ro: SELF_HARM, VIOLENCE, BULLYING, CYBER_BULLYING, EMOTIONAL, hoặc OTHER")
    signals: list[str] = Field(description="Danh sách các dấu hiệu phát hiện được")
    is_sensitive: bool = Field(description="true nếu nội dung nhạy cảm, false nếu không")
    recommended_actions: list[str] = Field(description="Danh sách hành động đề xuất")
    reasoning: str = Field(description="Giải thích ngắn gọn lý do đánh giá")


# Prompt for AI to analyze risk WITH conversation context
RISK_ANALYSIS_PROMPT = """Bạn là hệ thống phân tích rủi ro cho học sinh. Phân tích tin nhắn và xác định mức độ rủi ro.

TIN NHẮN HIỆN TẠI:
"{message}"

CONTEXT CUỘC TRÒ CHUYỆN (nếu có):
{conversation_context}

ĐẶC BIỆT QUAN TRỌNG:
- Nếu có conversation context cho thấy học sinh đang gặp vấn đề nghiêm trọng (bị đánh, bị bắt nạt, trầm cảm...), 
  thì PHẢI giữ nguyên mức rủi ro và recommended actions tương ứng, NGAY CẢ KHI tin nhắn hiện tại không chứa keywords.
- Ví dụ: Nếu context là "học sinh nói bị đánh" và tin nhắn hiện tại là "vậy mình phải làm gì", 
  vẫn phải đề xuất OPEN_REPORT_MODULE vì context vẫn liên quan đến violence/bullying.

QUY TẮC ĐÁNH GIÁ:

**CRITICAL** (Khẩn cấp - Cần can thiệp ngay):
- Ý định tự tử, tự làm đau bản thân
- Bị xâm hại tình dục
- Đang bị bạo hành nghiêm trọng

**HIGH** (Nghiêm trọng):
- Đe dọa bạo lực trực tiếp (online hoặc offline)
- Bị đánh, bị thương
- Sợ hãi về an toàn bản thân
- Bị quấy rối tình dục
- Cyberbullying nghiêm trọng (đe dọa, lan truyền ảnh/video, tống tiền)
- **Trầm cảm**, rối loạn lo âu nặng, các vấn đề tâm lý nghiêm trọng
- Cảm giác vô vọng kéo dài

**MEDIUM** (Cần hỗ trợ):
- Bị bắt nạt (trực tiếp hoặc online)
- Bị cô lập, tẩy chay
- Bị nói xấu, chửi bới
- Bị quấy rối online (nhắn tin liên tục, theo dõi)
- Xung đột nghiêm trọng với bạn bè/gia đình
- Thay đổi tính nết, thu mình lại

**LOW** (Hỗ trợ cảm xúc):
- Buồn, chán, mệt mỏi
- Lo lắng về học tập
- Cảm thấy cô đơn
- Stress bình thường

LOẠI RỦI RO:
- SELF_HARM: Tự làm hại bản thân (bao gồm cả ý nghĩ tự tử tiềm ẩn)
- VIOLENCE: Bạo lực thể chất
- BULLYING: Bắt nạt trực tiếp
- CYBER_BULLYING: Bắt nạt qua mạng, đe dọa online
- EMOTIONAL: Vấn đề cảm xúc, trầm cảm, lo âu
- OTHER: Khác

HÀNH ĐỘNG ĐỀ XUẤT (chọn 1-3 phù hợp nhất dựa trên CONTEXT + tin nhắn hiện tại):
- OPEN_SOS_MODULE: Khi cần gọi trợ giúp khẩn cấp hoặc hỗ trợ chuyên sâu (CRITICAL/HIGH/Trầm cảm)
- OPEN_REPORT_MODULE: Khi cần báo cáo sự việc (bắt nạt, quấy rối, đe dọa, bị đánh)
- OPEN_EXERCISES: Gợi ý bài tập thư giãn (stress, lo lắng)
- OPEN_EMOTION_DIARY: Gợi ý viết nhật ký cảm xúc (buồn, cô đơn)

{format_instructions}
"""


class AIRiskDetectorService:
    """
    AI-powered risk detection service.
    Uses gpt-4.1-nano for fast and accurate classification.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.3,  # Low temp for consistent classification
            openai_api_key=settings.OPENAI_API_KEY,
        )
        
        # Use Pydantic-based parser
        self.output_parser = JsonOutputParser(pydantic_object=RiskAnalysis)
        self.prompt = ChatPromptTemplate.from_template(RISK_ANALYSIS_PROMPT)
    
    def analyze(
        self, 
        text: str,
        conversation_summary: str | None = None,
        last_risk_level: str | None = None,
        last_risk_type: str | None = None,
    ) -> RiskDetectionResult:
        """
        Analyze text for risk using AI.
        
        Args:
            text: Current message to analyze
            conversation_summary: Summary of previous conversation (from LangChain)
            last_risk_level: Previous risk level from session (HIGH, MEDIUM, etc.)
            last_risk_type: Previous risk type from session (BULLYING, VIOLENCE, etc.)
        """
        try:
            format_instructions = self.output_parser.get_format_instructions()
            
            # Build context string
            context_parts = []
            if conversation_summary:
                context_parts.append(f"Tóm tắt cuộc trò chuyện trước: {conversation_summary}")
            if last_risk_level and last_risk_level not in ["LOW", "OTHER"]:
                context_parts.append(f"Mức rủi ro trước đó: {last_risk_level}")
            if last_risk_type and last_risk_type not in ["OTHER"]:
                context_parts.append(f"Loại rủi ro trước đó: {last_risk_type}")
            
            conversation_context = "\n".join(context_parts) if context_parts else "(Không có context trước đó)"
            
            messages = self.prompt.format_messages(
                message=text,
                conversation_context=conversation_context,
                format_instructions=format_instructions,
            )
            
            response = self.llm.invoke(messages)
            parsed = self.output_parser.parse(response.content)
            
            signals = parsed.get("signals", [])
            if isinstance(signals, str):
                signals = [signals]
            
            actions = parsed.get("recommended_actions", [])
            if isinstance(actions, str):
                actions = [actions]
            
            return RiskDetectionResult(
                risk_level=parsed.get("risk_level", "LOW"),
                risk_type=parsed.get("risk_type", "OTHER"),
                signals=signals,
                is_sensitive=parsed.get("is_sensitive", False),
                recommended_actions=actions,
            )
            
        except Exception as e:
            print(f"[AI RISK DETECTOR ERROR] {e}")
            import traceback
            traceback.print_exc()
            return RiskDetectionResult(
                risk_level="LOW",
                risk_type="OTHER",
                signals=[],
                is_sensitive=False,
                recommended_actions=["OPEN_EXERCISES"],
            )
    
    async def analyze_async(self, text: str) -> RiskDetectionResult:
        """Async version of analyze."""
        try:
            format_instructions = self.output_parser.get_format_instructions()
            messages = self.prompt.format_messages(
                message=text,
                format_instructions=format_instructions,
            )
            
            response = await self.llm.ainvoke(messages)
            parsed = self.output_parser.parse(response.content)
            
            signals = parsed.get("signals", [])
            if isinstance(signals, str):
                signals = [signals]
            
            actions = parsed.get("recommended_actions", [])
            if isinstance(actions, str):
                actions = [actions]
            
            return RiskDetectionResult(
                risk_level=parsed.get("risk_level", "LOW"),
                risk_type=parsed.get("risk_type", "OTHER"),
                signals=signals,
                is_sensitive=parsed.get("is_sensitive", False),
                recommended_actions=actions,
            )
            
        except Exception as e:
            print(f"[AI RISK DETECTOR ERROR] {e}")
            import traceback
            traceback.print_exc()
            return RiskDetectionResult(
                risk_level="LOW",
                risk_type="OTHER",
                signals=[],
                is_sensitive=False,
                recommended_actions=["OPEN_EXERCISES"],
            )


# Singleton instance
_ai_risk_detector: AIRiskDetectorService | None = None


def get_ai_risk_detector() -> AIRiskDetectorService:
    """Get singleton AI risk detector instance."""
    global _ai_risk_detector
    if _ai_risk_detector is None:
        _ai_risk_detector = AIRiskDetectorService()
    return _ai_risk_detector
