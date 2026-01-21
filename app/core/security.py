"""
Security utilities cho Auth module.
Bao gom password hashing va JWT token handling.
"""
from datetime import datetime, timedelta
from typing import Any
import uuid

from jose import jwt, JWTError
import bcrypt

from app.core.config import get_settings

settings = get_settings()

# ============================================
# PASSWORD HASHING
# ============================================
# Su dung bcrypt - algorithm bao mat tieu chuan


def hash_password(password: str) -> str:
    """
    Hash mat khau su dung bcrypt.
    
    Args:
        password: Mat khau dang plain text
        
    Returns:
        Mat khau da hash
    """
    # Encode password to bytes and hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Kiem tra mat khau co khop voi hash khong.
    
    Args:
        plain_password: Mat khau nguoi dung nhap
        hashed_password: Hash luu trong database
        
    Returns:
        True neu khop, False neu khong
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# ============================================
# JWT TOKEN HANDLING
# ============================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Tao JWT access token.
    
    Args:
        data: Payload data (sub, role_code, school_id, ...)
        expires_delta: Thoi gian het han (mac dinh tu config)
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    })
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token() -> tuple[str, str, datetime]:
    """
    Tao refresh token (UUID-based).
    
    Returns:
        Tuple (token_string, jti, expires_at)
        - token_string: Token gui cho client
        - jti: JWT ID luu trong DB
        - expires_at: Thoi gian het han
    """
    jti = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Token gui cho client la JWT chua jti
    token_data = {
        "jti": jti,
        "type": "refresh",
        "exp": expires_at,
        "iat": datetime.utcnow(),
    }
    
    token_string = jwt.encode(
        token_data,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return token_string, jti, expires_at


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode va validate access token.
    
    Args:
        token: JWT access token
        
    Returns:
        Payload dict neu hop le, None neu khong
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Kiem tra token type
        if payload.get("type") != "access":
            return None
        
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """
    Decode va validate refresh token.
    
    Args:
        token: JWT refresh token
        
    Returns:
        Payload dict neu hop le, None neu khong
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Kiem tra token type
        if payload.get("type") != "refresh":
            return None
        
        return payload
    except JWTError:
        return None


def generate_reset_token() -> str:
    """
    Tao token cho password reset.
    
    Returns:
        Random token string
    """
    return str(uuid.uuid4())
