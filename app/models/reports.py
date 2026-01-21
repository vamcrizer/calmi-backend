"""
Models for Module 1 - Anonymous Reporting.
Includes: IncidentType, Report, ReportAIAnalysis, ReportDestination,
          ReportAttachment, ReportStatusHistory.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    BigInteger, String, Text, Boolean, DateTime, 
    ForeignKey, Numeric, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.school import School
    from app.models.support_organization import SupportOrganization
    from app.models.file import File


class IncidentType(Base, TimestampMixin):
    """
    Lookup table for incident types.
    
    Examples: PHYSICAL, VERBAL, CYBERBULLYING, SEXUAL, SELF_HARM, OTHER.
    """
    __tablename__ = "incident_types"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="incident_type",
        lazy="dynamic",
    )
    
    def __repr__(self) -> str:
        return f"<IncidentType(code='{self.code}', name='{self.name}')>"


class Report(Base):
    """
    Main report table for anonymous submissions.
    
    Stores report content, AI severity cache, and status.
    Reporter identity is protected (can be NULL for strict anonymity).
    """
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    school_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
    )
    reporter_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    incident_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("incident_types.id"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    location_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Numeric(10, 8), nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Numeric(11, 8), nullable=True)
    
    # AI analysis cache (for quick access)
    severity_level: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="LOW",
    )
    ai_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status workflow
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    
    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    school: Mapped["School"] = relationship("School", lazy="selectin")
    reporter: Mapped["User"] = relationship("User", lazy="selectin")
    incident_type: Mapped["IncidentType"] = relationship(
        "IncidentType",
        back_populates="reports",
        lazy="selectin",
    )
    ai_analyses: Mapped[list["ReportAIAnalysis"]] = relationship(
        "ReportAIAnalysis",
        back_populates="report",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    destinations: Mapped[list["ReportDestination"]] = relationship(
        "ReportDestination",
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["ReportAttachment"]] = relationship(
        "ReportAttachment",
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list["ReportStatusHistory"]] = relationship(
        "ReportStatusHistory",
        back_populates="report",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Report(id={self.id}, status='{self.status}', severity='{self.severity_level}')>"


class ReportAIAnalysis(Base):
    """
    AI analysis log for audit trail.
    
    Stores full AI results including model name, severity, risk type, guidance.
    """
    __tablename__ = "report_ai_analyses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    # Relationships
    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="ai_analyses",
    )
    
    def __repr__(self) -> str:
        return f"<ReportAIAnalysis(report_id={self.report_id}, severity='{self.severity_level}')>"


class ReportDestination(Base):
    """
    Destination records for report routing.
    
    Types:
    - INTERNAL_USER: Teacher/counselor in platform
    - SUPPORT_ORG: External organization onboarded
    - EMAIL: Raw email address
    """
    __tablename__ = "report_destinations"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    destination_type: Mapped[str] = mapped_column(String(30), nullable=False)
    destination_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    destination_support_org_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("support_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    destination_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Relationships
    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="destinations",
    )
    destination_user: Mapped["User"] = relationship("User", lazy="selectin")
    destination_support_org: Mapped["SupportOrganization"] = relationship(
        "SupportOrganization",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<ReportDestination(type='{self.destination_type}', status='{self.status}')>"


class ReportAttachment(Base):
    """
    Links reports to anonymized files.
    
    Files are processed through Identity Firewall before attachment.
    """
    __tablename__ = "report_attachments"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attachment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OTHER",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    # Relationships
    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="attachments",
    )
    file: Mapped["File"] = relationship("File", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ReportAttachment(report_id={self.report_id}, file_id={self.file_id})>"


class ReportStatusHistory(Base):
    """
    Audit trail for report status changes.
    """
    __tablename__ = "report_status_history"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    # Relationships
    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="status_history",
    )
    changed_by: Mapped["User"] = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ReportStatusHistory(report_id={self.report_id}, {self.from_status}->{self.to_status})>"
