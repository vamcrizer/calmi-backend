"""
Module repositories - Export tat ca cac repositories.
"""
from app.repositories.base import BaseRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.user_repository import (
    UserRepository,
    StudentProfileRepository,
    TeacherProfileRepository,
)
from app.repositories.class_repository import ClassRepository
from app.repositories.emergency_contact_repository import EmergencyContactRepository
from app.repositories.file_repository import FileRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.system_setting_repository import SystemSettingRepository

__all__ = [
    "BaseRepository",
    "RoleRepository",
    "SchoolRepository",
    "UserRepository",
    "StudentProfileRepository",
    "TeacherProfileRepository",
    "ClassRepository",
    "EmergencyContactRepository",
    "FileRepository",
    "NotificationRepository",
    "SystemSettingRepository",
]
