"""
Router cho Auth - API endpoints xac thuc nguoi dung.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import api_error, api_response
from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    UserExistsError,
    UserNotActiveError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency injection cho AuthService."""
    return AuthService(db)


def get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Lay thong tin client tu request."""
    user_agent = request.headers.get("user-agent")
    
    # Lay IP, uu tien X-Forwarded-For (proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    
    return user_agent, ip_address


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Dang ky tai khoan student moi.
    
    - **username**: Ten dang nhap (3-50 ky tu)
    - **email**: Email
    - **password**: Mat khau (toi thieu 6 ky tu)
    - **full_name**: Ho va ten
    - **phone**: So dien thoai (tuy chon)
    - **school_id**: ID truong hoc (tuy chon)
    
    Sau dang ky se tu dong dang nhap va tra ve tokens.
    """
    user_agent, ip_address = get_client_info(request)
    
    try:
        token_response = await service.register_student(
            data=data,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return api_response(
            data=token_response.model_dump(),
            message="Dang ky thanh cong",
            status_code=201,
        )
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Dang nhap nguoi dung.
    
    - **identifier**: Username hoac email
    - **password**: Mat khau
    
    Tra ve access token (JWT) va refresh token.
    """
    user_agent, ip_address = get_client_info(request)
    
    try:
        token_response = await service.login(
            identifier=data.identifier,
            password=data.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return api_response(
            data=token_response.model_dump(),
            message="Dang nhap thanh cong",
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_error(str(e), 401),
        )
    except UserNotActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_error(str(e), 403),
        )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Lay thong tin user hien tai.
    
    Yeu cau dang nhap (access token).
    Tra ve thong tin day du cua user.
    """
    from app.schemas.auth import UserInfo
    
    user_info = UserInfo(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role.code if current_user.role else "UNKNOWN",
        school_id=current_user.school_id,
    )
    
    return api_response(
        data=user_info.model_dump(),
        message="Lay thong tin user thanh cong",
    )


@router.post("/refresh")
async def refresh_token(
    data: RefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Lam moi access token.
    
    Su dung refresh token de lay access token moi.
    Refresh token cu se bi revoke va tra ve token moi.
    """
    user_agent, ip_address = get_client_info(request)
    
    try:
        token_response = await service.refresh_token(
            refresh_token=data.refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return api_response(
            data=token_response.model_dump(),
            message="Token da duoc lam moi",
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_error(str(e), 401),
        )


@router.post("/logout")
async def logout(
    data: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Dang xuat nguoi dung.
    
    - **refresh_token**: Token can revoke
    - **logout_all**: True de dang xuat tat ca thiet bi
    """
    success = await service.logout(
        refresh_token=data.refresh_token,
        logout_all=data.logout_all,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error("Khong the dang xuat. Token khong hop le.", 400),
        )
    
    message = "Da dang xuat thanh cong"
    if data.logout_all:
        message = "Da dang xuat khoi tat ca thiet bi"
    
    return api_response(data=None, message=message)


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Doi mat khau.
    
    Yeu cau dang nhap (access token).
    """
    try:
        await service.change_password(
            user=current_user,
            current_password=data.current_password,
            new_password=data.new_password,
            logout_other_devices=data.logout_other_devices,
        )
        
        message = "Mat khau da duoc cap nhat"
        if data.logout_other_devices:
            message += ". Cac phien dang nhap khac da bi dang xuat."
        
        return api_response(data=None, message=message)
    
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Yeu cau reset mat khau.
    
    Gui email chua link reset mat khau.
    Khong tiet lo email co ton tai hay khong (bao mat).
    """
    token = await service.forgot_password(data.email)
    
    # TODO: Gui email voi token
    # Hien tai chi log token (development)
    if token:
        print(f"[DEV] Password reset token for {data.email}: {token}")
    
    # Luon tra ve cung message (bao mat)
    return api_response(
        data=None,
        message="Neu email ton tai, chung toi se gui huong dan reset mat khau.",
    )


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Reset mat khau bang token.
    
    Token duoc gui qua email tu /forgot-password.
    """
    try:
        await service.reset_password(
            token=data.token,
            new_password=data.new_password,
        )
        return api_response(
            data=None,
            message="Mat khau da duoc cap nhat thanh cong.",
        )
    
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )
