"""
AI-Powered Risk Detector Service.
Uses OpenAI gpt-4.1-nano to analyze messages and determine risk levels + recommended actions.
"""
import json
from dataclasses import dataclass
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
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
    risk_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")
    risk_type: str = Field(description="SELF_HARM, VIOLENCE, BULLYING, CYBER_BULLYING, EMOTIONAL, OTHER")
    signals: list[str] = Field(description="Detected risk signals")
    is_sensitive: bool = Field(description="true if sensitive content")
    recommended_actions: list[str] = Field(description="Actions to recommend")
    reasoning: str = Field(description="Brief explanation")


# OPTIMIZED: Condensed prompt for faster processing
RISK_ANALYSIS_PROMPT = """Phân tích tin nhắn học sinh và xác định rủi ro.

TIN NHẮN: "{message}"

CONTEXT: {conversation_context}

LƯU Ý QUAN TRỌNG: Nếu context có vấn đề nghiêm trọng (bị đánh, bắt nạt, trầm cảm), GIỮ NGUYÊN mức rủi ro cao và actions tương ứng.

MỨC ĐỘ:
• CRITICAL: Tự tử, tự hại, xâm hại tình dục, bạo hành nghiêm trọng → OPEN_SOS_MODULE
• HIGH: Bị đánh, đe dọa, trầm cảm, cyberbullying nặng → OPEN_SOS_MODULE + OPEN_REPORT_MODULE
• MEDIUM: Bắt nạt, cô lập, xung đột, quấy rối → OPEN_REPORT_MODULE
• LOW: Buồn, stress, lo lắng → OPEN_EXERCISES hoặc OPEN_EMOTION_DIARY

LOẠI RỦI RO: SELF_HARM, VIOLENCE, BULLYING, CYBER_BULLYING, EMOTIONAL, OTHER

HÀNH ĐỘNG (chọn 1-2 phù hợp):
• OPEN_SOS_MODULE: Khẩn cấp, cần người lớn can thiệp (CRITICAL/HIGH)
• OPEN_REPORT_MODULE: Cần báo cáo sự việc (bị đánh, bắt nạt, quấy rối, đe dọa)
• OPEN_EXERCISES: Thư giãn, giảm stress
• OPEN_EMOTION_DIARY: Ghi chép cảm xúc

VÍ DỤ: "bị đánh" → HIGH, VIOLENCE, [OPEN_SOS_MODULE, OPEN_REPORT_MODULE]

{format_instructions}"""


class AIRiskDetectorService:
    """
    AI-powered risk detection service.
    Uses gpt-4.1-nano for fast and accurate classification.
    
    OPTIMIZED: Shorter timeout and limited tokens for speed.
    """
    
    def __init__(self):
        # OPTIMIZED: Fast settings for classification task
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,  # Low temp for consistent classification
            openai_api_key=settings.OPENAI_API_KEY,
            max_retries=1,  # Quick fail on error
            timeout=10.0,  # 10s timeout - classification should be fast
            max_tokens=200,  # JSON output is small
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
    
    async def analyze_async(
        self, 
        text: str,
        conversation_summary: str | None = None,
        last_risk_level: str | None = None,
        last_risk_type: str | None = None,
    ) -> RiskDetectionResult:
        """
        Async version of analyze with full context support.
        Use this for parallel processing to avoid blocking.
        """
        try:
            format_instructions = self.output_parser.get_format_instructions()
            
            # Build context string (same as sync version)
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
            print(f"[AI RISK DETECTOR ASYNC ERROR] {e}")
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
