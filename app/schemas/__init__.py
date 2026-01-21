"""
Module schemas - Export tat ca cac Pydantic schemas.
"""
from app.schemas.class_ import (
    ClassBase,
    ClassCreate,
    ClassRead,
    ClassUpdate,
    ClassWithTeacherRead,
)
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.emergency_contact import (
    EmergencyContactBase,
    EmergencyContactCreate,
    EmergencyContactQueryParams,
    EmergencyContactRead,
    EmergencyContactUpdate,
)
from app.schemas.file import FileAnonymizeRequest, FileBase, FileCreate, FileRead
from app.schemas.notification import (
    NotificationBase,
    NotificationCreate,
    NotificationMarkRead,
    NotificationRead,
)
from app.schemas.role import RoleBase, RoleCreate, RoleRead, RoleUpdate
from app.schemas.school import (
    SchoolBase,
    SchoolCreate,
    SchoolListRead,
    SchoolRead,
    SchoolUpdate,
)
from app.schemas.system_setting import (
    SystemSettingBase,
    SystemSettingCreate,
    SystemSettingRead,
    SystemSettingUpdate,
)
from app.schemas.user import (
    StudentProfileBase,
    StudentProfileCreate,
    StudentProfileRead,
    TeacherProfileBase,
    TeacherProfileCreate,
    TeacherProfileRead,
    UserBase,
    UserCreate,
    UserListRead,
    UserRead,
    UserUpdate,
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
