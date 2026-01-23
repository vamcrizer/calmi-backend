"""
Router for Mood Tracking - Student emotion diary.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
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
    
    If entry exists for the date, updates it.
    Student can check-in once per day.
    """
    entry = await service.create_or_update_mood(current_user, data)
    
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
    """Get mood history for current user."""
    entries = await service.get_mood_history(
        current_user,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )
    
    return api_list_response(
        data=[MoodEntryRead.model_validate(e).model_dump() for e in entries],
        message="Lay lich su cam xuc thanh cong",
    )


@router.get("/stats")
async def get_mood_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """
    Get mood statistics for last N days.
    
    Returns daily mood values and average.
    """
    stats_data = await service.get_stats(current_user, days)
    
    # Convert to response model
    response = MoodStatsResponse(
        stats=[MoodStatsDay(**s) for s in stats_data["stats"]],
        average=stats_data["average"]
    )
    
    return api_response(
        data=response.model_dump(),
        message="Lay thong ke cam xuc thanh cong",
    )


@router.get("/streak")
async def get_mood_streak(
    current_user: User = Depends(get_current_user),
    service: MoodService = Depends(get_mood_service),
):
    """
    Get consecutive days streak.
    
    Returns count and whether streak is active.
    """
    streak_data = await service.get_streak(current_user)
    
    response = MoodStreakResponse(**streak_data)
    
    return api_response(
        data=response.model_dump(),
        message="Lay chuoi ngay lien tuc thanh cong",
    )


@router.get("/debug-timezone")
async def debug_timezone():
    """
    Debug endpoint to check timezone settings.
    Shows current time in UTC, Vietnam, and server local.
    """
    vn_tz = timezone(timedelta(hours=7))
    
    now_utc = datetime.now(timezone.utc)
    now_vn = datetime.now(vn_tz)
    now_local = datetime.now()
    
    return {
        "utc": {
            "datetime": now_utc.isoformat(),
            "date": now_utc.date().isoformat(),
            "weekday": now_utc.strftime("%A"),
        },
        "vietnam_gmt7": {
            "datetime": now_vn.isoformat(),
            "date": now_vn.date().isoformat(),
            "weekday": now_vn.strftime("%A"),
        },
        "server_local": {
            "datetime": now_local.isoformat(),
            "date": now_local.date().isoformat(),
            "weekday": now_local.strftime("%A"),
        },
        "expected_today_vn": now_vn.date().isoformat(),
    }
