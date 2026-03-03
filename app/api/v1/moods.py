"""
Router for Mood Tracking - Student emotion diary.

OPTIMIZED: In-memory caching for all GET endpoints.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.cache import cache
from app.models.user import User
from app.schemas.common import api_list_response, api_response
from app.schemas.mood import (
    MoodEntryCreate,
    MoodEntryRead,
    MoodStatsDay,
    MoodStatsResponse,
    MoodStreakResponse,
)
from app.services.mood_service import MoodService

router = APIRouter(prefix="/moods", tags=["Moods - Emotion Diary"])

# Cache TTLs
MOOD_CACHE_TTL = 120       # 2 phút cho mood data
AI_SUMMARY_CACHE_TTL = 600  # 10 phút cho AI summary (tốn tiền OpenAI)


def get_mood_service(db: AsyncSession = Depends(get_db)) -> MoodService:
    """Dependency injection for MoodService."""
    return MoodService(db)


@router.post("/")
async def create_mood_entry(
    data: MoodEntryCreate,
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """
    Create or update mood entry for current user.
    Invalidates cache after write.
    """
    entry = await service.create_or_update_mood(current_user, data)
    
    # Invalidate tất cả mood cache của user này
    cache.delete_pattern(f"moods:{current_user.id}:*")
    
    return api_response(
        data=MoodEntryRead.model_validate(entry).model_dump(),
        message="Ghi nhat ky cam xuc thanh cong",
        status_code=201,
    )


@router.get("/my")
async def get_my_moods(
    from_date: date | None = Query(None, description="From date"),
    to_date: date | None = Query(None, description="To date"),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """Get mood history for current user. (Cached 2 min)"""
    cache_key = f"moods:{current_user.id}:my:{from_date}:{to_date}:{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    entries = await service.get_mood_history(
        current_user,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )
    
    result = api_list_response(
        data=[MoodEntryRead.model_validate(e).model_dump() for e in entries],
        message="Lay lich su cam xuc thanh cong",
    )
    cache.set(cache_key, result, ttl=MOOD_CACHE_TTL)
    return result


@router.get("/stats")
async def get_mood_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """Get mood statistics for last N days. (Cached 2 min)"""
    cache_key = f"moods:{current_user.id}:stats:{days}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    stats_data = await service.get_stats(current_user, days)
    
    response = MoodStatsResponse(
        stats=[MoodStatsDay(**s) for s in stats_data["stats"]],
        average=stats_data["average"]
    )
    
    result = api_response(
        data=response.model_dump(),
        message="Lay thong ke cam xuc thanh cong",
    )
    cache.set(cache_key, result, ttl=MOOD_CACHE_TTL)
    return result


@router.get("/streak")
async def get_mood_streak(
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """Get consecutive days streak. (Cached 2 min)"""
    cache_key = f"moods:{current_user.id}:streak"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    streak_data = await service.get_streak(current_user)
    response = MoodStreakResponse(**streak_data)
    
    result = api_response(
        data=response.model_dump(),
        message="Lay chuoi ngay lien tuc thanh cong",
    )
    cache.set(cache_key, result, ttl=MOOD_CACHE_TTL)
    return result


@router.get("/ai-summary")
async def get_ai_mood_summary(
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
    db: AsyncSession = Depends(get_db),
):
    """AI-generated weekly mood summary. (Cached 10 min — tốn OpenAI credit)"""
    cache_key = f"moods:{current_user.id}:ai_summary"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    try:
        # Get mood data
        stats = await service.get_stats(current_user, days=7)
        streak = await service.get_streak(current_user)
        
        mood_data = stats.get("stats", [])
        average = stats.get("average", 0)
        streak_count = streak.get("count", 0)
        
        if not mood_data or average == 0:
            result = api_response(
                data={
                    "summary": "Chào bạn! Calmi chưa có đủ dữ liệu cảm xúc của bạn. Hãy check-in mỗi ngày để Calmi có thể hiểu bạn hơn nhé! 💚",
                    "emoji": "🤗",
                    "trend": "neutral",
                    "days_tracked": 0,
                },
                message="AI summary generated",
            )
            cache.set(cache_key, result, ttl=AI_SUMMARY_CACHE_TTL)
            return result
        
        # Generate AI summary
        from app.core.openai_client import quick_chat_completion
        
        mood_descriptions = {1: "rất buồn", 2: "buồn", 3: "bình thường", 4: "vui", 5: "rất vui"}
        mood_text = ", ".join([
            f"{d.get('date', '')}: {mood_descriptions.get(d.get('mood_value', 3), 'bình thường')}"
            for d in mood_data if d.get('mood_value')
        ])
        
        prompt = f"""Bạn là Calmi, trợ lý tâm lý cho học sinh. Hãy tạo một đoạn nhận xét ngắn (2-3 câu) về cảm xúc tuần qua của học sinh.

Dữ liệu:
- Cảm xúc 7 ngày: {mood_text}
- Điểm trung bình: {average:.1f}/5
- Streak check-in: {streak_count} ngày liên tục

Yêu cầu:
- Thân thiện, động viên, không phán xét
- Dùng emoji phù hợp
- Nếu mood thấp: khuyến khích nhẹ nhàng
- Nếu mood cao: chúc mừng và khuyến khích duy trì
- Viết như đang nói chuyện với học sinh"""

        ai_summary = await quick_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        
        # Determine trend
        if len(mood_data) >= 3:
            recent_avg = sum(d.get("mood_value", 0) for d in mood_data[:3] if d.get("mood_value")) / 3
            older_avg = sum(d.get("mood_value", 0) for d in mood_data[3:] if d.get("mood_value")) / max(1, len([d for d in mood_data[3:] if d.get("mood_value")]))
            if recent_avg > older_avg + 0.3:
                trend = "up"
                emoji = "📈"
            elif recent_avg < older_avg - 0.3:
                trend = "down"
                emoji = "💚"
            else:
                trend = "stable"
                emoji = "✨"
        else:
            trend = "neutral"
            emoji = "🌟"
        
        result = api_response(
            data={
                "summary": ai_summary.strip(),
                "emoji": emoji,
                "trend": trend,
                "average": round(average, 1),
                "days_tracked": len([d for d in mood_data if d.get("mood_value")]),
                "streak": streak_count,
            },
            message="AI summary generated",
        )
        cache.set(cache_key, result, ttl=AI_SUMMARY_CACHE_TTL)
        return result
        
    except Exception as e:
        print(f"AI Summary error: {e}")
        return api_response(
            data={
                "summary": "Calmi thấy bạn đang cố gắng mỗi ngày. Tiếp tục check-in để Calmi hiểu bạn hơn nhé! 💚",
                "emoji": "🤗",
                "trend": "neutral",
                "days_tracked": 0,
            },
            message="Default summary",
        )
