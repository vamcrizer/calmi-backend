"""
Service cho Notification - Xu ly thong bao nguoi dung.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate


class NotificationService:
    """Service xu ly cac nghiep vu lien quan den Notification."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)
    
    async def get_notification(self, notification_id: int) -> Notification | None:
        """Lay thong bao theo ID."""
        return await self.repo.get_by_id(notification_id)
    
    async def list_user_notifications(
        self,
        user_id: int,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Lay danh sach thong bao cua nguoi dung."""
        return await self.repo.list_by_user(user_id, is_read, skip, limit)
    
    async def count_unread(self, user_id: int) -> int:
        """Dem so thong bao chua doc."""
        return await self.repo.count_unread(user_id)
    
    async def create_notification(self, data: NotificationCreate) -> Notification:
        """Tao thong bao moi."""
        return await self.repo.create(data.model_dump())
    
    async def send_to_user(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        content: str | None = None,
    ) -> Notification:
        """
        Gui thong bao den nguoi dung.
        Shortcut method de tao thong bao nhanh.
        """
        return await self.repo.create({
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "content": content,
        })
    
    async def mark_as_read(
        self,
        notification_ids: list[int],
        user_id: int,
    ) -> int:
        """Danh dau cac thong bao da doc."""
        return await self.repo.mark_as_read(notification_ids, user_id)
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Danh dau tat ca thong bao da doc."""
        return await self.repo.mark_all_as_read(user_id)
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Xoa thong bao."""
        return await self.repo.delete(notification_id)
