"""
Repository cho Notification.
"""
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository quan ly Notification."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)
    
    async def list_by_user(
        self,
        user_id: int,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Lay danh sach thong bao cua nguoi dung.
        
        Args:
            user_id: ID nguoi dung
            is_read: Loc theo trang thai doc (None = tat ca)
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach thong bao
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        
        result = await self.session.execute(
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_unread(self, user_id: int) -> int:
        """Dem so thong bao chua doc."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
        )
        return result.scalar() or 0
    
    async def mark_as_read(self, notification_ids: list[int], user_id: int) -> int:
        """
        Danh dau cac thong bao da doc.
        
        Args:
            notification_ids: Danh sach ID thong bao
            user_id: ID nguoi dung (de bao mat)
            
        Returns:
            So thong bao da cap nhat
        """
        result = await self.session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id.in_(notification_ids),
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Danh dau tat ca thong bao da doc."""
        result = await self.session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
