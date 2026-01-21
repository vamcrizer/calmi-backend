"""
Risk Detector Service - Rule-based risk detection for chat messages.
Easily replaceable with AI-based detection in the future.
"""
from dataclasses import dataclass
import re


@dataclass
class RiskDetectionResult:
    """Result from risk detection analysis."""
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_type: str   # EMOTIONAL, BULLYING, SELF_HARM, OTHER
    signals: list[str]
    is_sensitive: bool


class RiskDetectorService:
    """
    Rule-based risk detection service.
    Analyzes text for risk indicators using keyword patterns.
    
    Designed to be easily replaceable with an LLM-based detector.
    """
    
    # Vietnamese keywords for risk detection
    # CRITICAL: Imminent danger, self-harm ideation
    CRITICAL_PATTERNS = [
        r"muốn chết",
        r"muốn tự tử",
        r"không muốn sống",
        r"tự sát",
        r"kết thúc cuộc sống",
        r"tự làm đau",
        r"cắt tay",
        r"nhảy lầu",
        r"uống thuốc",
        r"giết mình",
        r"sẽ chết",
        r"bị xâm hại",
        r"bị hiếp",
        r"bị cưỡng",
    ]
    
    # HIGH: Direct threats, violence, fear of harm
    HIGH_PATTERNS = [
        r"bị đánh",
        r"bị đe dọa giết",
        r"bị đe doạ giết",
        r"sợ bị giết",
        r"họ sẽ đánh",
        r"bị thương nặng",
        r"đánh tôi rất đau",
        r"sợ về nhà",
        r"bị bạo hành",
        r"bị cấu xé",
        r"đánh vào mặt",
        r"đánh vào đầu",
        r"bị nhốt",
        r"bị trói",
    ]
    
    # MEDIUM: Bullying indicators
    MEDIUM_PATTERNS = [
        r"bị bắt nạt",
        r"bị đe doạ",
        r"bị đe dọa",
        r"bị cô lập",
        r"bị tẩy chay",
        r"bị nói xấu",
        r"bị chửi",
        r"bị xúc phạm",
        r"bị trêu chọc",
        r"bị ép buộc",
        r"không ai chơi",
        r"bị loại ra",
        r"bị bỏ rơi",
        r"bị ghét",
        r"bị khinh",
        r"bị chê bai",
        r"bị đánh nhẹ",
        r"bị đẩy",
        r"bị giật tóc",
        r"bị giấu đồ",
        r"bị lấy tiền",
        r"bị quấy rối",
    ]
    
    # LOW: Mild distress, sadness
    LOW_PATTERNS = [
        r"buồn",
        r"chán",
        r"mệt mỏi",
        r"căng thẳng",
        r"lo lắng",
        r"sợ",
        r"không vui",
        r"grumpy",
        r"cô đơn",
        r"không có bạn",
        r"khó ngủ",
        r"áp lực",
        r"stress",
        r"không tập trung",
        r"thiếu động lực",
    ]
    
    # Risk type detection patterns
    SELF_HARM_PATTERNS = [
        r"tự tử", r"muốn chết", r"tự làm đau", r"cắt tay",
        r"không muốn sống", r"kết thúc", r"giết mình",
    ]
    
    BULLYING_PATTERNS = [
        r"bắt nạt", r"đánh", r"đe doạ", r"đe dọa", r"cô lập",
        r"tẩy chay", r"nói xấu", r"chửi", r"trêu chọc",
        r"bỏ rơi", r"loại ra", r"ghét", r"khinh",
    ]
    
    def __init__(self):
        # Pre-compile patterns for efficiency
        self._critical_re = [re.compile(p, re.IGNORECASE) for p in self.CRITICAL_PATTERNS]
        self._high_re = [re.compile(p, re.IGNORECASE) for p in self.HIGH_PATTERNS]
        self._medium_re = [re.compile(p, re.IGNORECASE) for p in self.MEDIUM_PATTERNS]
        self._low_re = [re.compile(p, re.IGNORECASE) for p in self.LOW_PATTERNS]
        self._self_harm_re = [re.compile(p, re.IGNORECASE) for p in self.SELF_HARM_PATTERNS]
        self._bullying_re = [re.compile(p, re.IGNORECASE) for p in self.BULLYING_PATTERNS]
    
    def analyze(self, text: str) -> RiskDetectionResult:
        """
        Analyze text for risk indicators.
        
        Args:
            text: Message content to analyze
            
        Returns:
            RiskDetectionResult with level, type, signals, and sensitivity flag
        """
        text_lower = text.lower()
        signals = []
        
        # Check CRITICAL first (highest priority)
        for pattern in self._critical_re:
            match = pattern.search(text_lower)
            if match:
                signals.append(match.group())
        
        if signals:
            risk_type = self._determine_risk_type(text_lower)
            return RiskDetectionResult(
                risk_level="CRITICAL",
                risk_type=risk_type,
                signals=list(set(signals)),
                is_sensitive=True,
            )
        
        # Check HIGH
        for pattern in self._high_re:
            match = pattern.search(text_lower)
            if match:
                signals.append(match.group())
        
        if signals:
            risk_type = self._determine_risk_type(text_lower)
            return RiskDetectionResult(
                risk_level="HIGH",
                risk_type=risk_type,
                signals=list(set(signals)),
                is_sensitive=True,
            )
        
        # Check MEDIUM
        for pattern in self._medium_re:
            match = pattern.search(text_lower)
            if match:
                signals.append(match.group())
        
        if signals:
            risk_type = self._determine_risk_type(text_lower)
            return RiskDetectionResult(
                risk_level="MEDIUM",
                risk_type=risk_type,
                signals=list(set(signals)),
                is_sensitive=False,
            )
        
        # Check LOW
        for pattern in self._low_re:
            match = pattern.search(text_lower)
            if match:
                signals.append(match.group())
        
        if signals:
            return RiskDetectionResult(
                risk_level="LOW",
                risk_type="EMOTIONAL",
                signals=list(set(signals)),
                is_sensitive=False,
            )
        
        # Default: LOW with no specific signals
        return RiskDetectionResult(
            risk_level="LOW",
            risk_type="OTHER",
            signals=[],
            is_sensitive=False,
        )
    
    def _determine_risk_type(self, text: str) -> str:
        """Determine the type of risk based on patterns."""
        # Check for self-harm first
        for pattern in self._self_harm_re:
            if pattern.search(text):
                return "SELF_HARM"
        
        # Check for bullying
        for pattern in self._bullying_re:
            if pattern.search(text):
                return "BULLYING"
        
        # Default to OTHER
        return "OTHER"


# Singleton instance
_risk_detector: RiskDetectorService | None = None


def get_risk_detector() -> RiskDetectorService:
    """Get singleton risk detector instance."""
    global _risk_detector
    if _risk_detector is None:
        _risk_detector = RiskDetectorService()
    return _risk_detector
