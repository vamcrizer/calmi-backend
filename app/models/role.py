"""
Model Role - Quan ly vai tro nguoi dung trong he thong.
Cac vai tro: STUDENT, TEACHER, COUNSELOR, SCHOOL_ADMIN, SYSTEM_ADMIN
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base, TimestampMixin):
    """
    Bang roles - Luu tru cac vai tro nguoi dung.
    
    Attributes:
        id: Khoa chinh
        code: Ma vai tro (STUDENT, TEACHER, ...)
        name: Ten hien thi cua vai tro
        description: Mo ta chi tiet vai tro
    """
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="role",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, code='{self.code}')>"
