"""
Base model va mixins cho SQLAlchemy ORM.
Dinh nghia cac class cha de cac model khac ke thua.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class cho tat ca cac model SQLAlchemy.
    Cac model khac se ke thua tu class nay.
    """
    pass


class TimestampMixin:
    """
    Mixin cung cap cac truong thoi gian chung.
    Su dung cho cac bang can theo doi thoi gian tao va cap nhat.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin ho tro xoa mem (soft delete).
    Thay vi xoa ban ghi, chi danh dau thoi gian xoa.
    """
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
