"""
Module schemas - Export tat ca cac Pydantic schemas.
"""
from app.schemas.common import PaginationParams, PaginatedResponse, MessageResponse
from app.schemas.role import RoleBase, RoleCreate, RoleUpdate, RoleRead
from app.schemas.school import (
    SchoolBase, SchoolCreate, SchoolUpdate, SchoolRead, SchoolListRead
)
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserRead, UserListRead,
    StudentProfileBase, StudentProfileCreate, StudentProfileRead,
    TeacherProfileBase, TeacherProfileCreate, TeacherProfileRead,
)
from app.schemas.class_ import (
    ClassBase, ClassCreate, ClassUpdate, ClassRead, ClassWithTeacherRead
)
from app.schemas.emergency_contact import (
    EmergencyContactBase, EmergencyContactCreate, EmergencyContactUpdate,
    EmergencyContactRead, EmergencyContactQueryParams,
)
from app.schemas.file import FileBase, FileCreate, FileRead, FileAnonymizeRequest
from app.schemas.notification import (
    NotificationBase, NotificationCreate, NotificationRead, NotificationMarkRead
)
from app.schemas.system_setting import (
    SystemSettingBase, SystemSettingCreate, SystemSettingUpdate, SystemSettingRead
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    # Role
    "RoleBase", "RoleCreate", "RoleUpdate", "RoleRead",
    # School
    "SchoolBase", "SchoolCreate", "SchoolUpdate", "SchoolRead", "SchoolListRead",
    # User
    "UserBase", "UserCreate", "UserUpdate", "UserRead", "UserListRead",
    "StudentProfileBase", "StudentProfileCreate", "StudentProfileRead",
    "TeacherProfileBase", "TeacherProfileCreate", "TeacherProfileRead",
    # Class
    "ClassBase", "ClassCreate", "ClassUpdate", "ClassRead", "ClassWithTeacherRead",
    # EmergencyContact
    "EmergencyContactBase", "EmergencyContactCreate", "EmergencyContactUpdate",
    "EmergencyContactRead", "EmergencyContactQueryParams",
    # File
    "FileBase", "FileCreate", "FileRead", "FileAnonymizeRequest",
    # Notification
    "NotificationBase", "NotificationCreate", "NotificationRead", "NotificationMarkRead",
    # SystemSetting
    "SystemSettingBase", "SystemSettingCreate", "SystemSettingUpdate", "SystemSettingRead",
]
