"""
Schemas for Module 4 - Preventive Education.
DTOs for educational content, exercises, and daily messages.
"""
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


# ==========================================
# ENUMS
# ==========================================

class ContentType(str, Enum):
    """Types of educational content."""
    EXERCISE = "EXERCISE"
    BOOKLET = "BOOKLET"
    VIDEO = "VIDEO"
    ARTICLE = "ARTICLE"
    MINIGAME = "MINIGAME"


class Topic(str, Enum):
    """Content topics."""
    STRESS = "stress"
    ANXIETY = "anxiety"
    BULLYING = "bullying"
    KINDNESS = "kindness"
    CONFIDENCE = "confidence"
    EMOTIONAL_REGULATION = "emotional_regulation"


# ==========================================
# CONTENT SCHEMAS
# ==========================================

class QuestionItem(BaseModel):
    """Question in a quiz exercise."""
    id: int
    question_text: str
    options: list[str]
    order_index: int


class ContentListItem(BaseModel):
    """Item in content list."""
    id: int
    content_type: ContentType
    title: str
    description: str | None
    topic: str
    media_url: str | None
    
    class Config:
        from_attributes = True


class ContentDetail(ContentListItem):
    """Detailed content with questions for exercises."""
    questions: list[QuestionItem] = []


class ContentListResponse(BaseModel):
    """Response for content listing."""
    contents: list[ContentListItem]
    total: int


# ==========================================
# EXERCISE SCHEMAS
# ==========================================

class ExerciseSubmitRequest(BaseModel):
    """Request to submit exercise result."""
    answers: list[str] = Field(
        default=[],
        description="List of answers for quiz questions",
    )
    duration_seconds: int = Field(
        ge=0,
        le=7200,  # Max 2 hours
        description="Time spent on exercise",
    )


class ExerciseSubmitResponse(BaseModel):
    """Response after submitting exercise."""
    attempt_id: int
    score: int | None
    total_questions: int
    correct_answers: int
    duration_seconds: int
    message: str


# ==========================================
# BOOKLET SCHEMAS
# ==========================================

class BookletProgressRequest(BaseModel):
    """Request to update reading progress."""
    progress_percent: int = Field(ge=0, le=100)


class BookletProgressResponse(BaseModel):
    """Response for booklet progress update."""
    content_id: int
    progress_percent: int
    read_at: datetime


# ==========================================
# MINIGAME SCHEMAS
# ==========================================

class MinigameResultRequest(BaseModel):
    """Request to submit minigame result."""
    score: int = Field(ge=0)
    

class MinigameResultResponse(BaseModel):
    """Response after submitting minigame result."""
    result_id: int
    score: int
    reward_points: int
    message: str


# ==========================================
# DAILY KIND MESSAGE SCHEMAS
# ==========================================

class DailyKindMessageResponse(BaseModel):
    """Today's kind message."""
    id: int
    message_text: str
    active_date: date
    has_responded: bool = False
    my_response: str | None = None


class DailyKindRespondRequest(BaseModel):
    """Request to respond to daily message."""
    response_text: str = Field(
        min_length=1,
        max_length=500,
        description="Student's kind action for today",
    )


class DailyKindRespondResponse(BaseModel):
    """Response after submitting daily kind response."""
    response_id: int
    message: str


# ==========================================
# HISTORY SCHEMAS
# ==========================================

class HistoryExerciseItem(BaseModel):
    """Exercise attempt in history."""
    id: int
    content_id: int
    content_title: str
    content_type: str
    topic: str
    score: int | None
    duration_seconds: int | None
    completed_at: datetime


class HistoryBookletItem(BaseModel):
    """Booklet read in history."""
    id: int
    content_id: int
    content_title: str
    topic: str
    progress_percent: int
    read_at: datetime


class HistoryMinigameItem(BaseModel):
    """Minigame result in history."""
    id: int
    content_id: int
    content_title: str
    score: int
    reward_points: int
    played_at: datetime


class LearningHistoryResponse(BaseModel):
    """Student's complete learning history."""
    exercises: list[HistoryExerciseItem]
    booklets: list[HistoryBookletItem]
    minigames: list[HistoryMinigameItem]
    total_points: int
