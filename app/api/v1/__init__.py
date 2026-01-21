"""
API v1 - Router chinh bao gom tat ca cac sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.classes import router as classes_router
from app.api.v1.education import router as education_router
from app.api.v1.emergency_contacts import router as emergency_contacts_router
from app.api.v1.files import router as files_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.moods import router as moods_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.reports import router as reports_router
from app.api.v1.schools import router as schools_router
from app.api.v1.system_settings import router as system_settings_router
from app.api.v1.users import router as users_router
from app.api.v1.voice_chat import router as voice_chat_router

# Router chinh cho API v1
api_router = APIRouter()

# Dang ky cac sub-routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(schools_router)
api_router.include_router(classes_router)
api_router.include_router(emergency_contacts_router)
api_router.include_router(notifications_router)
api_router.include_router(system_settings_router)
api_router.include_router(reports_router)
api_router.include_router(inbox_router)
api_router.include_router(files_router)
api_router.include_router(chat_router)
api_router.include_router(education_router)
api_router.include_router(voice_chat_router)
api_router.include_router(moods_router)
