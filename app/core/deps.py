"""
Dependencies cho FastAPI - Authentication va Authorization.
Cung cap cac dependencies de bao ve endpoints.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency de lay user hien tai tu access token.
    
    Quy trinh:
    1. Doc Bearer token tu header Authorization
    2. Decode JWT
    3. Load user tu database
    4. Kiem tra user active
    
    Raises:
        HTTPException 401: Neu token khong hop le hoac user khong ton tai
        
    Returns:
        User instance
    """
    # Kiem tra co token khong
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Khong tim thay token xac thuc",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token khong hop le hoac da het han",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Lay user ID tu payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token khong hop le",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Load user tu database
    user_repo = UserRepository(db)
    user = await user_repo.get_active_user_by_id(int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nguoi dung khong ton tai hoac da bi vo hieu hoa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency de lay user active.
    Tuong tu get_current_user nhung co the them kiem tra bo sung.
    
    Args:
        current_user: User tu get_current_user
        
    Returns:
        User instance neu active
    """
    # Kiem tra them trang thai (du get_current_user da kiem tra)
    if current_user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tai khoan da bi vo hieu hoa",
        )
    
    return current_user


def require_roles(*allowed_roles: str):
    """
    Factory function tao dependency kiem tra role.
    
    Su dung:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_roles("SYSTEM_ADMIN", "SCHOOL_ADMIN"))
        ):
            ...
    
    Args:
        allowed_roles: Danh sach role codes duoc phep
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Kiem tra user co role phu hop khong."""
        # Lay role code tu user
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Khong the xac dinh vai tro cua ban",
            )
        
        user_role = current_user.role.code
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Ban khong co quyen truy cap. Yeu cau: {', '.join(allowed_roles)}",
            )
        
        return current_user
    
    return role_checker


# Type hints cho convenience
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
