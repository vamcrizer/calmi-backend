"""
Model Class - Quan ly thong tin lop hoc.
Moi lop thuoc mot truong va co giao vien chu nhiem.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Class(Base, TimestampMixin):
    """
    Bang classes - Luu tru thong tin lop hoc.
    
    Attributes:
        id: Khoa chinh
        school_id: Truong hoc (bat buoc)
        name: Ten lop (VD: 10A1, 9B)
        grade: Khoi lop (VD: 10, 9)
        homeroom_teacher_id: Giao vien chu nhiem
    """
    __tablename__ = "classes"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    homeroom_teacher_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    school: Mapped["School"] = relationship(
        "School",
        back_populates="classes",
        lazy="selectin",
    )
    homeroom_teacher: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[homeroom_teacher_id],
        lazy="selectin",
    )
    students: Mapped[list["StudentProfile"]] = relationship(
        "StudentProfile",
        back_populates="student_class",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Class(id={self.id}, name='{self.name}')>"
