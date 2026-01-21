"""
Schemas cho Notification - Thong bao trong ung dung.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    """Schema co so cho Notification."""
    type: str = Field(..., max_length=50, description="Loai thong bao")
    title: str | None = Field(None, max_length=255, description="Tieu de")
    content: str | None = Field(None, description="Noi dung")


class NotificationCreate(NotificationBase):
    """Schema de tao moi Notification."""
    user_id: int = Field(..., description="ID nguoi nhan")


class NotificationRead(NotificationBase):
    """Schema tra ve khi doc Notification."""
    id: int
    user_id: int
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Yeu cau danh dau da doc."""
    notification_ids: list[int] = Field(..., description="Danh sach ID thong bao")
