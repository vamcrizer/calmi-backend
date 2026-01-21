"""
Schemas for Module 3 - AI Psychological Chatbot.
DTOs for chat sessions, messages, and risk detection.
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ==========================================
# ENUMS
# ==========================================

class RiskLevel(str, Enum):
    """Risk severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskType(str, Enum):
    """Types of detected risk."""
    EMOTIONAL = "EMOTIONAL"
    BULLYING = "BULLYING"
    SELF_HARM = "SELF_HARM"
    OTHER = "OTHER"


class SenderType(str, Enum):
    """Message sender types."""
    USER = "USER"
    AI = "AI"


class SessionStatus(str, Enum):
    """Chat session status."""
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class RecommendedAction(str, Enum):
    """Recommended actions based on risk assessment."""
    OPEN_REPORT_MODULE = "OPEN_REPORT_MODULE"      # Module 1
    OPEN_SOS_MODULE = "OPEN_SOS_MODULE"            # Module 2
    OPEN_EXERCISES = "OPEN_EXERCISES"              # Module 4
    OPEN_EMOTION_DIARY = "OPEN_EMOTION_DIARY"      # Module 5


# ==========================================
# SESSION SCHEMAS
# ==========================================

class SessionCreateResponse(BaseModel):
    """Response when creating a new chat session."""
    session_id: int
    started_at: datetime
    status: SessionStatus
    
    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    """Item in session list response."""
    id: int
    started_at: datetime
    ended_at: datetime | None
    status: SessionStatus
    last_risk_level: RiskLevel | None
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: list[SessionListItem]
    total: int


class EndSessionResponse(BaseModel):
    """Response when ending a session."""
    session_id: int
    status: SessionStatus
    ended_at: datetime


# ==========================================
# MESSAGE SCHEMAS
# ==========================================

class MessageCreateRequest(BaseModel):
    """Request to send a message."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Message content",
    )


class MessageCreateResponse(BaseModel):
    """Response after sending a message."""
    user_message_id: int
    ai_message_id: int
    ai_message: str
    risk_level: RiskLevel
    risk_type: RiskType
    recommended_actions: list[RecommendedAction]


class MessageListItem(BaseModel):
    """Item in message list response."""
    id: int
    sender_type: SenderType
    content: str
    risk_level: RiskLevel | None
    risk_type: RiskType | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Response for listing messages."""
    messages: list[MessageListItem]
    total: int


# ==========================================
# RISK DETECTION SCHEMAS
# ==========================================

class RiskDetectionResult(BaseModel):
    """Result from risk detection analysis."""
    risk_level: RiskLevel
    risk_type: RiskType
    signals: list[str]
    is_sensitive: bool
