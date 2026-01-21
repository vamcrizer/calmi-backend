"""
Mood Service - Business logic for mood tracking.
Handles mood entry creation, stats, and streak calculation.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mood import MoodEntry
from app.models.user import User
from app.repositories.mood_repository import MoodRepository
from app.schemas.mood import MoodEntryCreate


class MoodService:
    """Service for mood tracking operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mood_repo = MoodRepository(session)
    
    async def create_or_update_mood(
        self,
        user: User,
        data: MoodEntryCreate
    ) -> MoodEntry:
        """
        Create or update mood entry for user.
        
        If entry exists for the date, updates it.
        Otherwise creates new entry.
        """
        mood_date = data.mood_date or date.today()
        
        return await self.mood_repo.create_or_update(
            user_id=user.id,
            mood_value=data.mood_value,
            note=data.note,
            mood_date=mood_date
        )
    
    async def get_mood_history(
        self,
        user: User,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 30
    ) -> list[MoodEntry]:
        """Get mood history for user."""
        return await self.mood_repo.list_by_user(
            user.id,
            from_date=from_date,
            to_date=to_date,
            limit=limit
        )
    
    async def get_stats(self, user: User, days: int = 7) -> dict:
        """
        Get mood stats for last N days.
        
        Returns daily stats with mood values and average.
        """
        # Get entries for last N days
        entries_dict = {}
        entries = await self.mood_repo.get_last_n_days(user.id, days)
        
        for entry in entries:
            entries_dict[entry.mood_date] = entry
        
        # Build stats for each day
        stats = []
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        total_mood = 0
        count_with_entry = 0
        
        for i in range(days - 1, -1, -1):
            check_date = date.today() - timedelta(days=i)
            entry = entries_dict.get(check_date)
            
            if entry:
                mood_value = entry.mood_value
                has_entry = True
                total_mood += mood_value
                count_with_entry += 1
            else:
                mood_value = None
                has_entry = False
            
            day_name = day_names[check_date.weekday()]
            
            stats.append({
                "date": check_date,
                "mood_value": mood_value,
                "has_entry": has_entry,
                "day_name": day_name
            })
        
        average = total_mood / count_with_entry if count_with_entry > 0 else 0
        
        return {
            "stats": stats,
            "average": round(average, 1)
        }
    
    async def get_streak(self, user: User) -> dict:
        """Get consecutive days streak for user."""
        return await self.mood_repo.get_streak(user.id)
