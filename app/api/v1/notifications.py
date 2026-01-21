"""
Router cho Notifications - API thong bao nguoi dung.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import api_error, api_list_response, api_response
from app.schemas.notification import (
    NotificationCreate,
    NotificationMarkRead,
    NotificationRead,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    """Dependency injection cho NotificationService."""
    return NotificationService(db)


@router.get("/user/{user_id}")
async def list_user_notifications(
    user_id: int,
    is_read: bool | None = Query(None, description="Loc theo trang thai doc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: NotificationService = Depends(get_notification_service),
):
    """Lay danh sach thong bao cua nguoi dung."""
    notifications = await service.list_user_notifications(user_id, is_read, skip, limit)
    return api_list_response(
        data=[NotificationRead.model_validate(n) for n in notifications],
        message="Lay danh sach thong bao thanh cong",
    )


@router.get("/user/{user_id}/unread-count")
async def get_unread_count(
    user_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Dem so thong bao chua doc."""
    count = await service.count_unread(user_id)
    return api_response(
        data={"user_id": user_id, "unread_count": count},
        message="Lay so thong bao chua doc thanh cong",
    )


@router.get("/{notification_id}")
async def get_notification(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Lay thong tin chi tiet thong bao."""
    notification = await service.get_notification(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Thong bao khong ton tai", 404),
        )
    return api_response(
        data=NotificationRead.model_validate(notification),
        message="Lay thong tin thong bao thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    service: NotificationService = Depends(get_notification_service),
):
    """Tao thong bao moi."""
    notification = await service.create_notification(data)
    return api_response(
        data=NotificationRead.model_validate(notification),
        message="Tao thong bao thanh cong",
        status_code=201,
    )


@router.post("/mark-read")
async def mark_notifications_as_read(
    data: NotificationMarkRead,
    user_id: int = Query(..., description="ID nguoi dung"),
    service: NotificationService = Depends(get_notification_service),
):
    """Danh dau cac thong bao da doc."""
    count = await service.mark_as_read(data.notification_ids, user_id)
    return api_response(
        data={"marked_count": count},
        message=f"Da danh dau {count} thong bao da doc",
    )


@router.post("/mark-all-read/{user_id}")
async def mark_all_as_read(
    user_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Danh dau tat ca thong bao da doc."""
    count = await service.mark_all_as_read(user_id)
    return api_response(
        data={"marked_count": count},
        message=f"Da danh dau {count} thong bao da doc",
    )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Xoa thong bao."""
    success = await service.delete_notification(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Thong bao khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa thong bao thanh cong")
