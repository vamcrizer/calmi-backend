"""
Schemas cho Class - Dinh nghia cac Pydantic model cho API.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ClassBase(BaseModel):
    """Schema co so cho Class."""
    school_id: int = Field(..., description="ID truong hoc")
    name: str = Field(..., max_length=100, description="Ten lop (VD: 10A1)")
    grade: str | None = Field(None, max_length=20, description="Khoi lop")
    homeroom_teacher_id: int | None = Field(None, description="ID giao vien chu nhiem")


class ClassCreate(ClassBase):
    """Schema de tao moi Class."""
    pass


class ClassUpdate(BaseModel):
    """Schema de cap nhat Class."""
    name: str | None = Field(None, max_length=100)
    grade: str | None = Field(None, max_length=20)
    homeroom_teacher_id: int | None = None


class ClassRead(ClassBase):
    """Schema tra ve khi doc Class."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ClassWithTeacherRead(ClassRead):
    """Schema tra ve Class kem thong tin giao vien chu nhiem."""
    homeroom_teacher_name: str | None = None
