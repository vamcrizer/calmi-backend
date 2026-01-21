"""
Schemas cho File - Quan ly file upload.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class FileBase(BaseModel):
    """Schema co so cho File."""
    storage_path: str = Field(..., max_length=500, description="Duong dan luu tru")
    original_filename: str | None = Field(None, max_length=255, description="Ten file goc")
    mime_type: str | None = Field(None, max_length=100, description="Loai file")
    size_bytes: int | None = Field(None, ge=0, description="Kich thuoc file")


class FileCreate(FileBase):
    """Schema de tao moi File."""
    owner_user_id: int | None = Field(None, description="ID nguoi upload")
    checksum: str | None = Field(None, max_length=100, description="Ma bam")


class FileRead(FileBase):
    """Schema tra ve khi doc File."""
    id: int
    owner_user_id: int | None
    is_anonymized: bool
    anonymized_path: str | None
    checksum: str | None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FileAnonymizeRequest(BaseModel):
    """Yeu cau an danh hoa file."""
    anonymized_path: str = Field(..., description="Duong dan file da an danh hoa")
    checksum: str | None = Field(None, description="Ma bam file moi")
