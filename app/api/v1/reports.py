"""
Router for Student Reports - Submit and view anonymous reports.
"""
import json
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.common import api_error, api_list_response, api_response
from app.schemas.reports import (
    IncidentTypeRead,
    ReportCreate,
    ReportCreateResponse,
    ReportStudentDetail,
    ReportStudentRead,
)
from app.services.report_service import (
    ReportNotFoundError,
    ReportService,
    ReportServiceError,
    UnauthorizedError,
)

router = APIRouter(prefix="/reports", tags=["Reports - Student"])


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Dependency injection for ReportService."""
    return ReportService(db)


# Cache for incident types (static data, rarely changes)
_incident_types_cache = None
_incident_types_cache_time = None


@router.get("/incident-types")
async def list_incident_types(
    service: ReportService = Depends(get_report_service),
):
    """
    List all available incident types.
    
    Public endpoint for form population.
    
    OPTIMIZED: Cached for 1 hour (static data).
    """
    global _incident_types_cache, _incident_types_cache_time
    
    from datetime import datetime, timedelta
    
    # Check cache (1 hour TTL)
    if _incident_types_cache and _incident_types_cache_time:
        if datetime.utcnow() - _incident_types_cache_time < timedelta(hours=1):
            return _incident_types_cache
    
    # Fetch from DB
    types = await service.list_incident_types()
    response = api_list_response(
        data=[IncidentTypeRead.model_validate(t) for t in types],
        message="Lay danh sach loai su co thanh cong",
    )
    
    # Update cache
    _incident_types_cache = response
    _incident_types_cache_time = datetime.utcnow()
    
    return response


@router.post("/")
async def create_report(
    content: Annotated[str, Form(...)],
    incident_type_id: Annotated[int, Form(...)],
    title: Annotated[str | None, Form()] = None,
    location_text: Annotated[str | None, Form()] = None,
    location_lat: Annotated[float | None, Form()] = None,
    location_lng: Annotated[float | None, Form()] = None,
    destinations_json: Annotated[str | None, Form()] = None,
    is_anonymous: Annotated[bool, Form()] = True,
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(require_roles("STUDENT")),
    service: ReportService = Depends(get_report_service),
    background_tasks: BackgroundTasks = None,
):
    """
    Submit a new anonymous report.
    
    Requires STUDENT role.
    
    - Attachments are processed through Identity Firewall
    - AI severity analysis is performed
    - Report is routed to specified destinations
    
    Returns AI guidance for the student.
    """
    # Parse destinations JSON
    destinations = []
    if destinations_json:
        try:
            destinations_data = json.loads(destinations_json)
            from app.schemas.reports import DestinationInput
            destinations = [DestinationInput(**d) for d in destinations_data]
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error(f"Destinations JSON khong hop le: {e}", 400),
            )
    
    # Build report data
    report_data = ReportCreate(
        content=content,
        incident_type_id=incident_type_id,
        title=title,
        location_text=location_text,
        location_lat=location_lat,
        location_lng=location_lng,
        destinations=destinations,
        is_anonymous=is_anonymous,
    )
    
    try:
        report, ai_guidance = await service.create_report(
            data=report_data,
            student=current_user,
            files=files if files else None,
            background_tasks=background_tasks,  # Pass for email routing
        )
        
        return api_response(
            data=ReportCreateResponse(
                id=report.id,
                status=report.status,
                severity_level=report.severity_level,
                ai_guidance=ai_guidance,  # AI guidance returned immediately
            ).model_dump(),
            message="Bao cao da duoc gui thanh cong",
            status_code=201,
        )
    
    except ReportServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )


@router.get("/my")
async def list_my_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("STUDENT")),
    service: ReportService = Depends(get_report_service),
):
    """List reports submitted by current student. (Cached 2 min)"""
    from app.core.cache import cache
    cache_key = f"reports:{current_user.id}:my:{skip}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    reports = await service.list_student_reports(current_user, skip, limit)
    response = api_list_response(
        data=[ReportStudentRead.model_validate(r) for r in reports],
        message="Lay danh sach bao cao thanh cong",
    )
    cache.set(cache_key, response, ttl=120)
    return response


@router.get("/{report_id}")
async def get_my_report(
    report_id: int,
    current_user: User = Depends(require_roles("STUDENT")),
    service: ReportService = Depends(get_report_service),
):
    """
    Get detail of a specific report.
    
    Student can only view their own reports.
    """
    try:
        report = await service.get_student_report(report_id, current_user)
        return api_response(
            data=ReportStudentDetail.model_validate(report),
            message="Lay chi tiet bao cao thanh cong",
        )
    
    except ReportNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error(str(e), 404),
        )
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_error(str(e), 403),
        )
