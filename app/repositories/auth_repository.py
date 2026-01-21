"""
Repository cho Auth - Quan ly refresh tokens va reset tokens.
"""
from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthRefreshToken, PasswordResetToken
from app.repositories.base import BaseRepository


class AuthRefreshTokenRepository(BaseRepository[AuthRefreshToken]):
    """Repository quan ly AuthRefreshToken."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(AuthRefreshToken, session)
    
    async def create_token(
        self,
        user_id: int,
        jti: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthRefreshToken:
        """
        Tao refresh token moi.
        
        Args:
            user_id: ID nguoi dung
            jti: JWT ID (unique identifier)
            expires_at: Thoi gian het han
            user_agent: Thong tin thiet bi
            ip_address: Dia chi IP
            
        Returns:
            AuthRefreshToken da tao
        """
        return await self.create({
            "user_id": user_id,
            "jti": jti,
            "expires_at": expires_at,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "is_revoked": False,
        })
    
    async def get_by_jti(self, jti: str) -> AuthRefreshToken | None:
        """Tim token theo JTI."""
        result = await self.session.execute(
            select(AuthRefreshToken).where(AuthRefreshToken.jti == jti)
        )
        return result.scalar_one_or_none()
    
    async def get_valid_token(self, jti: str) -> AuthRefreshToken | None:
        """
        Tim token hop le (chua revoke, chua het han).
        
        Args:
            jti: JWT ID
            
        Returns:
            Token neu hop le, None neu khong
        """
        result = await self.session.execute(
            select(AuthRefreshToken).where(
                and_(
                    AuthRefreshToken.jti == jti,
                    AuthRefreshToken.is_revoked == False,
                    AuthRefreshToken.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def revoke_token(self, jti: str) -> bool:
        """
        Revoke mot token.
        
        Args:
            jti: JWT ID cua token
            
        Returns:
            True neu thanh cong
        """
        result = await self.session.execute(
            update(AuthRefreshToken)
            .where(AuthRefreshToken.jti == jti)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke tat ca tokens cua user.
        Dung cho logout from all devices.
        
        Args:
            user_id: ID nguoi dung
            
        Returns:
            So tokens da revoke
        """
        result = await self.session.execute(
            update(AuthRefreshToken)
            .where(
                and_(
                    AuthRefreshToken.user_id == user_id,
                    AuthRefreshToken.is_revoked == False,
                )
            )
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    """Repository quan ly PasswordResetToken."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(PasswordResetToken, session)
    
    async def create_token(
        self,
        user_id: int,
        token: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        """Tao reset token moi."""
        return await self.create({
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "is_used": False,
        })
    
    async def get_valid_token(self, token: str) -> PasswordResetToken | None:
        """
        Tim reset token hop le.
        
        Args:
            token: Token string
            
        Returns:
            Token neu hop le, None neu khong
        """
        result = await self.session.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def mark_as_used(self, token: str) -> bool:
        """Danh dau token da su dung."""
        result = await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.token == token)
            .values(is_used=True, used_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def invalidate_user_tokens(self, user_id: int) -> int:
        """Vo hieu hoa tat ca reset tokens cua user."""
        result = await self.session.execute(
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.is_used == False,
                )
            )
            .values(is_used=True, used_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
