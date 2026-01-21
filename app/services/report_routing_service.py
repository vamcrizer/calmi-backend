"""
Report Routing Service - Route reports to destinations.
Handles in-app notifications and email sending with AI analysis and attachments.
"""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reports import Report, ReportDestination
from app.repositories.notification_repository import NotificationRepository
from app.repositories.report_repository import (
    ReportAttachmentRepository,
    ReportDestinationRepository,
)
from app.services.email_service import get_email_service
from app.services.report_ai_service import AIAnalysisResult


class ReportRoutingService:
    """
    Service to route reports to their destinations.
    Includes AI analysis and attachments in emails.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dest_repo = ReportDestinationRepository(session)
        self.attach_repo = ReportAttachmentRepository(session)
        self.notif_repo = NotificationRepository(session)
        self.email_service = get_email_service()
    
    async def route_report(
        self,
        report: Report,
        ai_result: AIAnalysisResult | None = None,
    ) -> None:
        """Route a report to all its destinations."""
        for dest in report.destinations:
            try:
                if dest.destination_type == "INTERNAL_USER":
                    await self._route_to_internal_user(report, dest, ai_result)
                elif dest.destination_type == "SUPPORT_ORG":
                    await self._route_to_support_org(report, dest)
                elif dest.destination_type == "EMAIL":
                    await self._route_to_email(report, dest, ai_result)
            except Exception as e:
                await self.dest_repo.update_status(
                    dest.id,
                    status="FAILED",
                    error=str(e),
                )
    
    async def _route_to_internal_user(
        self,
        report: Report,
        dest: ReportDestination,
        ai_result: AIAnalysisResult | None = None,
    ) -> None:
        """Route to internal user via in-app notification."""
        if not dest.destination_user_id:
            raise ValueError("destination_user_id is required")
        
        content = f"Bạn có một báo cáo mới cần xử lý. Mức độ: {report.severity_level}."
        if ai_result and ai_result.receiver_guidance:
            content += f"\n\n🤖 Hướng dẫn: {ai_result.receiver_guidance}"
        
        await self.notif_repo.create({
            "user_id": dest.destination_user_id,
            "type": "REPORT_RECEIVED",
            "title": f"Báo cáo mới: {report.incident_type.name if report.incident_type else 'Báo cáo'}",
            "content": content,
            "is_read": False,
        })
        
        await self.dest_repo.update_status(dest.id, status="SENT")
    
    async def _route_to_support_org(
        self,
        report: Report,
        dest: ReportDestination,
    ) -> None:
        """Route to support organization."""
        await self.dest_repo.update_status(dest.id, status="SENT")
    
    async def _route_to_email(
        self,
        report: Report,
        dest: ReportDestination,
        ai_result: AIAnalysisResult | None = None,
    ) -> None:
        """Route to external email with attachments."""
        if not dest.destination_email:
            raise ValueError("destination_email is required")
        
        incident_type_name = report.incident_type.name if report.incident_type else "Báo cáo"
        content_preview = report.content[:500] if report.content else ""
        
        risk_type = ai_result.risk_type if ai_result else "OTHER"
        receiver_guidance = ai_result.receiver_guidance if ai_result else "Vui lòng xem xét."
        
        # Get attachments
        email_attachments = []
        attachments = await self.attach_repo.list_by_report(report.id)
        for i, att in enumerate(attachments):
            if att.file:
                file_path = att.file.anonymized_path or att.file.storage_path
                email_attachments.append({
                    "path": file_path,
                    "filename": att.file.original_filename or f"attachment_{i}",
                    "mime_type": att.file.mime_type or "application/octet-stream",
                    "cid": f"att_{att.file.id}",
                })
        
        try:
            result = self.email_service.send_report_notification(
                to=dest.destination_email,
                report_id=report.id,
                incident_type=incident_type_name,
                severity=report.severity_level,
                risk_type=risk_type,
                content_preview=content_preview,
                receiver_guidance=receiver_guidance,
                attachments=email_attachments if email_attachments else None,
            )
            
            if result:
                await self.dest_repo.update_status(dest.id, status="SENT")
            else:
                await self.dest_repo.update_status(
                    dest.id,
                    status="PENDING",
                    error="Email service disabled",
                )
        except Exception as e:
            await self.dest_repo.update_status(
                dest.id,
                status="FAILED",
                error=str(e),
            )
            raise
