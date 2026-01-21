"""
Module models - Export tat ca cac SQLAlchemy models.
Import module nay de su dung cac model trong ung dung.
"""
from app.models.auth import AuthRefreshToken, PasswordResetToken
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.chat import ChatMessage, ChatSession
from app.models.class_ import Class
from app.models.education import (
    BookletRead,
    DailyKindMessage,
    DailyKindResponse,
    EducationContent,
    ExerciseAttempt,
    ExerciseQuestion,
    MinigameResult,
)
from app.models.emergency_contact import EmergencyContact
from app.models.file import File
from app.models.notification import Notification
from app.models.reports import (
    IncidentType,
    Report,
    ReportAIAnalysis,
    ReportAttachment,
    ReportDestination,
    ReportStatusHistory,
)
from app.models.role import Role
from app.models.school import School
from app.models.support_organization import SupportOrganization
from app.models.system_setting import SystemSetting
from app.models.user import StudentProfile, TeacherProfile, User

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Models
    "Role",
    "School",
    "User",
    "StudentProfile",
    "TeacherProfile",
    "Class",
    "SupportOrganization",
    "EmergencyContact",
    "File",
    "Notification",
    "SystemSetting",
    # Auth
    "AuthRefreshToken",
    "PasswordResetToken",
    # Reports
    "IncidentType",
    "Report",
    "ReportAIAnalysis",
    "ReportDestination",
    "ReportAttachment",
    "ReportStatusHistory",
    # Chat
    "ChatSession",
    "ChatMessage",
    # Education
    "EducationContent",
    "ExerciseQuestion",
    "ExerciseAttempt",
    "BookletRead",
    "MinigameResult",
    "DailyKindMessage",
    "DailyKindResponse",
]
