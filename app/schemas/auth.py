"""
Schemas cho Auth module.
Bao gom cac Pydantic models cho login, token, change password.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ============================================
# REGISTER SCHEMAS
# ============================================

class RegisterRequest(BaseModel):
    """Request body cho dang ky student."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Ten dang nhap",
    )
    email: EmailStr = Field(..., description="Email")
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Mat khau (toi thieu 6 ky tu)",
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Ho va ten",
    )
    phone: str | None = Field(None, max_length=20, description="So dien thoai")
    school_id: int | None = Field(None, description="ID truong hoc")


# ============================================
# LOGIN SCHEMAS
# ============================================

class LoginRequest(BaseModel):
    """Request body cho dang nhap."""
    identifier: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Username hoac email",
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Mat khau",
    )


class UserInfo(BaseModel):
    """Thong tin user tra ve sau khi dang nhap."""
    id: int
    full_name: str
    email: str | None
    username: str | None
    role: str  # Role code (STUDENT, TEACHER, ...)
    school_id: int | None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response tra ve sau khi dang nhap thanh cong."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token de lam moi access token")
    token_type: str = Field("bearer", description="Loai token")
    expires_in: int = Field(..., description="Thoi gian het han (giay)")
    user: UserInfo


# ============================================
# REFRESH TOKEN SCHEMAS
# ============================================

class RefreshRequest(BaseModel):
    """Request body de lam moi access token."""
    refresh_token: str = Field(..., description="Refresh token hien tai")


# ============================================
# LOGOUT SCHEMAS
# ============================================

class LogoutRequest(BaseModel):
    """Request body de dang xuat."""
    refresh_token: str = Field(..., description="Refresh token can revoke")
    logout_all: bool = Field(
        False,
        description="Revoke tat ca tokens cua user (dang xuat moi thiet bi)",
    )


# ============================================
# CHANGE PASSWORD SCHEMAS
# ============================================

class ChangePasswordRequest(BaseModel):
    """Request body de doi mat khau."""
    current_password: str = Field(
        ...,
        min_length=1,
        description="Mat khau hien tai",
    )
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Mat khau moi (toi thieu 6 ky tu)",
    )
    logout_other_devices: bool = Field(
        True,
        description="Revoke tat ca refresh tokens khac",
    )


# ============================================
# FORGOT / RESET PASSWORD SCHEMAS
# ============================================

class ForgotPasswordRequest(BaseModel):
    """Request body de yeu cau reset mat khau."""
    email: EmailStr = Field(..., description="Email dang ky")


class ForgotPasswordResponse(BaseModel):
    """Response sau khi gui yeu cau reset."""
    message: str = Field(
        "Neu email ton tai, chung toi se gui huong dan reset mat khau.",
        description="Thong bao (khong tiet lo email co ton tai khong)",
    )


class ResetPasswordRequest(BaseModel):
    """Request body de reset mat khau."""
    token: str = Field(..., description="Reset token tu email")
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Mat khau moi",
    )


class ResetPasswordResponse(BaseModel):
    """Response sau khi reset thanh cong."""
    message: str = "Mat khau da duoc cap nhat thanh cong."


# ============================================
# COMMON RESPONSE SCHEMAS
# ============================================

class AuthMessageResponse(BaseModel):
    """Response don gian cho cac thao tac auth."""
    message: str
    success: bool = True
