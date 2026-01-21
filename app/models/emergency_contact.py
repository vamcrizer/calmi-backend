"""
Model EmergencyContact - Quan ly lien he khan cap cho SOS.
Ho tro tim lien he theo vi tri dia ly va loai lien he.
"""
from __future__ import annotations

from decimal import Decimal
from sqlalchemy import BigInteger, String, SmallInteger, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EmergencyContact(Base, TimestampMixin):
    """
    Bang emergency_contacts - Luu tru lien he khan cap cho tinh nang SOS.
    
    Attributes:
        id: Khoa chinh
        support_org_id: To chuc ho tro (neu co)
        school_id: Truong hoc (cho hotline truong)
        contact_type: Loai lien he (NATIONAL_111, LOCAL_CHILD_HOTLINE, POLICE, SCHOOL_HOTLINE)
        name: Ten hien thi
        phone: So dien thoai
        province: Tinh/Thanh pho
        district: Quan/Huyen
        latitude: Vi do (cho tim kiem theo vi tri)
        longitude: Kinh do
        priority: Do uu tien (1 = cao nhat)
        is_active: Trang thai hoat dong
    """
    __tablename__ = "emergency_contacts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    support_org_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("support_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    school_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
    )
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    support_organization: Mapped["SupportOrganization | None"] = relationship(
        "SupportOrganization",
        back_populates="emergency_contacts",
        lazy="selectin",
    )
    school: Mapped["School | None"] = relationship(
        "School",
        back_populates="emergency_contacts",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<EmergencyContact(id={self.id}, type='{self.contact_type}')>"
