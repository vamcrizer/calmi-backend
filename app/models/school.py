"""
Model School - Quan ly thong tin truong hoc.
Moi truong co the co nhieu lop va nhieu nguoi dung.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class School(Base, TimestampMixin):
    """
    Bang schools - Luu tru thong tin truong hoc.
    
    Attributes:
        id: Khoa chinh
        name: Ten truong
        code: Ma truong (VD: THPT_HOABINH)
        address: Dia chi
        province: Tinh/Thanh pho
        district: Quan/Huyen
        phone: So dien thoai
        email: Email lien he
        status: Trang thai (ACTIVE, INACTIVE)
    """
    __tablename__ = "schools"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="school",
        lazy="selectin",
    )
    classes: Mapped[list["Class"]] = relationship(
        "Class",
        back_populates="school",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    emergency_contacts: Mapped[list["EmergencyContact"]] = relationship(
        "EmergencyContact",
        back_populates="school",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<School(id={self.id}, name='{self.name}')>"
