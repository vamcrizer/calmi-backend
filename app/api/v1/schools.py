"""
Router cho Schools - API endpoints lien quan den truong hoc.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.school_service import SchoolService
from app.schemas.school import SchoolCreate, SchoolUpdate, SchoolRead, SchoolListRead
from app.schemas.common import api_response, api_list_response, api_error

router = APIRouter(prefix="/schools", tags=["Schools"])


def get_school_service(db: AsyncSession = Depends(get_db)) -> SchoolService:
    """Dependency injection cho SchoolService."""
    return SchoolService(db)


@router.get("/")
async def list_schools(
    province: str | None = Query(None, description="Loc theo tinh/thanh pho"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: SchoolService = Depends(get_school_service),
):
    """Lay danh sach truong hoc."""
    if province:
        schools = await service.list_schools_by_province(province, skip, limit)
    else:
        schools = await service.list_schools(skip, limit)
    
    return api_list_response(
        data=[SchoolListRead.model_validate(s) for s in schools],
        message="Lay danh sach truong thanh cong",
    )


@router.get("/{school_id}")
async def get_school(
    school_id: int,
    service: SchoolService = Depends(get_school_service),
):
    """Lay thong tin chi tiet truong."""
    school = await service.get_school(school_id)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Truong khong ton tai", 404),
        )
    return api_response(
        data=SchoolRead.model_validate(school),
        message="Lay thong tin truong thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_school(
    data: SchoolCreate,
    service: SchoolService = Depends(get_school_service),
):
    """Tao truong moi."""
    try:
        school = await service.create_school(data)
        return api_response(
            data=SchoolRead.model_validate(school),
            message="Tao truong thanh cong",
            status_code=201,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.put("/{school_id}")
async def update_school(
    school_id: int,
    data: SchoolUpdate,
    service: SchoolService = Depends(get_school_service),
):
    """Cap nhat thong tin truong."""
    school = await service.update_school(school_id, data)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Truong khong ton tai", 404),
        )
    return api_response(
        data=SchoolRead.model_validate(school),
        message="Cap nhat truong thanh cong",
    )


@router.delete("/{school_id}")
async def delete_school(
    school_id: int,
    service: SchoolService = Depends(get_school_service),
):
    """Xoa truong."""
    success = await service.delete_school(school_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Truong khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa truong thanh cong")
