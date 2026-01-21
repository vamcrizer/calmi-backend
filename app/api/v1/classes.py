"""
Router cho Classes - API endpoints lien quan den lop hoc.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.class_service import ClassService
from app.schemas.class_ import ClassCreate, ClassUpdate, ClassRead
from app.schemas.common import api_response, api_list_response, api_error

router = APIRouter(prefix="/classes", tags=["Classes"])


def get_class_service(db: AsyncSession = Depends(get_db)) -> ClassService:
    """Dependency injection cho ClassService."""
    return ClassService(db)


@router.get("/")
async def list_classes(
    school_id: int = Query(..., description="ID truong hoc (bat buoc)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: ClassService = Depends(get_class_service),
):
    """Lay danh sach lop trong truong."""
    classes = await service.list_classes_by_school(school_id, skip, limit)
    return api_list_response(
        data=[ClassRead.model_validate(c) for c in classes],
        message="Lay danh sach lop thanh cong",
    )


@router.get("/{class_id}")
async def get_class(
    class_id: int,
    service: ClassService = Depends(get_class_service),
):
    """Lay thong tin chi tiet lop."""
    class_obj = await service.get_class(class_id)
    if not class_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Lop khong ton tai", 404),
        )
    return api_response(
        data=ClassRead.model_validate(class_obj),
        message="Lay thong tin lop thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassCreate,
    service: ClassService = Depends(get_class_service),
):
    """Tao lop moi."""
    try:
        class_obj = await service.create_class(data)
        return api_response(
            data=ClassRead.model_validate(class_obj),
            message="Tao lop thanh cong",
            status_code=201,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.put("/{class_id}")
async def update_class(
    class_id: int,
    data: ClassUpdate,
    service: ClassService = Depends(get_class_service),
):
    """Cap nhat thong tin lop."""
    try:
        class_obj = await service.update_class(class_id, data)
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_error("Lop khong ton tai", 404),
            )
        return api_response(
            data=ClassRead.model_validate(class_obj),
            message="Cap nhat lop thanh cong",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.put("/{class_id}/homeroom-teacher")
async def assign_homeroom_teacher(
    class_id: int,
    teacher_id: int = Query(..., description="ID giao vien chu nhiem"),
    service: ClassService = Depends(get_class_service),
):
    """
    Gan giao vien chu nhiem cho lop.
    
    Giao vien phai co role TEACHER hoac COUNSELOR va thuoc cung truong.
    """
    try:
        class_obj = await service.assign_homeroom_teacher(class_id, teacher_id)
        return api_response(
            data=ClassRead.model_validate(class_obj),
            message="Gan giao vien chu nhiem thanh cong",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.delete("/{class_id}")
async def delete_class(
    class_id: int,
    service: ClassService = Depends(get_class_service),
):
    """Xoa lop."""
    success = await service.delete_class(class_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Lop khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa lop thanh cong")
