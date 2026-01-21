"""
Repository for Mood operations.
Handles database queries for mood entries.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mood import MoodEntry
from app.repositories.base import BaseRepository


class MoodRepository(BaseRepository[MoodEntry]):
    """Repository for mood entry operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MoodEntry, session)
    
    async def get_by_user_and_date(self, user_id: int, mood_date: date) -> MoodEntry | None:
        """Get mood entry for specific user and date."""
        stmt = select(MoodEntry).where(
            and_(
                MoodEntry.user_id == user_id,
                MoodEntry.mood_date == mood_date
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_or_update(
        self,
        user_id: int,
        mood_value: int,
        note: str | None,
        mood_date: date
    ) -> MoodEntry:
        """Create new mood entry or update existing one for the date."""
        existing = await self.get_by_user_and_date(user_id, mood_date)
        
        if existing:
            # Update existing
            existing.mood_value = mood_value
            existing.note = note
            existing.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            entry = MoodEntry(
                user_id=user_id,
                mood_value=mood_value,
                note=note,
                mood_date=mood_date,
            )
            self.session.add(entry)
            await self.session.commit()
            await self.session.refresh(entry)
            return entry
    
    async def list_by_user(
        self,
        user_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 30
    ) -> list[MoodEntry]:
        """List mood entries for user, optionally filtered by date range."""
        stmt = select(MoodEntry).where(MoodEntry.user_id == user_id)
        
        if from_date:
            stmt = stmt.where(MoodEntry.mood_date >= from_date)
        if to_date:
            stmt = stmt.where(MoodEntry.mood_date <= to_date)
        
        stmt = stmt.order_by(desc(MoodEntry.mood_date)).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_last_n_days(self, user_id: int, days: int = 7) -> list[MoodEntry]:
        """Get mood entries for last N days."""
        from_date = date.today() - timedelta(days=days - 1)
        return await self.list_by_user(user_id, from_date=from_date, limit=days)
    
    async def get_streak(self, user_id: int) -> dict:
        """Calculate consecutive days streak."""
        # Get recent entries sorted by date descending
        entries = await self.list_by_user(user_id, limit=100)
        
        if not entries:
            return {"count": 0, "active": False}
        
        # Get unique dates
        unique_dates = sorted(list(set(e.mood_date for e in entries)), reverse=True)
        
        if not unique_dates:
            return {"count": 0, "active": False}
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        latest_date = unique_dates[0]
        
        # Check if streak is active (latest entry is today or yesterday)
        if latest_date != today and latest_date != yesterday:
            return {"count": 0, "active": False}
        
        # Count consecutive days
        streak_count = 0
        check_date = latest_date
        
        for entry_date in unique_dates:
            if entry_date == check_date:
                streak_count += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        
        return {"count": streak_count, "active": True}
