"""
Schemas cho SystemSetting - Cau hinh he thong.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class SystemSettingBase(BaseModel):
    """Schema co so cho SystemSetting."""
    key: str = Field(..., max_length=100, description="Khoa cau hinh")
    value: str = Field(..., description="Gia tri")
    description: str | None = Field(None, description="Mo ta")


class SystemSettingCreate(SystemSettingBase):
    """Schema de tao moi SystemSetting."""
    pass


class SystemSettingUpdate(BaseModel):
    """Schema de cap nhat SystemSetting."""
    value: str | None = None
    description: str | None = None


class SystemSettingRead(SystemSettingBase):
    """Schema tra ve khi doc SystemSetting."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
