"""
Model SupportOrganization - Quan ly to chuc ho tro.
Cac to chuc nhu: Hotline 111, NGO, Trung tam bao ve tre em, Cong an.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SupportOrganization(Base, TimestampMixin):
    """
    Bang support_organizations - Luu tru thong tin to chuc ho tro.
    
    Attributes:
        id: Khoa chinh
        name: Ten to chuc
        type: Loai to chuc (HOTLINE, NGO, GOV, CHILD_PROTECTION)
        description: Mo ta
        province: Tinh/Thanh pho
        district: Quan/Huyen
        address: Dia chi chi tiet
        email: Email lien he
        phone: So dien thoai
        website: Dia chi website
        is_active: Trang thai hoat dong
    """
    __tablename__ = "support_organizations"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    emergency_contacts: Mapped[list["EmergencyContact"]] = relationship(
        "EmergencyContact",
        back_populates="support_organization",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<SupportOrganization(id={self.id}, name='{self.name}')>"
