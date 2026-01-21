"""
Report Service - Main orchestrator for report operations.
Coordinates Identity Firewall, AI, Routing services.
"""
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reports import Report
from app.models.user import User
from app.repositories.report_repository import (
    IncidentTypeRepository,
    ReportAttachmentRepository,
    ReportDestinationRepository,
    ReportRepository,
    ReportStatusHistoryRepository,
)
from app.schemas.reports import DestinationInput, ReportCreate
from app.services.identity_firewall_service import IdentityFirewallService
from app.services.report_ai_service import ReportAIService
from app.services.report_routing_service import ReportRoutingService

# Valid status transitions
STATUS_TRANSITIONS = {
    "NEW": ["IN_PROGRESS", "CLOSED"],
    "IN_PROGRESS": ["RESOLVED", "NEW", "CLOSED"],
    "RESOLVED": ["CLOSED", "IN_PROGRESS"],
    "CLOSED": [],  # Terminal state
}


class ReportServiceError(Exception):
    """Base exception for ReportService."""
    pass


class InvalidStatusTransitionError(ReportServiceError):
    """Invalid status transition."""
    pass


class ReportNotFoundError(ReportServiceError):
    """Report not found."""
    pass


class UnauthorizedError(ReportServiceError):
    """User not authorized."""
    pass


class ReportService:
    """
    Main service for report operations.
    
    Orchestrates:
    - Report creation with attachments and destinations
    - Identity Firewall for file anonymization
    - AI analysis for severity and guidance
    - Routing to destinations
    - Status updates
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repo = ReportRepository(session)
        self.incident_type_repo = IncidentTypeRepository(session)
        self.dest_repo = ReportDestinationRepository(session)
        self.attach_repo = ReportAttachmentRepository(session)
        self.history_repo = ReportStatusHistoryRepository(session)
        self.firewall = IdentityFirewallService(session)
        self.ai_service = ReportAIService(session)
        self.routing_service = ReportRoutingService(session)
    
    async def create_report(
        self,
        data: ReportCreate,
        student: User,
        files: list[UploadFile] | None = None,
        background_tasks = None,
    ) -> tuple[Report, str | None]:
        """
        Create a new report with attachments and destinations.
        
        Full process:
        1. Validate incident type
        2. Process files through Identity Firewall
        3. Create report record
        4. Create attachments
        5. Create destinations
        6. Run AI analysis (SYNC - to return guidance immediately)
        7. Route to destinations (BACKGROUND - to avoid blocking response)
        
        Args:
            data: Report creation data
            student: Current student user
            files: Optional list of uploaded files
            background_tasks: Optional background tasks for email routing
            
        Returns:
            Tuple of (Report, AI guidance)
        """
        # Validate incident type
        incident_type = await self.incident_type_repo.get_by_id(data.incident_type_id)
        if not incident_type:
            raise ReportServiceError("Loai su co khong hop le")
        
        # Process files through Identity Firewall
        file_results = []
        if files:
            file_results = await self.firewall.process_attachments(files)
        
        # Create report
        report_data = {
            "school_id": student.school_id,
            "reporter_user_id": student.id if not data.is_anonymous else None,
            "is_anonymous": data.is_anonymous,
            "incident_type_id": data.incident_type_id,
            "title": data.title,
            "content": data.content,
            "location_text": data.location_text,
            "location_lat": data.location_lat,
            "location_lng": data.location_lng,
            "status": "NEW",
            "severity_level": "LOW",  # Will be updated by AI
            "submitted_at": datetime.utcnow(),
        }
        
        report = await self.report_repo.create(report_data)
        
        # Create attachments
        for file_record, attachment_type in file_results:
            await self.attach_repo.create({
                "report_id": report.id,
                "file_id": file_record.id,
                "attachment_type": attachment_type,
            })
        
        # Create destinations
        for dest_input in data.destinations:
            await self._create_destination(report.id, dest_input)
        
        # Reload report with relations
        report = await self.report_repo.get_by_id_with_relations(report.id)
        
        # Run AI analysis SYNC (to return guidance immediately)
        ai_result = await self.ai_service.analyze_and_save(report)
        
        # Reload to get updated severity
        report = await self.report_repo.get_by_id_with_relations(report.id)
        
        # Route to destinations in BACKGROUND (email sending is slow)
        if background_tasks:
            background_tasks.add_task(
                self.routing_service.route_report,
                report,
                ai_result,
            )
        else:
            # Fallback: run sync if no background tasks
            await self.routing_service.route_report(report, ai_result)
        
        return report, ai_result.guidance
    
    async def _create_destination(
        self,
        report_id: int,
        dest_input: DestinationInput,
    ) -> None:
        """Create a single destination record."""
        dest_type = dest_input.destination_type
        
        # Determine delivery channel
        if dest_type == "EMAIL":
            delivery_channel = "EMAIL"
        else:
            delivery_channel = "IN_APP"
        
        await self.dest_repo.create({
            "report_id": report_id,
            "destination_type": dest_type,
            "destination_user_id": dest_input.destination_user_id,
            "destination_support_org_id": dest_input.destination_support_org_id,
            "destination_email": dest_input.destination_email,
            "delivery_channel": delivery_channel,
            "status": "PENDING",
        })
    
    async def get_student_report(self, report_id: int, student: User) -> Report:
        """
        Get a report for student view.
        
        Validates that the student owns this report.
        """
        report = await self.report_repo.get_by_id_with_relations(report_id)
        
        if not report:
            raise ReportNotFoundError("Bao cao khong ton tai")
        
        # Check ownership
        if report.reporter_user_id != student.id:
            raise UnauthorizedError("Ban khong co quyen xem bao cao nay")
        
        return report
    
    async def list_student_reports(
        self,
        student: User,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Report]:
        """List reports submitted by a student."""
        return await self.report_repo.list_for_student(student.id, skip, limit)
    
    async def get_receiver_report(self, report_id: int, receiver: User) -> Report:
        """
        Get a report for receiver view.
        
        Validates that the user is a destination for this report.
        """
        report = await self.report_repo.get_by_id_with_relations(report_id)
        
        if not report:
            raise ReportNotFoundError("Bao cao khong ton tai")
        
        # Check if user is a destination
        is_receiver = await self.report_repo.is_receiver(report_id, receiver.id)
        if not is_receiver:
            raise UnauthorizedError("Ban khong co quyen xem bao cao nay")
        
        return report
    
    async def list_receiver_reports(
        self,
        receiver: User,
        status: str | None = None,
        severity_level: str | None = None,
        incident_type_id: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Report]:
        """List reports where user is a destination."""
        return await self.report_repo.list_for_receiver(
            receiver.id,
            status=status,
            severity_level=severity_level,
            incident_type_id=incident_type_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
        )
    
    async def update_status(
        self,
        report_id: int,
        to_status: str,
        changed_by: User,
        note: str | None = None,
    ) -> Report:
        """
        Update report status.
        
        Validates status transition and records history.
        """
        report = await self.report_repo.get_by_id(report_id)
        
        if not report:
            raise ReportNotFoundError("Bao cao khong ton tai")
        
        # Check if user is a destination
        is_receiver = await self.report_repo.is_receiver(report_id, changed_by.id)
        if not is_receiver:
            raise UnauthorizedError("Ban khong co quyen cap nhat bao cao nay")
        
        # Validate status transition
        current_status = report.status
        allowed_transitions = STATUS_TRANSITIONS.get(current_status, [])
        
        if to_status not in allowed_transitions:
            raise InvalidStatusTransitionError(
                f"Khong the chuyen tu '{current_status}' sang '{to_status}'"
            )
        
        # Update status
        await self.report_repo.update_status(report_id, to_status)
        
        # Record history
        await self.history_repo.add_entry(
            report_id=report_id,
            from_status=current_status,
            to_status=to_status,
            changed_by_user_id=changed_by.id,
            note=note,
        )
        
        return await self.report_repo.get_by_id_with_relations(report_id)
    
    async def list_incident_types(self) -> list:
        """List all active incident types."""
        return await self.incident_type_repo.list_active()
