"""
Auth Service - Xu ly logic nghiep vu xac thuc.
Bao gom login, refresh, logout, change password, register.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_reset_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.auth_repository import (
    AuthRefreshTokenRepository,
    PasswordResetTokenRepository,
)
from app.schemas.auth import TokenResponse, UserInfo, RegisterRequest

settings = get_settings()


class AuthServiceError(Exception):
    """Base exception cho AuthService."""
    pass


class InvalidCredentialsError(AuthServiceError):
    """Sai thong tin dang nhap."""
    pass


class UserNotActiveError(AuthServiceError):
    """User khong active."""
    pass


class InvalidTokenError(AuthServiceError):
    """Token khong hop le."""
    pass


class UserExistsError(AuthServiceError):
    """User da ton tai."""
    pass


class AuthService:
    """
    Service xu ly cac nghiep vu xac thuc.
    
    Cac chuc nang:
    - Register: Dang ky student moi
    - Login: Xac thuc va tao tokens
    - Refresh: Lam moi access token
    - Logout: Revoke refresh token
    - Change password: Doi mat khau
    - Forgot/Reset password: Khoi phuc mat khau
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.token_repo = AuthRefreshTokenRepository(session)
        self.reset_repo = PasswordResetTokenRepository(session)
    
    async def register_student(
        self,
        data: RegisterRequest,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Dang ky student moi.
        
        Args:
            data: Thong tin dang ky
            user_agent: Thong tin thiet bi
            ip_address: Dia chi IP
            
        Returns:
            TokenResponse (tu dong dang nhap sau dang ky)
            
        Raises:
            UserExistsError: Username hoac email da ton tai
        """
        # Kiem tra username da ton tai
        existing = await self.user_repo.get_by_username(data.username)
        if existing:
            raise UserExistsError("Ten dang nhap da duoc su dung")
        
        # Kiem tra email da ton tai
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise UserExistsError("Email da duoc su dung")
        
        # Lay role STUDENT
        student_role = await self.role_repo.get_by_code("STUDENT")
        if not student_role:
            raise AuthServiceError("Khong tim thay role STUDENT")
        
        # Hash password
        password_hash = hash_password(data.password)
        
        # Tao user
        user = await self.user_repo.create({
            "username": data.username,
            "email": data.email,
            "password_hash": password_hash,
            "full_name": data.full_name,
            "phone": data.phone,
            "school_id": data.school_id,
            "role_id": student_role.id,
            "status": "ACTIVE",
        })
        
        # Tu dong dang nhap
        return await self.login(
            identifier=data.username,
            password=data.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    
    
    async def login(
        self,
        identifier: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Dang nhap nguoi dung.
        
        Args:
            identifier: Username hoac email
            password: Mat khau
            user_agent: Thong tin thiet bi
            ip_address: Dia chi IP
            
        Returns:
            TokenResponse voi access_token va refresh_token
            
        Raises:
            InvalidCredentialsError: Sai thong tin dang nhap
            UserNotActiveError: User khong active
        """
        # Tim user theo username hoac email
        user = await self.user_repo.get_by_username_or_email(identifier)
        
        if not user:
            raise InvalidCredentialsError("Sai ten dang nhap hoac mat khau")
        
        # Kiem tra user active
        if user.status != "ACTIVE":
            raise UserNotActiveError("Tai khoan da bi vo hieu hoa")
        
        if user.deleted_at is not None:
            raise InvalidCredentialsError("Sai ten dang nhap hoac mat khau")
        
        # Kiem tra mat khau
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Sai ten dang nhap hoac mat khau")
        
        # Cap nhat last_login_at
        await self.user_repo.update_last_login(user.id)
        
        # Tao access token
        role_code = user.role.code if user.role else "UNKNOWN"
        access_token = create_access_token({
            "sub": str(user.id),
            "role_code": role_code,
            "school_id": user.school_id,
        })
        
        # Tao refresh token
        refresh_token_str, jti, expires_at = create_refresh_token()
        
        # Luu refresh token vao DB
        await self.token_repo.create_token(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        # Tao response
        user_info = UserInfo(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            username=user.username,
            role=role_code,
            school_id=user.school_id,
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )
    
    async def refresh_token(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Lam moi access token bang refresh token.
        Thuc hien token rotation (revoke token cu, tao token moi).
        
        Args:
            refresh_token: Refresh token hien tai
            user_agent: Thong tin thiet bi
            ip_address: Dia chi IP
            
        Returns:
            TokenResponse moi
            
        Raises:
            InvalidTokenError: Token khong hop le
        """
        # Decode refresh token
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise InvalidTokenError("Refresh token khong hop le")
        
        jti = payload.get("jti")
        if not jti:
            raise InvalidTokenError("Refresh token khong hop le")
        
        # Tim token trong DB
        token_record = await self.token_repo.get_valid_token(jti)
        if not token_record:
            raise InvalidTokenError("Refresh token da het han hoac bi revoke")
        
        # Lay user
        user = await self.user_repo.get_active_user_by_id(token_record.user_id)
        if not user:
            raise InvalidTokenError("Nguoi dung khong ton tai")
        
        # Revoke token cu (token rotation)
        await self.token_repo.revoke_token(jti)
        
        # Tao access token moi
        role_code = user.role.code if user.role else "UNKNOWN"
        new_access_token = create_access_token({
            "sub": str(user.id),
            "role_code": role_code,
            "school_id": user.school_id,
        })
        
        # Tao refresh token moi
        new_refresh_token_str, new_jti, new_expires_at = create_refresh_token()
        
        await self.token_repo.create_token(
            user_id=user.id,
            jti=new_jti,
            expires_at=new_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        user_info = UserInfo(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            username=user.username,
            role=role_code,
            school_id=user.school_id,
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )
    
    async def logout(self, refresh_token: str, logout_all: bool = False) -> bool:
        """
        Dang xuat nguoi dung.
        
        Args:
            refresh_token: Refresh token can revoke
            logout_all: Revoke tat ca tokens (dang xuat moi thiet bi)
            
        Returns:
            True neu thanh cong
        """
        # Decode token
        payload = decode_refresh_token(refresh_token)
        if not payload:
            return False
        
        jti = payload.get("jti")
        if not jti:
            return False
        
        # Tim token
        token_record = await self.token_repo.get_by_jti(jti)
        if not token_record:
            return False
        
        if logout_all:
            # Revoke tat ca tokens cua user
            await self.token_repo.revoke_all_user_tokens(token_record.user_id)
        else:
            # Chi revoke token hien tai
            await self.token_repo.revoke_token(jti)
        
        return True
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        logout_other_devices: bool = True,
    ) -> bool:
        """
        Doi mat khau nguoi dung.
        
        Args:
            user: User hien tai (tu dependency)
            current_password: Mat khau hien tai
            new_password: Mat khau moi
            logout_other_devices: Revoke cac tokens khac
            
        Returns:
            True neu thanh cong
            
        Raises:
            InvalidCredentialsError: Sai mat khau hien tai
        """
        # Kiem tra mat khau hien tai
        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Mat khau hien tai khong dung")
        
        # Hash va cap nhat mat khau moi
        new_hash = hash_password(new_password)
        await self.user_repo.update_password_hash(user.id, new_hash)
        
        # Revoke cac tokens khac neu can
        if logout_other_devices:
            await self.token_repo.revoke_all_user_tokens(user.id)
        
        return True
    
    async def forgot_password(self, email: str) -> str | None:
        """
        Tao reset token cho forgot password.
        
        Args:
            email: Email nguoi dung
            
        Returns:
            Reset token neu user ton tai, None neu khong
            
        Note:
            Khong raise exception neu email khong ton tai (bao mat)
        """
        user = await self.user_repo.get_by_email(email)
        if not user or user.status != "ACTIVE":
            return None
        
        # Vo hieu hoa cac tokens cu
        await self.reset_repo.invalidate_user_tokens(user.id)
        
        # Tao token moi
        token = generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
        
        await self.reset_repo.create_token(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset mat khau bang token.
        
        Args:
            token: Reset token
            new_password: Mat khau moi
            
        Returns:
            True neu thanh cong
            
        Raises:
            InvalidTokenError: Token khong hop le
        """
        # Tim token hop le
        token_record = await self.reset_repo.get_valid_token(token)
        if not token_record:
            raise InvalidTokenError("Token khong hop le hoac da het han")
        
        # Cap nhat mat khau
        new_hash = hash_password(new_password)
        await self.user_repo.update_password_hash(token_record.user_id, new_hash)
        
        # Danh dau token da su dung
        await self.reset_repo.mark_as_used(token)
        
        # Revoke tat ca refresh tokens
        await self.token_repo.revoke_all_user_tokens(token_record.user_id)
        
        return True
