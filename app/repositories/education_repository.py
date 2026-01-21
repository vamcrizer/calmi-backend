"""
Repositories for Module 4 - Education.
Data access layer for educational content and student progress.
"""
from datetime import datetime, date
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.education import (
    EducationContent,
    ExerciseQuestion,
    ExerciseAttempt,
    BookletRead,
    MinigameResult,
    DailyKindMessage,
    DailyKindResponse,
)
from app.repositories.base import BaseRepository


class EducationContentRepository(BaseRepository[EducationContent]):
    """Repository for educational content."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(EducationContent, session)
    
    async def list_active(
        self,
        content_type: str | None = None,
        topic: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[EducationContent]:
        """List active content with optional filters."""
        query = select(EducationContent).where(EducationContent.is_active == True)
        
        if content_type:
            query = query.where(EducationContent.content_type == content_type)
        if topic:
            query = query.where(EducationContent.topic == topic)
        
        query = query.order_by(EducationContent.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count_active(
        self,
        content_type: str | None = None,
        topic: str | None = None,
    ) -> int:
        """Count active content."""
        query = select(func.count(EducationContent.id)).where(EducationContent.is_active == True)
        
        if content_type:
            query = query.where(EducationContent.content_type == content_type)
        if topic:
            query = query.where(EducationContent.topic == topic)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_with_questions(self, content_id: int) -> EducationContent | None:
        """Get content with questions loaded."""
        result = await self.session.execute(
            select(EducationContent)
            .options(selectinload(EducationContent.questions))
            .where(EducationContent.id == content_id)
        )
        return result.scalar_one_or_none()


class ExerciseQuestionRepository(BaseRepository[ExerciseQuestion]):
    """Repository for exercise questions."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ExerciseQuestion, session)
    
    async def list_by_content(self, content_id: int) -> list[ExerciseQuestion]:
        """Get questions for a content, ordered by index."""
        result = await self.session.execute(
            select(ExerciseQuestion)
            .where(ExerciseQuestion.content_id == content_id)
            .order_by(ExerciseQuestion.order_index)
        )
        return list(result.scalars().all())


class ExerciseAttemptRepository(BaseRepository[ExerciseAttempt]):
    """Repository for exercise attempts."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ExerciseAttempt, session)
    
    async def create_attempt(
        self,
        user_id: int,
        content_id: int,
        score: int | None = None,
        duration_seconds: int | None = None,
    ) -> ExerciseAttempt:
        """Create a new exercise attempt."""
        return await self.create({
            "user_id": user_id,
            "content_id": content_id,
            "score": score,
            "duration_seconds": duration_seconds,
        })
    
    async def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ExerciseAttempt]:
        """List attempts by user, most recent first."""
        result = await self.session.execute(
            select(ExerciseAttempt)
            .options(selectinload(ExerciseAttempt.content))
            .where(ExerciseAttempt.user_id == user_id)
            .order_by(desc(ExerciseAttempt.completed_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class BookletReadRepository(BaseRepository[BookletRead]):
    """Repository for booklet reading progress."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(BookletRead, session)
    
    async def upsert_progress(
        self,
        user_id: int,
        content_id: int,
        progress_percent: int,
    ) -> BookletRead:
        """Update or create reading progress."""
        # Check if exists
        result = await self.session.execute(
            select(BookletRead)
            .where(BookletRead.user_id == user_id)
            .where(BookletRead.content_id == content_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.progress_percent = progress_percent
            existing.read_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.create({
                "user_id": user_id,
                "content_id": content_id,
                "progress_percent": progress_percent,
            })
    
    async def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BookletRead]:
        """List reads by user."""
        result = await self.session.execute(
            select(BookletRead)
            .options(selectinload(BookletRead.content))
            .where(BookletRead.user_id == user_id)
            .order_by(desc(BookletRead.read_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class MinigameResultRepository(BaseRepository[MinigameResult]):
    """Repository for minigame results."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MinigameResult, session)
    
    async def create_result(
        self,
        user_id: int,
        content_id: int,
        score: int,
        reward_points: int,
    ) -> MinigameResult:
        """Create a minigame result."""
        return await self.create({
            "user_id": user_id,
            "content_id": content_id,
            "score": score,
            "reward_points": reward_points,
        })
    
    async def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MinigameResult]:
        """List results by user."""
        result = await self.session.execute(
            select(MinigameResult)
            .options(selectinload(MinigameResult.content))
            .where(MinigameResult.user_id == user_id)
            .order_by(desc(MinigameResult.played_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_total_points(self, user_id: int) -> int:
        """Get total reward points for user."""
        result = await self.session.execute(
            select(func.sum(MinigameResult.reward_points))
            .where(MinigameResult.user_id == user_id)
        )
        return result.scalar() or 0


class DailyKindMessageRepository(BaseRepository[DailyKindMessage]):
    """Repository for daily kind messages."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DailyKindMessage, session)
    
    async def get_by_date(self, target_date: date) -> DailyKindMessage | None:
        """Get message for a specific date."""
        result = await self.session.execute(
            select(DailyKindMessage)
            .where(DailyKindMessage.active_date == target_date)
        )
        return result.scalar_one_or_none()
    
    async def get_today(self) -> DailyKindMessage | None:
        """Get today's message."""
        return await self.get_by_date(date.today())


class DailyKindResponseRepository(BaseRepository[DailyKindResponse]):
    """Repository for daily kind responses."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DailyKindResponse, session)
    
    async def get_user_response(
        self,
        user_id: int,
        message_id: int,
    ) -> DailyKindResponse | None:
        """Get user's response to a message."""
        result = await self.session.execute(
            select(DailyKindResponse)
            .where(DailyKindResponse.user_id == user_id)
            .where(DailyKindResponse.message_id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def create_response(
        self,
        user_id: int,
        message_id: int,
        response_text: str,
    ) -> DailyKindResponse:
        """Create a response to daily message."""
        return await self.create({
            "user_id": user_id,
            "message_id": message_id,
            "response_text": response_text,
        })
