"""
Router for Receiver Inbox - View and manage received reports.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User
from app.services.report_service import (
    ReportService,
    ReportNotFoundError,
    UnauthorizedError,
    InvalidStatusTransitionError,
)
from app.schemas.reports import (
    ReportReceiverRead,
    ReportReceiverDetail,
    ReportStatusUpdate,
    AttachmentRead,
)
from app.schemas.common import api_response, api_list_response, api_error

router = APIRouter(prefix="/inbox/reports", tags=["Reports - Inbox"])


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Dependency injection for ReportService."""
    return ReportService(db)


@router.get("/")
async def list_inbox_reports(
    status_filter: str | None = Query(None, alias="status"),
    severity_level: str | None = Query(None),
    incident_type_id: int | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("TEACHER", "COUNSELOR", "SCHOOL_ADMIN", "SYSTEM_ADMIN")
    ),
    service: ReportService = Depends(get_report_service),
):
    """
    List reports in receiver's inbox.
    
    Shows only reports where current user is a destination.
    
    Filters:
    - status: NEW, IN_PROGRESS, RESOLVED, CLOSED
    - severity_level: LOW, MEDIUM, HIGH, EMERGENCY
    - incident_type_id: Filter by incident type
    - from_date, to_date: Date range
    """
    reports = await service.list_receiver_reports(
        receiver=current_user,
        status=status_filter,
        severity_level=severity_level,
        incident_type_id=incident_type_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    
    return api_list_response(
        data=[ReportReceiverRead.model_validate(r) for r in reports],
        message="Lay danh sach bao cao thanh cong",
    )


@router.get("/{report_id}")
async def get_inbox_report(
    report_id: int,
    current_user: User = Depends(
        require_roles("TEACHER", "COUNSELOR", "SCHOOL_ADMIN", "SYSTEM_ADMIN")
    ),
    service: ReportService = Depends(get_report_service),
):
    """
    Get detail of a report in inbox.
    
    Only accessible if user is a destination.
    **Never exposes reporter identity.**
    """
    try:
        report = await service.get_receiver_report(report_id, current_user)
        
        # Build response with attachments
        attachments = [
            AttachmentRead.model_validate(a) for a in report.attachments
        ]
        
        response_data = ReportReceiverDetail(
            id=report.id,
            incident_type=report.incident_type,
            title=report.title,
            content=report.content,
            location_text=report.location_text,
            status=report.status,
            severity_level=report.severity_level,
            submitted_at=report.submitted_at,
            school_id=report.school_id,
            attachments=attachments,
        )
        
        return api_response(
            data=response_data.model_dump(),
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


@router.patch("/{report_id}/status")
async def update_report_status(
    report_id: int,
    data: ReportStatusUpdate,
    current_user: User = Depends(
        require_roles("TEACHER", "COUNSELOR", "SCHOOL_ADMIN", "SYSTEM_ADMIN")
    ),
    service: ReportService = Depends(get_report_service),
):
    """
    Update report status.
    
    Valid transitions:
    - NEW -> IN_PROGRESS, CLOSED
    - IN_PROGRESS -> RESOLVED, NEW, CLOSED
    - RESOLVED -> CLOSED, IN_PROGRESS
    - CLOSED -> (terminal, no transitions)
    """
    try:
        report = await service.update_status(
            report_id=report_id,
            to_status=data.to_status,
            changed_by=current_user,
            note=data.note,
        )
        
        return api_response(
            data=ReportReceiverRead.model_validate(report),
            message=f"Da cap nhat trang thai thanh {data.to_status}",
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
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(str(e), 400),
        )
