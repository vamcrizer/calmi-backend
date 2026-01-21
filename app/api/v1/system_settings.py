"""
Router cho SystemSettings - API cau hinh he thong.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.system_setting_service import SystemSettingService
from app.schemas.system_setting import (
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingRead,
)
from app.schemas.common import api_response, api_list_response, api_error

router = APIRouter(prefix="/system-settings", tags=["System Settings"])


def get_setting_service(
    db: AsyncSession = Depends(get_db),
) -> SystemSettingService:
    """Dependency injection cho SystemSettingService."""
    return SystemSettingService(db)


@router.get("/")
async def list_settings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: SystemSettingService = Depends(get_setting_service),
):
    """Lay danh sach cau hinh he thong."""
    settings = await service.list_settings(skip, limit)
    return api_list_response(
        data=[SystemSettingRead.model_validate(s) for s in settings],
        message="Lay danh sach cau hinh thanh cong",
    )


@router.get("/by-key/{key}")
async def get_setting_by_key(
    key: str,
    service: SystemSettingService = Depends(get_setting_service),
):
    """Lay cau hinh theo khoa."""
    setting = await service.get_by_key(key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error(f"Khong tim thay cau hinh voi khoa '{key}'", 404),
        )
    return api_response(
        data=SystemSettingRead.model_validate(setting),
        message="Lay cau hinh thanh cong",
    )


@router.get("/value/{key}")
async def get_setting_value(
    key: str,
    default: str | None = Query(None, description="Gia tri mac dinh"),
    service: SystemSettingService = Depends(get_setting_service),
):
    """Lay gia tri cau hinh (chi tra ve value)."""
    value = await service.get_value(key, default)
    return api_response(
        data={"key": key, "value": value},
        message="Lay gia tri cau hinh thanh cong",
    )


@router.get("/{setting_id}")
async def get_setting(
    setting_id: int,
    service: SystemSettingService = Depends(get_setting_service),
):
    """Lay cau hinh theo ID."""
    setting = await service.get_setting(setting_id)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Cau hinh khong ton tai", 404),
        )
    return api_response(
        data=SystemSettingRead.model_validate(setting),
        message="Lay cau hinh thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_setting(
    data: SystemSettingCreate,
    service: SystemSettingService = Depends(get_setting_service),
):
    """Tao cau hinh moi."""
    try:
        setting = await service.create_setting(data)
        return api_response(
            data=SystemSettingRead.model_validate(setting),
            message="Tao cau hinh thanh cong",
            status_code=201,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.put("/{setting_id}")
async def update_setting(
    setting_id: int,
    data: SystemSettingUpdate,
    service: SystemSettingService = Depends(get_setting_service),
):
    """Cap nhat cau hinh."""
    setting = await service.update_setting(setting_id, data)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Cau hinh khong ton tai", 404),
        )
    return api_response(
        data=SystemSettingRead.model_validate(setting),
        message="Cap nhat cau hinh thanh cong",
    )


@router.delete("/{setting_id}")
async def delete_setting(
    setting_id: int,
    service: SystemSettingService = Depends(get_setting_service),
):
    """Xoa cau hinh."""
    success = await service.delete_setting(setting_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Cau hinh khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa cau hinh thanh cong")
