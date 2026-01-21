"""
Schemas cho School - Dinh nghia cac Pydantic model cho API.
"""
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class SchoolBase(BaseModel):
    """Schema co so cho School."""
    name: str = Field(..., max_length=255, description="Ten truong")
    code: str | None = Field(None, max_length=50, description="Ma truong")
    address: str | None = Field(None, description="Dia chi")
    province: str | None = Field(None, max_length=100, description="Tinh/Thanh pho")
    district: str | None = Field(None, max_length=100, description="Quan/Huyen")
    phone: str | None = Field(None, max_length=50, description="So dien thoai")
    email: str | None = Field(None, max_length=255, description="Email")
    status: str = Field("ACTIVE", description="Trang thai")


class SchoolCreate(SchoolBase):
    """Schema de tao moi School."""
    pass


class SchoolUpdate(BaseModel):
    """Schema de cap nhat School."""
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50)
    address: str | None = None
    province: str | None = Field(None, max_length=100)
    district: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    status: str | None = None


class SchoolRead(SchoolBase):
    """Schema tra ve khi doc School."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SchoolListRead(BaseModel):
    """Schema tra ve danh sach School (gon nhe hon)."""
    id: int
    name: str
    code: str | None
    province: str | None
    status: str
    
    class Config:
        from_attributes = True
