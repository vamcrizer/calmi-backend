"""
Router cho Users - API endpoints lien quan den nguoi dung.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate, UserRead, UserListRead
from app.schemas.common import api_response, api_list_response, api_error

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency injection cho UserService."""
    return UserService(db)


@router.get("/")
async def list_users(
    school_id: int | None = Query(None, description="Loc theo truong"),
    role_id: int | None = Query(None, description="Loc theo vai tro"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: UserService = Depends(get_user_service),
):
    """
    Lay danh sach nguoi dung.
    
    Co the loc theo truong va/hoac vai tro.
    """
    if school_id:
        users = await service.list_users_by_school(school_id, role_id, skip, limit)
    else:
        users = await service.user_repo.get_all(skip, limit)
    
    return api_list_response(
        data=[UserListRead.model_validate(u) for u in users],
        message="Lay danh sach nguoi dung thanh cong",
    )


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    """Lay thong tin chi tiet nguoi dung."""
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Nguoi dung khong ton tai", 404),
        )
    return api_response(
        data=UserRead.model_validate(user),
        message="Lay thong tin nguoi dung thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
):
    """
    Tao nguoi dung moi.
    
    Neu co student_profile hoac teacher_profile,
    se tao profile tuong ung.
    """
    try:
        user = await service.create_user_with_profile(data)
        return api_response(
            data=UserRead.model_validate(user),
            message="Tao nguoi dung thanh cong",
            status_code=201,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    """Cap nhat thong tin nguoi dung."""
    user = await service.update_user(user_id, data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Nguoi dung khong ton tai", 404),
        )
    return api_response(
        data=UserRead.model_validate(user),
        message="Cap nhat nguoi dung thanh cong",
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    """
    Xoa nguoi dung (soft delete).
    Thay vi xoa han, nguoi dung se bi danh dau da xoa.
    """
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Nguoi dung khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa nguoi dung thanh cong")
