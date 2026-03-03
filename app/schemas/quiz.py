"""
Pydantic schemas cho Quiz system (Candy Crush style).
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ==========================================
# QUIZ LEVEL SCHEMAS
# ==========================================

class QuizLevelMap(BaseModel):
    """Hien thi tren ban do (danh sach levels)."""
    id: int
    file_id: str
    set_number: int
    set_title: str
    tags: list[str] = []
    unlock_order: int
    # Progress cua user
    is_unlocked: bool = False
    stars: int = 0  # 0-3
    best_score: float = 0.0
    attempt_count: int = 0
    question_count: int = 0
    
    class Config:
        from_attributes = True


class QuizLevelDetail(BaseModel):
    """Chi tiet level khi chon de lam."""
    id: int
    file_id: str
    set_number: int
    set_title: str
    tags: list[str] = []
    questions: list["QuizQuestionOut"] = []
    
    class Config:
        from_attributes = True


# ==========================================
# QUIZ QUESTION SCHEMAS
# ==========================================

class QuizQuestionOut(BaseModel):
    """Cau hoi tra ve cho frontend (KHONG tra ve dap an dung)."""
    id: int
    question_id: str
    question_type: str  # multiple_choice, fill_blank, matching, ordering
    prompt: str
    options: list[dict[str, Any]] | None = []
    interaction: dict[str, Any] | None = {}
    order_index: int
    
    class Config:
        from_attributes = True


# ==========================================
# QUIZ ANSWER / SUBMIT SCHEMAS
# ==========================================

class QuizAnswerItem(BaseModel):
    """Moi cau tra loi cua user."""
    question_id: str = Field(..., description="ID cau hoi (F1_Q1, F2_Q3,...)")
    answer: Any = Field(..., description="Dap an: string cho MC, list cho ordering/matching/fill_blank")


class QuizSubmitRequest(BaseModel):
    """Request nop bai quiz."""
    answers: list[QuizAnswerItem] = Field(..., min_length=1, description="Danh sach cau tra loi")
    duration_seconds: int | None = Field(None, ge=0, description="Thoi gian lam bai (giay)")


class QuizSubmitResult(BaseModel):
    """Ket qua lam quiz."""
    attempt_id: int
    level_id: int
    score: float = Field(..., description="Diem so (0-100)")
    stars: int = Field(..., ge=0, le=3, description="So sao dat duoc")
    correct_count: int
    total_questions: int
    is_new_best: bool = Field(False, description="Co phai ky luc moi khong")
    next_level_unlocked: bool = Field(False, description="Da mo khoa level ke tiep chua")
    message: str = ""


# ==========================================
# QUIZ PROGRESS SCHEMAS
# ==========================================

class QuizOverallProgress(BaseModel):
    """Tong quan tien do quiz."""
    total_levels: int
    completed_levels: int  # >= 1 star
    total_stars: int  # Tong so sao (max = total_levels * 3)
    max_possible_stars: int
    completion_percent: float
