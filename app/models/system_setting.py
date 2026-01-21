"""
Model SystemSetting - Quan ly cau hinh he thong.
Luu tru cac tham so cau hinh dang key-value.
"""
from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemSetting(Base, TimestampMixin):
    """
    Bang system_settings - Luu tru cau hinh he thong.
    
    Vi du:
    - daily_kind_message_time: "08:00" - Thoi gian gui tin nhan tot lanh
    - default_locale: "vi-VN" - Ngon ngu mac dinh
    - emotion_diary_reminder_enabled: "true" - Bat/tat nhac nho nhat ky
    
    Attributes:
        id: Khoa chinh
        key: Khoa cau hinh (unique)
        value: Gia tri cau hinh
        description: Mo ta cau hinh
    """
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}')>"
