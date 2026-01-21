"""
Organization Router - API endpoints for support organizations.
Handles report management and statistics for organization users.
"""
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.models.reports import Report, ReportDestination, ReportStatusHistory
from app.models.support_organization import SupportOrganization
from app.schemas.common import api_response, api_list_response

router = APIRouter(prefix="/organization", tags=["Organization"])

# Dependency to get organization user only
OrganizationUser = Annotated[User, Depends(require_roles("ORGANIZATION"))]


# ==========================================
# SCHEMAS
# ==========================================
class ReportListItem(BaseModel):
    id: int
    incident_type_id: int
    incident_type_name: str | None = None
    title: str | None
    content_preview: str
    severity_level: str
    status: str
    submitted_at: datetime
    location_text: str | None = None


class ReportDetail(BaseModel):
    id: int
    incident_type_id: int
    incident_type_name: str | None = None
    title: str | None
    content: str
    location_text: str | None
    severity_level: str
    status: str
    ai_guidance: str | None
    submitted_at: datetime
    created_at: datetime
    status_history: list[dict] = []


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(IN_PROGRESS|RESOLVED|CLOSED)$")
    note: str | None = None


class StatsResponse(BaseModel):
    total_reports: int
    new_reports: int
    in_progress_reports: int
    resolved_reports: int
    by_severity: dict
    recent_activity: list[dict]


# ==========================================
# HELPER: Get organization ID for user
# ==========================================
async def get_user_organization_id(user: User, db: AsyncSession) -> int | None:
    """Get the support organization ID associated with this user."""
    # For now, we match by email domain or explicit link
    # In production, you'd have a user_support_org_id column or junction table
    
    # Simple approach: get the first active organization
    # TODO: Add proper user-organization linking
    result = await db.execute(
        select(SupportOrganization.id)
        .where(SupportOrganization.is_active == True)
        .limit(1)
    )
    org = result.scalar_one_or_none()
    return org


# ==========================================
# ENDPOINTS
# ==========================================
@router.get("/reports")
async def list_reports(
    current_user: OrganizationUser,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List reports assigned to this organization.
    """
    org_id = await get_user_organization_id(current_user, db)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any organization"
        )
    
    # Build query for reports destined to this organization
    query = (
        select(Report)
        .join(ReportDestination, Report.id == ReportDestination.report_id)
        .where(
            and_(
                ReportDestination.destination_support_org_id == org_id,
                Report.deleted_at.is_(None)
            )
        )
    )
    
    # Apply filters
    if status_filter:
        query = query.where(Report.status == status_filter)
    if severity:
        query = query.where(Report.severity_level == severity)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(Report.submitted_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()
    
    # Format response
    items = []
    for r in reports:
        # Get incident type name
        incident_name = None
        if r.incident_type:
            incident_name = r.incident_type.name
        
        items.append(ReportListItem(
            id=r.id,
            incident_type_id=r.incident_type_id,
            incident_type_name=incident_name,
            title=r.title,
            content_preview=r.content[:100] + "..." if len(r.content) > 100 else r.content,
            severity_level=r.severity_level or "LOW",
            status=r.status,
            submitted_at=r.submitted_at,
            location_text=r.location_text,
        ))
    
    return api_list_response(
        data=[item.model_dump() for item in items],
        total=total,
        message="Danh sach bao cao"
    )


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: int,
    current_user: OrganizationUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific report.
    """
    org_id = await get_user_organization_id(current_user, db)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any organization"
        )
    
    # Verify report belongs to this organization
    query = (
        select(Report)
        .join(ReportDestination, Report.id == ReportDestination.report_id)
        .where(
            and_(
                Report.id == report_id,
                ReportDestination.destination_support_org_id == org_id,
                Report.deleted_at.is_(None)
            )
        )
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or not accessible"
        )
    
    # Get status history
    history_query = (
        select(ReportStatusHistory)
        .where(ReportStatusHistory.report_id == report_id)
        .order_by(ReportStatusHistory.changed_at.desc())
    )
    history_result = await db.execute(history_query)
    history = history_result.scalars().all()
    
    history_items = [
        {
            "from_status": h.from_status,
            "to_status": h.to_status,
            "note": h.note,
            "changed_at": h.changed_at.isoformat(),
        }
        for h in history
    ]
    
    # Get incident type name
    incident_name = None
    if report.incident_type:
        incident_name = report.incident_type.name
    
    detail = ReportDetail(
        id=report.id,
        incident_type_id=report.incident_type_id,
        incident_type_name=incident_name,
        title=report.title,
        content=report.content,
        location_text=report.location_text,
        severity_level=report.severity_level or "LOW",
        status=report.status,
        ai_guidance=report.ai_guidance,
        submitted_at=report.submitted_at,
        created_at=report.created_at,
        status_history=history_items,
    )
    
    return api_response(
        data=detail.model_dump(),
        message="Chi tiet bao cao"
    )


@router.put("/reports/{report_id}/status")
async def update_report_status(
    report_id: int,
    request: StatusUpdateRequest,
    current_user: OrganizationUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of a report.
    """
    org_id = await get_user_organization_id(current_user, db)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any organization"
        )
    
    # Verify report belongs to this organization
    query = (
        select(Report)
        .join(ReportDestination, Report.id == ReportDestination.report_id)
        .where(
            and_(
                Report.id == report_id,
                ReportDestination.destination_support_org_id == org_id,
                Report.deleted_at.is_(None)
            )
        )
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or not accessible"
        )
    
    # Create status history entry
    old_status = report.status
    history_entry = ReportStatusHistory(
        report_id=report_id,
        from_status=old_status,
        to_status=request.status,
        changed_by_user_id=current_user.id,
        note=request.note,
    )
    db.add(history_entry)
    
    # Update report status
    report.status = request.status
    report.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return api_response(
        data={
            "report_id": report_id,
            "old_status": old_status,
            "new_status": request.status,
        },
        message="Cap nhat trang thai thanh cong"
    )


@router.get("/stats")
async def get_organization_stats(
    current_user: OrganizationUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard statistics for the organization.
    """
    org_id = await get_user_organization_id(current_user, db)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any organization"
        )
    
    # Base query for reports belonging to this org
    base_query = (
        select(Report)
        .join(ReportDestination, Report.id == ReportDestination.report_id)
        .where(
            and_(
                ReportDestination.destination_support_org_id == org_id,
                Report.deleted_at.is_(None)
            )
        )
    )
    
    # Total reports
    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = total_result.scalar() or 0
    
    # Count by status
    status_counts = {}
    for status_val in ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
        count_result = await db.execute(
            select(func.count()).select_from(
                base_query.where(Report.status == status_val).subquery()
            )
        )
        status_counts[status_val.lower()] = count_result.scalar() or 0
    
    # Count by severity
    severity_counts = {}
    for sev in ["LOW", "MEDIUM", "HIGH", "EMERGENCY"]:
        count_result = await db.execute(
            select(func.count()).select_from(
                base_query.where(Report.severity_level == sev).subquery()
            )
        )
        severity_counts[sev.lower()] = count_result.scalar() or 0
    
    # Recent activity (last 5 status changes)
    activity_query = (
        select(ReportStatusHistory)
        .join(Report, ReportStatusHistory.report_id == Report.id)
        .join(ReportDestination, Report.id == ReportDestination.report_id)
        .where(ReportDestination.destination_support_org_id == org_id)
        .order_by(ReportStatusHistory.changed_at.desc())
        .limit(5)
    )
    activity_result = await db.execute(activity_query)
    activities = activity_result.scalars().all()
    
    recent_activity = [
        {
            "report_id": a.report_id,
            "from_status": a.from_status,
            "to_status": a.to_status,
            "changed_at": a.changed_at.isoformat(),
        }
        for a in activities
    ]
    
    stats = StatsResponse(
        total_reports=total,
        new_reports=status_counts.get("new", 0),
        in_progress_reports=status_counts.get("in_progress", 0),
        resolved_reports=status_counts.get("resolved", 0),
        by_severity=severity_counts,
        recent_activity=recent_activity,
    )
    
    return api_response(
        data=stats.model_dump(),
        message="Thong ke to chuc"
    )
