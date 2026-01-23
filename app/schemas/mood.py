"""
Schemas for Mood Tracking (Emotion Diary).
Pydantic DTOs for mood entries.
"""
from datetime import date, datetime

from pydantic import BaseModel, Field


class MoodEntryCreate(BaseModel):
    """Request body to create/update mood entry."""
    mood_value: int = Field(..., ge=20, le=100, description="Mood value (20-100)")
    note: str | None = Field(None, max_length=500, description="Optional note")
    mood_date: date | None = Field(None, description="Date of mood (defaults to today)")


class MoodEntryRead(BaseModel):
    """Mood entry for display."""
    id: int
    mood_value: int
    note: str | None = None
    mood_date: date
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MoodStatsDay(BaseModel):
    """Mood stats for a single day."""
    date: date
    mood_value: int | None = None  # None if no entry for that day
    has_entry: bool
    day_name: str  # e.g., "Mon", "Tue"


class MoodStatsResponse(BaseModel):
    """Stats response with last 7 days."""
    stats: list[MoodStatsDay]
    average: float  # Average mood value (excluding missing days)
    
    
class MoodStreakResponse(BaseModel):
    """Streak information."""
    count: int  # Number of consecutive days
    active: bool  # Is streak active (includes today or yesterday)
    checked_in_today: bool = False  # Has user checked in today
