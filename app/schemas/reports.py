"""
Schemas for Module 1 - Anonymous Reporting.
Pydantic DTOs for reports, destinations, AI analysis.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============================================
# INCIDENT TYPE SCHEMAS
# ============================================

class IncidentTypeRead(BaseModel):
    """Incident type for display."""
    id: int
    code: str
    name: str
    description: str | None = None
    
    class Config:
        from_attributes = True


# ============================================
# DESTINATION SCHEMAS
# ============================================

class DestinationInput(BaseModel):
    """Input for a single destination when creating report."""
    destination_type: str = Field(
        ...,
        description="INTERNAL_USER, SUPPORT_ORG, or EMAIL",
    )
    destination_user_id: int | None = Field(
        None,
        description="User ID for INTERNAL_USER type",
    )
    destination_support_org_id: int | None = Field(
        None,
        description="Support org ID for SUPPORT_ORG type",
    )
    destination_email: str | None = Field(
        None,
        description="Email address for EMAIL type",
    )


class DestinationRead(BaseModel):
    """Destination info in response."""
    id: int
    destination_type: str
    delivery_channel: str
    status: str
    sent_at: datetime | None = None
    
    class Config:
        from_attributes = True


# ============================================
# ATTACHMENT SCHEMAS
# ============================================

class AttachmentRead(BaseModel):
    """Attachment info in response."""
    id: int
    attachment_type: str
    file_id: int
    # Add anonymized URL when needed
    
    class Config:
        from_attributes = True


# ============================================
# AI ANALYSIS SCHEMAS
# ============================================

class AIAnalysisRead(BaseModel):
    """AI analysis result."""
    severity_level: str
    risk_type: str | None = None
    guidance: str | None = None
    model_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# REPORT SCHEMAS - STUDENT FACING
# ============================================

class ReportCreate(BaseModel):
    """Request body to create a new report."""
    content: str = Field(..., min_length=1, max_length=10000)
    incident_type_id: int = Field(..., description="ID of incident type")
    title: str | None = Field(None, max_length=255)
    location_text: str | None = Field(None, max_length=500)
    location_lat: float | None = Field(None, ge=-90, le=90)
    location_lng: float | None = Field(None, ge=-180, le=180)
    destinations: list[DestinationInput] = Field(
        default_factory=list,
        description="List of destinations to send report",
    )
    is_anonymous: bool = Field(True, description="Submit anonymously")


class ReportStudentRead(BaseModel):
    """Report info for student view (limited data)."""
    id: int
    incident_type: IncidentTypeRead
    title: str | None = None
    status: str
    severity_level: str
    ai_guidance: str | None = None
    submitted_at: datetime
    
    class Config:
        from_attributes = True


class ReportStudentDetail(BaseModel):
    """Detailed report for student view."""
    id: int
    incident_type: IncidentTypeRead
    title: str | None = None
    content: str
    location_text: str | None = None
    status: str
    severity_level: str
    ai_guidance: str | None = None
    submitted_at: datetime
    attachments: list[AttachmentRead] = []
    
    class Config:
        from_attributes = True


class ReportCreateResponse(BaseModel):
    """Response after creating a report."""
    id: int
    status: str
    severity_level: str
    ai_guidance: str | None = None
    message: str = "Bao cao da duoc gui thanh cong"


# ============================================
# REPORT SCHEMAS - RECEIVER FACING
# ============================================

class ReportReceiverRead(BaseModel):
    """Report info for receiver inbox (anonymized)."""
    id: int
    incident_type: IncidentTypeRead
    title: str | None = None
    status: str
    severity_level: str
    submitted_at: datetime
    school_id: int | None = None
    # Never expose reporter identity
    
    class Config:
        from_attributes = True


class ReportReceiverDetail(BaseModel):
    """Detailed report for receiver view (anonymized)."""
    id: int
    incident_type: IncidentTypeRead
    title: str | None = None
    content: str
    location_text: str | None = None
    status: str
    severity_level: str
    submitted_at: datetime
    school_id: int | None = None
    attachments: list[AttachmentRead] = []
    # Never expose reporter identity
    
    class Config:
        from_attributes = True


# ============================================
# STATUS UPDATE SCHEMAS
# ============================================

class ReportStatusUpdate(BaseModel):
    """Request to update report status."""
    to_status: str = Field(
        ...,
        description="NEW, IN_PROGRESS, RESOLVED, CLOSED",
    )
    note: str | None = Field(None, max_length=1000)


class StatusHistoryRead(BaseModel):
    """Status change history entry."""
    from_status: str | None
    to_status: str
    note: str | None = None
    changed_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# QUERY/FILTER SCHEMAS
# ============================================

class ReportFilterParams(BaseModel):
    """Query params for filtering reports."""
    status: str | None = None
    severity_level: str | None = None
    incident_type_id: int | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
