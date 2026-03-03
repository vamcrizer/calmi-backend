"""
Quiz Router - API endpoints cho he thong quiz kieu Candy Crush.

Endpoints:
- GET  /quiz/levels          : Ban do levels (Overview giong Candy Crush)
- GET  /quiz/levels/{id}     : Chi tiet level + cau hoi
- POST /quiz/levels/{id}/submit : Nop bai quiz
- GET  /quiz/progress        : Tong quan tien do
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User
from app.schemas.common import api_response
from app.schemas.quiz import QuizSubmitRequest
from app.services.quiz_service import (
    QuizLevelLockedError,
    QuizLevelNotFoundError,
    QuizNoQuestionsError,
    QuizService,
)

router = APIRouter(prefix="/quiz", tags=["Quiz - Candy Crush Style"])

# Dependency: chi STUDENT duoc lam quiz
StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]


# ==========================================
# LEVEL MAP (Ban do man choi)
# ==========================================

@router.get(
    "/levels",
    summary="Ban do cac man choi",
    description="Lay danh sach levels voi trang thai mo khoa va so sao (giong ban do Candy Crush).",
)
async def get_level_map(
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """Tra ve ban do tat ca levels. (Cached 5 min)"""
    from app.core.cache import cache
    cache_key = f"quiz:{current_user.id}:levels"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = QuizService(db)
    level_map = await service.get_level_map(current_user.id)
    
    response = api_response(
        data={"levels": level_map},
        message=f"Tong cong {len(level_map)} levels",
    )
    cache.set(cache_key, response, ttl=300)
    return response


# ==========================================
# LEVEL DETAIL (Chi tiet man choi + cau hoi)
# ==========================================

@router.get(
    "/levels/{level_id}",
    summary="Chi tiet man choi",
    description="Lay cau hoi cua man choi. Chi hoat dong voi levels da mo khoa.",
)
async def get_level_detail(
    level_id: int,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet level va danh sach cau hoi.
    
    - Kiem tra level da mo khoa chua
    - Tra ve cau hoi (KHONG tra dap an dung)
    - Voi matching: shuffle cot phai
    - Voi ordering: shuffle thu tu
    """
    service = QuizService(db)
    
    try:
        detail = await service.get_level_questions(current_user.id, level_id)
        return api_response(data=detail)
    
    except QuizLevelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except QuizLevelLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except QuizNoQuestionsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ==========================================
# SUBMIT QUIZ (Nop bai)
# ==========================================

@router.post(
    "/levels/{level_id}/submit",
    summary="Nop bai quiz",
    description="Nop dap an, he thong cham diem va tinh sao tu dong.",
)
async def submit_quiz(
    level_id: int,
    request: QuizSubmitRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Nop bai quiz.
    
    Logic Candy Crush:
    - Cham diem tu dong (ho tro 4 loai cau hoi)
    - Tinh sao: 3 sao (>=90%), 2 sao (>=70%), 1 sao (>=50%)
    - Cap nhat best score (chi cap nhat neu tot hon)
    - Mo khoa level tiep theo neu dat >= 1 sao
    
    Request body:
    - answers: [{question_id: "F1_Q1", answer: "B"}, ...]
    - duration_seconds: thoi gian lam bai (optional)
    """
    service = QuizService(db)
    
    try:
        # Convert request to dict list
        answers_data = [
            {"question_id": a.question_id, "answer": a.answer}
            for a in request.answers
        ]
        
        result = await service.submit_quiz(
            user_id=current_user.id,
            level_id=level_id,
            answers=answers_data,
            duration_seconds=request.duration_seconds,
        )
        
        # BUG-001 fix: pop message TRUOC khi build response
        msg = result.pop("message", "")
        
        # BUG-006 fix: Xoa cache sau khi submit (level moi mo khoa hien thi ngay)
        from app.core.cache import cache
        cache.delete(f"quiz:{current_user.id}:levels")
        cache.delete(f"quiz:{current_user.id}:progress")
        
        return api_response(
            data=result,
            message=msg,
            status_code=201,
        )
    
    except QuizLevelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except QuizLevelLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except QuizNoQuestionsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ==========================================
# OVERALL PROGRESS
# ==========================================

@router.get(
    "/progress",
    summary="Tong quan tien do",
    description="Xem tong so levels, so sao, phan tram hoan thanh.",
)
async def get_progress(
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lay tong quan tien do quiz. (Cached 2 min)"""
    from app.core.cache import cache
    cache_key = f"quiz:{current_user.id}:progress"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = QuizService(db)
    progress = await service.get_overall_progress(current_user.id)
    
    response = api_response(
        data=progress,
        message="Tien do hoc tap cua ban",
    )
    cache.set(cache_key, response, ttl=120)
    return response
