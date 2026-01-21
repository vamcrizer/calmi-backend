"""
Models cho Auth module.
Bao gom AuthRefreshToken va PasswordResetToken.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuthRefreshToken(Base):
    """
    Bang auth_refresh_tokens - Luu tru refresh tokens.
    
    Cho phep:
    - Revoke token khi logout
    - Token rotation (tao token moi, revoke token cu)
    - Logout from all devices
    
    Attributes:
        id: Khoa chinh
        user_id: Nguoi dung so huu token
        jti: JWT ID - identifier duy nhat cua token
        user_agent: Thong tin trinh duyet/thiet bi
        ip_address: Dia chi IP khi tao token
        expires_at: Thoi gian het han
        is_revoked: Da bi revoke chua
        created_at: Thoi gian tao
        revoked_at: Thoi gian revoke (neu co)
    """
    __tablename__ = "auth_refresh_tokens"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    jti: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<AuthRefreshToken(jti='{self.jti[:8]}...', user_id={self.user_id})>"


class PasswordResetToken(Base):
    """
    Bang password_reset_tokens - Luu tru tokens reset mat khau.
    
    Quy trinh:
    1. User yeu cau forgot password
    2. He thong tao token va gui email
    3. User click link va nhap mat khau moi
    4. He thong verify token va cap nhat mat khau
    
    Attributes:
        id: Khoa chinh
        user_id: Nguoi dung yeu cau reset
        token: Token gui qua email
        expires_at: Thoi gian het han (thuong 1-24h)
        is_used: Da su dung chua
        created_at: Thoi gian tao
        used_at: Thoi gian su dung (neu co)
    """
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken(token='{self.token[:8]}...', user_id={self.user_id})>"
