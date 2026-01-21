"""
Schemas cho User va cac Profile lien quan.
"""
from datetime import datetime, date
from pydantic import BaseModel, Field


# ============================================
# STUDENT PROFILE SCHEMAS
# ============================================

class StudentProfileBase(BaseModel):
    """Schema co so cho StudentProfile."""
    date_of_birth: date | None = Field(None, description="Ngay sinh")
    gender: str | None = Field(None, max_length=20, description="Gioi tinh")
    class_id: int | None = Field(None, description="ID lop hoc")
    guardian_name: str | None = Field(None, max_length=255, description="Ten phu huynh")
    guardian_phone: str | None = Field(None, max_length=50, description="SDT phu huynh")


class StudentProfileCreate(StudentProfileBase):
    """Schema de tao moi StudentProfile."""
    pass


class StudentProfileRead(StudentProfileBase):
    """Schema tra ve khi doc StudentProfile."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# TEACHER PROFILE SCHEMAS
# ============================================

class TeacherProfileBase(BaseModel):
    """Schema co so cho TeacherProfile."""
    position: str | None = Field(None, max_length=100, description="Chuc vu")
    specialization: str | None = Field(None, max_length=255, description="Chuyen mon")


class TeacherProfileCreate(TeacherProfileBase):
    """Schema de tao moi TeacherProfile."""
    pass


class TeacherProfileRead(TeacherProfileBase):
    """Schema tra ve khi doc TeacherProfile."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# USER SCHEMAS
# ============================================

class UserBase(BaseModel):
    """Schema co so cho User."""
    school_id: int | None = Field(None, description="ID truong hoc")
    role_id: int = Field(..., description="ID vai tro")
    full_name: str = Field(..., max_length=255, description="Ho va ten")
    email: str | None = Field(None, max_length=255, description="Email")
    phone: str | None = Field(None, max_length=50, description="So dien thoai")
    username: str | None = Field(None, max_length=100, description="Ten dang nhap")
    status: str = Field("ACTIVE", description="Trang thai")


class UserCreate(UserBase):
    """Schema de tao moi User."""
    password: str = Field(..., min_length=6, description="Mat khau")
    # Profile tuy chon - se tao cung user neu co
    student_profile: StudentProfileCreate | None = None
    teacher_profile: TeacherProfileCreate | None = None


class UserUpdate(BaseModel):
    """Schema de cap nhat User."""
    school_id: int | None = None
    role_id: int | None = None
    full_name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    username: str | None = Field(None, max_length=100)
    status: str | None = None
    password: str | None = Field(None, min_length=6, description="Mat khau moi")


class UserRead(UserBase):
    """Schema tra ve khi doc User."""
    id: int
    is_email_verified: bool
    is_phone_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    # Nested profiles
    student_profile: StudentProfileRead | None = None
    teacher_profile: TeacherProfileRead | None = None
    
    class Config:
        from_attributes = True


class UserListRead(BaseModel):
    """Schema tra ve danh sach User (gon nhe hon)."""
    id: int
    full_name: str
    email: str | None
    username: str | None
    role_id: int
    school_id: int | None
    status: str
    
    class Config:
        from_attributes = True
