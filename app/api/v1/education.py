"""
Education Router - API endpoints for Module 4 Preventive Education.
Only authenticated students can access these endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User
from app.schemas.common import api_error, api_response
from app.schemas.education import (
    BookletProgressRequest,
    DailyKindRespondRequest,
    ExerciseSubmitRequest,
    MinigameResultRequest,
)
from app.services.education_service import (
    AlreadyRespondedError,
    ContentNotActiveError,
    ContentNotFoundError,
    EducationService,
    InvalidContentTypeError,
    NoMessageTodayError,
)

router = APIRouter(prefix="/education", tags=["Education - Preventive Mental Health"])


# Dependency to get student user only
StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]


# ==========================================
# CONTENT ENDPOINTS
# ==========================================

@router.get(
    "/contents",
    response_model=dict,
    summary="Danh sách nội dung học tập",
    description="Lấy danh sách nội dung giáo dục (bài tập, sách, video, game).",
)
async def list_contents(
    current_user: StudentUser,
    content_type: str | None = Query(default=None, description="EXERCISE, BOOKLET, VIDEO, ARTICLE, MINIGAME"),
    topic: str | None = Query(default=None, description="stress, anxiety, bullying, kindness, etc."),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách nội dung giáo dục. (Cached 5 min)"""
    from app.core.cache import cache
    cache_key = f"edu:contents:{content_type}:{topic}:{limit}:{offset}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = EducationService(db)
    result = await service.list_contents(
        content_type=content_type,
        topic=topic,
        limit=limit,
        offset=offset,
    )
    
    contents_data = [
        {
            "id": c.id,
            "content_type": c.content_type,
            "title": c.title,
            "description": c.description,
            "topic": c.topic,
            "media_url": c.media_url,
        }
        for c in result.contents
    ]
    
    response = api_response(
        data={
            "contents": contents_data,
            "total": result.total,
        },
    )
    cache.set(cache_key, response, ttl=300)
    return response


@router.get(
    "/contents/{content_id}",
    response_model=dict,
    summary="Chi tiết nội dung",
    description="Lấy chi tiết nội dung, bao gồm câu hỏi cho bài tập quiz.",
)
async def get_content_detail(
    content_id: int,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy chi tiết nội dung.
    
    - Với bài tập EXERCISE, trả về danh sách câu hỏi
    - Với các loại khác, trả về thông tin cơ bản và media_url
    """
    service = EducationService(db)
    
    try:
        result = await service.get_content_detail(content_id)
        
        questions_data = [
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "order_index": q.order_index,
            }
            for q in result.questions
        ]
        
        return api_response(
            data={
                "id": result.id,
                "content_type": result.content_type,
                "title": result.title,
                "description": result.description,
                "topic": result.topic,
                "media_url": result.media_url,
                "questions": questions_data,
            },
        )
    
    except ContentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nội dung",
        )
    except ContentNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nội dung này không còn khả dụng",
        )


# ==========================================
# EXERCISE ENDPOINTS
# ==========================================

@router.post(
    "/exercises/{content_id}/submit",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Nộp bài tập",
    description="Nộp kết quả bài tập và nhận điểm.",
)
async def submit_exercise(
    content_id: int,
    request: ExerciseSubmitRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Nộp kết quả bài tập.
    
    - Với quiz: gửi danh sách câu trả lời, hệ thống tính điểm
    - Ghi lại thời gian hoàn thành
    """
    service = EducationService(db)
    
    try:
        result = await service.submit_exercise(
            user=current_user,
            content_id=content_id,
            answers=request.answers,
            duration_seconds=request.duration_seconds,
        )
        
        return api_response(
            data={
                "attempt_id": result.attempt_id,
                "score": result.score,
                "total_questions": result.total_questions,
                "correct_answers": result.correct_answers,
                "duration_seconds": result.duration_seconds,
            },
            message=result.message,
        )
    
    except ContentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bài tập",
        )
    except InvalidContentTypeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung này không phải bài tập",
        )


# ==========================================
# BOOKLET ENDPOINTS
# ==========================================

@router.post(
    "/booklets/{content_id}/progress",
    response_model=dict,
    summary="Cập nhật tiến độ đọc",
    description="Cập nhật tiến độ đọc sách/tài liệu.",
)
async def update_booklet_progress(
    content_id: int,
    request: BookletProgressRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật tiến độ đọc sách.
    
    - progress_percent: 0-100
    """
    service = EducationService(db)
    
    try:
        result = await service.update_booklet_progress(
            user=current_user,
            content_id=content_id,
            progress_percent=request.progress_percent,
        )
        
        return api_response(
            data={
                "content_id": result.content_id,
                "progress_percent": result.progress_percent,
                "read_at": result.read_at.isoformat(),
            },
            message="Đã lưu tiến độ đọc",
        )
    
    except ContentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài liệu",
        )
    except InvalidContentTypeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung này không phải sách/tài liệu",
        )


# ==========================================
# MINIGAME ENDPOINTS
# ==========================================

@router.post(
    "/minigames/{content_id}/result",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi kết quả minigame",
    description="Gửi kết quả chơi game và nhận điểm thưởng.",
)
async def submit_minigame_result(
    content_id: int,
    request: MinigameResultRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Gửi kết quả chơi minigame.
    
    - Nhận điểm thưởng dựa trên score
    """
    service = EducationService(db)
    
    try:
        result = await service.submit_minigame_result(
            user=current_user,
            content_id=content_id,
            score=request.score,
        )
        
        return api_response(
            data={
                "result_id": result.result_id,
                "score": result.score,
                "reward_points": result.reward_points,
            },
            message=result.message,
        )
    
    except ContentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy game",
        )
    except InvalidContentTypeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung này không phải minigame",
        )


# ==========================================
# DAILY KIND MESSAGE ENDPOINTS
# ==========================================

@router.get(
    "/daily-kind-message",
    response_model=dict,
    summary="Lời nhắn tốt đẹp hôm nay",
    description="Lấy lời nhắn tích cực của ngày hôm nay.",
)
async def get_daily_message(
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lấy lời nhắn tích cực hôm nay. (Cached 5 min)"""
    from app.core.cache import cache
    cache_key = f"edu:daily:{current_user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = EducationService(db)
    
    try:
        result = await service.get_daily_message(current_user)
        
        response = api_response(
            data={
                "id": result.id,
                "message_text": result.message_text,
                "active_date": result.active_date.isoformat(),
                "has_responded": result.has_responded,
                "my_response": result.my_response,
            },
        )
        cache.set(cache_key, response, ttl=300)
        return response
    
    except NoMessageTodayError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa có lời nhắn cho ngày hôm nay",
        )


@router.post(
    "/daily-kind-message/respond",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Phản hồi lời nhắn",
    description="Chia sẻ việc tốt bạn đã làm hôm nay.",
)
async def respond_to_daily_message(
    request: DailyKindRespondRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Phản hồi lời nhắn tích cực.
    
    - Mỗi ngày chỉ được phản hồi một lần
    """
    service = EducationService(db)
    
    try:
        result = await service.respond_to_daily_message(
            user=current_user,
            response_text=request.response_text,
        )
        
        return api_response(
            data={
                "response_id": result.response_id,
            },
            message=result.message,
        )
    
    except NoMessageTodayError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa có lời nhắn cho ngày hôm nay",
        )
    except AlreadyRespondedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã phản hồi lời nhắn hôm nay rồi",
        )


# ==========================================
# HISTORY ENDPOINTS
# ==========================================

@router.get(
    "/my/history",
    response_model=dict,
    summary="Lịch sử học tập",
    description="Xem lịch sử học tập của bạn.",
)
async def get_learning_history(
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lấy lịch sử học tập. (Cached 2 min)"""
    from app.core.cache import cache
    cache_key = f"edu:history:{current_user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    service = EducationService(db)
    result = await service.get_learning_history(current_user)
    
    response = api_response(
        data={
            "exercises": [
                {
                    "id": e.id,
                    "content_id": e.content_id,
                    "content_title": e.content_title,
                    "content_type": e.content_type,
                    "topic": e.topic,
                    "score": e.score,
                    "duration_seconds": e.duration_seconds,
                    "completed_at": e.completed_at.isoformat(),
                }
                for e in result.exercises
            ],
            "booklets": [
                {
                    "id": b.id,
                    "content_id": b.content_id,
                    "content_title": b.content_title,
                    "topic": b.topic,
                    "progress_percent": b.progress_percent,
                    "read_at": b.read_at.isoformat(),
                }
                for b in result.booklets
            ],
            "minigames": [
                {
                    "id": m.id,
                    "content_id": m.content_id,
                    "content_title": m.content_title,
                    "score": m.score,
                    "reward_points": m.reward_points,
                    "played_at": m.played_at.isoformat(),
                }
                for m in result.minigames
            ],
            "total_points": result.total_points,
        },
    )
    cache.set(cache_key, response, ttl=120)
    return response
