"""
Services for Module 4 - Education.
Business logic for educational content and student learning.
"""
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.education import EducationContent, ExerciseQuestion
from app.repositories.education_repository import (
    EducationContentRepository,
    ExerciseQuestionRepository,
    ExerciseAttemptRepository,
    BookletReadRepository,
    MinigameResultRepository,
    DailyKindMessageRepository,
    DailyKindResponseRepository,
)
from app.schemas.education import (
    ContentListItem,
    ContentDetail,
    ContentListResponse,
    QuestionItem,
    ExerciseSubmitResponse,
    BookletProgressResponse,
    MinigameResultResponse,
    DailyKindMessageResponse,
    DailyKindRespondResponse,
    LearningHistoryResponse,
    HistoryExerciseItem,
    HistoryBookletItem,
    HistoryMinigameItem,
)


class EducationServiceError(Exception):
    """Base exception for education service."""
    pass


class ContentNotFoundError(EducationServiceError):
    """Content not found."""
    pass


class ContentNotActiveError(EducationServiceError):
    """Content is not active."""
    pass


class InvalidContentTypeError(EducationServiceError):
    """Invalid content type for operation."""
    pass


class AlreadyRespondedError(EducationServiceError):
    """User has already responded today."""
    pass


class NoMessageTodayError(EducationServiceError):
    """No daily message for today."""
    pass


class EducationService:
    """
    Main service for educational content.
    """
    
    def __init__(self, session: AsyncSession):
        self.db = session
        self.content_repo = EducationContentRepository(session)
        self.question_repo = ExerciseQuestionRepository(session)
        self.attempt_repo = ExerciseAttemptRepository(session)
        self.booklet_repo = BookletReadRepository(session)
        self.minigame_repo = MinigameResultRepository(session)
        self.message_repo = DailyKindMessageRepository(session)
        self.response_repo = DailyKindResponseRepository(session)
    
    # ==========================================
    # CONTENT LISTING
    # ==========================================
    
    async def list_contents(
        self,
        content_type: str | None = None,
        topic: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ContentListResponse:
        """List active educational contents with filters."""
        contents = await self.content_repo.list_active(
            content_type=content_type,
            topic=topic,
            limit=limit,
            offset=offset,
        )
        total = await self.content_repo.count_active(
            content_type=content_type,
            topic=topic,
        )
        
        items = [
            ContentListItem(
                id=c.id,
                content_type=c.content_type,
                title=c.title,
                description=c.description,
                topic=c.topic,
                media_url=c.media_url,
            )
            for c in contents
        ]
        
        return ContentListResponse(contents=items, total=total)
    
    async def get_content_detail(self, content_id: int) -> ContentDetail:
        """Get content detail with questions for exercises."""
        content = await self.content_repo.get_with_questions(content_id)
        
        if not content:
            raise ContentNotFoundError(f"Content {content_id} not found")
        
        if not content.is_active:
            raise ContentNotActiveError(f"Content {content_id} is not active")
        
        questions = []
        if content.content_type == "EXERCISE" and content.questions:
            questions = [
                QuestionItem(
                    id=q.id,
                    question_text=q.question_text,
                    options=q.options if isinstance(q.options, list) else [],
                    order_index=q.order_index,
                )
                for q in sorted(content.questions, key=lambda x: x.order_index)
            ]
        
        return ContentDetail(
            id=content.id,
            content_type=content.content_type,
            title=content.title,
            description=content.description,
            topic=content.topic,
            media_url=content.media_url,
            questions=questions,
        )
    
    # ==========================================
    # EXERCISE SUBMISSION
    # ==========================================
    
    async def submit_exercise(
        self,
        user: User,
        content_id: int,
        answers: list[str],
        duration_seconds: int,
    ) -> ExerciseSubmitResponse:
        """Submit exercise result and calculate score."""
        content = await self.content_repo.get_with_questions(content_id)
        
        if not content:
            raise ContentNotFoundError(f"Content {content_id} not found")
        
        if content.content_type != "EXERCISE":
            raise InvalidContentTypeError("This content is not an exercise")
        
        # Calculate score for quiz
        score = None
        correct = 0
        total = len(content.questions) if content.questions else 0
        
        if content.questions and answers:
            for i, q in enumerate(sorted(content.questions, key=lambda x: x.order_index)):
                if i < len(answers) and answers[i] == q.correct_answer:
                    correct += 1
            score = int((correct / total) * 100) if total > 0 else 0
        
        # Create attempt
        attempt = await self.attempt_repo.create_attempt(
            user_id=user.id,
            content_id=content_id,
            score=score,
            duration_seconds=duration_seconds,
        )
        
        return ExerciseSubmitResponse(
            attempt_id=attempt.id,
            score=score,
            total_questions=total,
            correct_answers=correct,
            duration_seconds=duration_seconds,
            message="Chúc mừng bạn đã hoàn thành bài tập!" if score and score >= 70 else "Cảm ơn bạn đã hoàn thành bài tập!",
        )
    
    # ==========================================
    # BOOKLET PROGRESS
    # ==========================================
    
    async def update_booklet_progress(
        self,
        user: User,
        content_id: int,
        progress_percent: int,
    ) -> BookletProgressResponse:
        """Update reading progress for a booklet."""
        content = await self.content_repo.get_by_id(content_id)
        
        if not content:
            raise ContentNotFoundError(f"Content {content_id} not found")
        
        if content.content_type != "BOOKLET":
            raise InvalidContentTypeError("This content is not a booklet")
        
        read = await self.booklet_repo.upsert_progress(
            user_id=user.id,
            content_id=content_id,
            progress_percent=progress_percent,
        )
        
        return BookletProgressResponse(
            content_id=content_id,
            progress_percent=read.progress_percent,
            read_at=read.read_at,
        )
    
    # ==========================================
    # MINIGAME RESULTS
    # ==========================================
    
    async def submit_minigame_result(
        self,
        user: User,
        content_id: int,
        score: int,
    ) -> MinigameResultResponse:
        """Submit minigame play result."""
        content = await self.content_repo.get_by_id(content_id)
        
        if not content:
            raise ContentNotFoundError(f"Content {content_id} not found")
        
        if content.content_type != "MINIGAME":
            raise InvalidContentTypeError("This content is not a minigame")
        
        # Calculate reward points (simple formula)
        reward_points = min(score // 10, 10)  # 1 point per 10 score, max 10
        
        result = await self.minigame_repo.create_result(
            user_id=user.id,
            content_id=content_id,
            score=score,
            reward_points=reward_points,
        )
        
        return MinigameResultResponse(
            result_id=result.id,
            score=score,
            reward_points=reward_points,
            message=f"Tuyệt vời! Bạn nhận được {reward_points} điểm thưởng!",
        )
    
    # ==========================================
    # DAILY KIND MESSAGE
    # ==========================================
    
    async def get_daily_message(self, user: User) -> DailyKindMessageResponse:
        """Get today's daily kind message."""
        message = await self.message_repo.get_today()
        
        if not message:
            raise NoMessageTodayError("No message available for today")
        
        # Check if user has responded
        response = await self.response_repo.get_user_response(user.id, message.id)
        
        return DailyKindMessageResponse(
            id=message.id,
            message_text=message.message_text,
            active_date=message.active_date,
            has_responded=response is not None,
            my_response=response.response_text if response else None,
        )
    
    async def respond_to_daily_message(
        self,
        user: User,
        response_text: str,
    ) -> DailyKindRespondResponse:
        """Submit response to today's daily kind message."""
        message = await self.message_repo.get_today()
        
        if not message:
            raise NoMessageTodayError("No message available for today")
        
        # Check if already responded
        existing = await self.response_repo.get_user_response(user.id, message.id)
        if existing:
            raise AlreadyRespondedError("You have already responded to today's message")
        
        response = await self.response_repo.create_response(
            user_id=user.id,
            message_id=message.id,
            response_text=response_text,
        )
        
        return DailyKindRespondResponse(
            response_id=response.id,
            message="Cảm ơn bạn đã chia sẻ! Lòng tốt của bạn rất đáng quý. 💚",
        )
    
    # ==========================================
    # LEARNING HISTORY
    # ==========================================
    
    async def get_learning_history(self, user: User) -> LearningHistoryResponse:
        """Get student's complete learning history."""
        # Get exercises
        attempts = await self.attempt_repo.list_by_user(user.id, limit=50)
        exercises = [
            HistoryExerciseItem(
                id=a.id,
                content_id=a.content_id,
                content_title=a.content.title if a.content else "Unknown",
                content_type=a.content.content_type if a.content else "EXERCISE",
                topic=a.content.topic if a.content else "unknown",
                score=a.score,
                duration_seconds=a.duration_seconds,
                completed_at=a.completed_at,
            )
            for a in attempts
        ]
        
        # Get booklets
        reads = await self.booklet_repo.list_by_user(user.id, limit=50)
        booklets = [
            HistoryBookletItem(
                id=r.id,
                content_id=r.content_id,
                content_title=r.content.title if r.content else "Unknown",
                topic=r.content.topic if r.content else "unknown",
                progress_percent=r.progress_percent,
                read_at=r.read_at,
            )
            for r in reads
        ]
        
        # Get minigames
        results = await self.minigame_repo.list_by_user(user.id, limit=50)
        minigames = [
            HistoryMinigameItem(
                id=r.id,
                content_id=r.content_id,
                content_title=r.content.title if r.content else "Unknown",
                score=r.score,
                reward_points=r.reward_points,
                played_at=r.played_at,
            )
            for r in results
        ]
        
        # Get total points
        total_points = await self.minigame_repo.get_total_points(user.id)
        
        return LearningHistoryResponse(
            exercises=exercises,
            booklets=booklets,
            minigames=minigames,
            total_points=total_points,
        )
