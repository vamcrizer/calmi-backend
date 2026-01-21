"""
Model Notification - Quan ly thong bao trong ung dung.
Ho tro thong bao cho nguoi dung ve cac su kien trong he thong.
"""
from datetime import datetime
from sqlalchemy import BigInteger, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Notification(Base):
    """
    Bang notifications - Luu tru thong bao cho nguoi dung.
    
    Cac loai thong bao:
    - NEW_REPORT: Co bao cao moi
    - REPORT_STATUS: Cap nhat trang thai bao cao
    - DAILY_MESSAGE: Tin nhan tot lanh hang ngay
    - EMOTION_REMINDER: Nhac nho ghi nhat ky cam xuc
    
    Attributes:
        id: Khoa chinh
        user_id: Nguoi nhan thong bao
        type: Loai thong bao
        title: Tieu de
        content: Noi dung
        is_read: Da doc chua
        read_at: Thoi gian doc
        created_at: Thoi gian tao
    """
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type='{self.type}')>"
