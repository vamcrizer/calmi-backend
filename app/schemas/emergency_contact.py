"""
Schemas cho EmergencyContact - Lien he khan cap cho SOS.
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class EmergencyContactBase(BaseModel):
    """Schema co so cho EmergencyContact."""
    support_org_id: int | None = Field(None, description="ID to chuc ho tro")
    school_id: int | None = Field(None, description="ID truong hoc")
    contact_type: str = Field(..., max_length=50, description="Loai lien he")
    name: str = Field(..., max_length=255, description="Ten hien thi")
    phone: str = Field(..., max_length=50, description="So dien thoai")
    province: str | None = Field(None, max_length=100, description="Tinh/Thanh pho")
    district: str | None = Field(None, max_length=100, description="Quan/Huyen")
    latitude: Decimal | None = Field(None, description="Vi do")
    longitude: Decimal | None = Field(None, description="Kinh do")
    priority: int = Field(1, ge=1, description="Do uu tien")
    is_active: bool = Field(True, description="Trang thai hoat dong")


class EmergencyContactCreate(EmergencyContactBase):
    """Schema de tao moi EmergencyContact."""
    pass


class EmergencyContactUpdate(BaseModel):
    """Schema de cap nhat EmergencyContact."""
    support_org_id: int | None = None
    school_id: int | None = None
    contact_type: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    province: str | None = Field(None, max_length=100)
    district: str | None = Field(None, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    priority: int | None = Field(None, ge=1)
    is_active: bool | None = None


class EmergencyContactRead(EmergencyContactBase):
    """Schema tra ve khi doc EmergencyContact."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EmergencyContactQueryParams(BaseModel):
    """Tham so truy van tim kiem lien he khan cap."""
    province: str | None = Field(None, description="Loc theo tinh/thanh pho")
    district: str | None = Field(None, description="Loc theo quan/huyen")
    school_id: int | None = Field(None, description="Loc theo truong")
    contact_type: str | None = Field(None, description="Loc theo loai lien he")
    is_active: bool = Field(True, description="Chi lay lien he dang hoat dong")
