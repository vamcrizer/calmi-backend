"""
Model User va cac Profile lien quan.
User la thuc the chinh dai dien cho nguoi dung trong he thong.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.class_ import Class
    from app.models.file import File
    from app.models.notification import Notification


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    Bang users - Luu tru thong tin nguoi dung.
    
    Attributes:
        id: Khoa chinh
        school_id: Truong hoc (co the null voi System Admin)
        role_id: Vai tro cua nguoi dung
        full_name: Ho va ten day du
        email: Dia chi email
        phone: So dien thoai
        username: Ten dang nhap
        password_hash: Mat khau da ma hoa
        status: Trang thai tai khoan (ACTIVE, INACTIVE, SUSPENDED)
        is_email_verified: Da xac thuc email chua
        is_phone_verified: Da xac thuc so dien thoai chua
        last_login_at: Thoi gian dang nhap gan nhat
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    school_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    school: Mapped["School | None"] = relationship(
        "School",
        back_populates="users",
        lazy="selectin",
    )
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users",
        lazy="selectin",
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    teacher_profile: Mapped["TeacherProfile | None"] = relationship(
        "TeacherProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="owner",
        lazy="selectin",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class StudentProfile(Base, TimestampMixin):
    """
    Bang student_profiles - Thong tin bo sung cho hoc sinh.
    Quan he 1-1 voi User co role STUDENT.
    
    Attributes:
        user_id: Khoa ngoai toi bang users (unique)
        date_of_birth: Ngay sinh
        gender: Gioi tinh
        class_id: Lop hoc
        guardian_name: Ten phu huynh
        guardian_phone: So dien thoai phu huynh
    """
    __tablename__ = "student_profiles"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    class_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("classes.id", ondelete="SET NULL"),
        nullable=True,
    )
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_profile",
        lazy="selectin",
    )
    student_class: Mapped["Class | None"] = relationship(
        "Class",
        back_populates="students",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<StudentProfile(user_id={self.user_id})>"


class TeacherProfile(Base, TimestampMixin):
    """
    Bang teacher_profiles - Thong tin bo sung cho giao vien/tu van vien.
    Quan he 1-1 voi User co role TEACHER hoac COUNSELOR.
    
    Attributes:
        user_id: Khoa ngoai toi bang users (unique)
        position: Chuc vu (Giao vien chu nhiem, Tu van vien)
        specialization: Chuyen mon (Tam ly, Toan, Van)
    """
    __tablename__ = "teacher_profiles"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="teacher_profile",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<TeacherProfile(user_id={self.user_id})>"
