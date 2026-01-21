"""
Router cho EmergencyContacts - API lien he khan cap cho SOS.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import api_error, api_list_response, api_response
from app.schemas.emergency_contact import (
    EmergencyContactCreate,
    EmergencyContactRead,
    EmergencyContactUpdate,
)
from app.services.emergency_contact_service import EmergencyContactService

router = APIRouter(prefix="/emergency-contacts", tags=["Emergency Contacts"])


def get_emergency_service(
    db: AsyncSession = Depends(get_db),
) -> EmergencyContactService:
    """Dependency injection cho EmergencyContactService."""
    return EmergencyContactService(db)


@router.get("/for-location")
async def get_contacts_for_location(
    province: str | None = Query(None, description="Tinh/Thanh pho"),
    district: str | None = Query(None, description="Quan/Huyen"),
    school_id: int | None = Query(None, description="ID truong hoc"),
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """
    Lay danh sach lien he khan cap cho vi tri cu the.
    
    Dung cho tinh nang SOS - tra ve cac lien he:
    - Lien he quoc gia (111)
    - Lien he cua truong (neu co)
    - Lien he trong vung
    
    Ket qua sap xep theo do uu tien.
    """
    contacts = await service.get_available_for_location(province, district, school_id)
    return api_list_response(
        data=[EmergencyContactRead.model_validate(c) for c in contacts],
        message="Lay danh sach lien he khan cap thanh cong",
    )


@router.get("/by-school/{school_id}")
async def get_contacts_by_school(
    school_id: int,
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Lay danh sach lien he khan cap cua truong."""
    contacts = await service.list_by_school(school_id)
    return api_list_response(
        data=[EmergencyContactRead.model_validate(c) for c in contacts],
        message="Lay danh sach lien he cua truong thanh cong",
    )


@router.get("/by-type/{contact_type}")
async def get_contacts_by_type(
    contact_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Lay danh sach lien he theo loai (NATIONAL_111, POLICE, ...)."""
    contacts = await service.list_by_type(contact_type, skip, limit)
    return api_list_response(
        data=[EmergencyContactRead.model_validate(c) for c in contacts],
        message=f"Lay danh sach lien he loai {contact_type} thanh cong",
    )


@router.get("/{contact_id}")
async def get_contact(
    contact_id: int,
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Lay thong tin chi tiet lien he khan cap."""
    contact = await service.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Lien he khong ton tai", 404),
        )
    return api_response(
        data=EmergencyContactRead.model_validate(contact),
        message="Lay thong tin lien he thanh cong",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: EmergencyContactCreate,
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Tao lien he khan cap moi."""
    contact = await service.create_contact(data)
    return api_response(
        data=EmergencyContactRead.model_validate(contact),
        message="Tao lien he thanh cong",
        status_code=201,
    )


@router.put("/{contact_id}")
async def update_contact(
    contact_id: int,
    data: EmergencyContactUpdate,
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Cap nhat lien he khan cap."""
    contact = await service.update_contact(contact_id, data)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Lien he khong ton tai", 404),
        )
    return api_response(
        data=EmergencyContactRead.model_validate(contact),
        message="Cap nhat lien he thanh cong",
    )


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    service: EmergencyContactService = Depends(get_emergency_service),
):
    """Xoa lien he khan cap."""
    success = await service.delete_contact(contact_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("Lien he khong ton tai", 404),
        )
    return api_response(data=None, message="Xoa lien he thanh cong")
