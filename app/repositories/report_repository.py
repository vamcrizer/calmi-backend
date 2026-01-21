"""
Repositories for Module 1 - Reports.
"""
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reports import (
    IncidentType,
    Report,
    ReportAIAnalysis,
    ReportDestination,
    ReportAttachment,
    ReportStatusHistory,
)
from app.repositories.base import BaseRepository


class IncidentTypeRepository(BaseRepository[IncidentType]):
    """Repository for IncidentType."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(IncidentType, session)
    
    async def get_by_code(self, code: str) -> IncidentType | None:
        """Get incident type by code."""
        result = await self.session.execute(
            select(IncidentType).where(IncidentType.code == code)
        )
        return result.scalar_one_or_none()
    
    async def list_active(self) -> list[IncidentType]:
        """List all active incident types."""
        result = await self.session.execute(
            select(IncidentType)
            .where(IncidentType.is_active == True)
            .order_by(IncidentType.name)
        )
        return list(result.scalars().all())


class ReportRepository(BaseRepository[Report]):
    """Repository for Report."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Report, session)
    
    async def get_by_id_with_relations(self, id: int) -> Report | None:
        """Get report with all relations loaded."""
        result = await self.session.execute(
            select(Report)
            .options(
                selectinload(Report.incident_type),
                selectinload(Report.attachments),
                selectinload(Report.destinations),
            )
            .where(Report.id == id)
            .where(Report.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def list_for_student(
        self,
        reporter_user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Report]:
        """List reports submitted by a student."""
        result = await self.session.execute(
            select(Report)
            .options(selectinload(Report.incident_type))
            .where(
                and_(
                    Report.reporter_user_id == reporter_user_id,
                    Report.deleted_at.is_(None),
                )
            )
            .order_by(Report.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_for_receiver(
        self,
        receiver_user_id: int,
        status: str | None = None,
        severity_level: str | None = None,
        incident_type_id: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Report]:
        """List reports where user is a destination."""
        # Subquery to find report IDs where user is destination
        dest_subq = (
            select(ReportDestination.report_id)
            .where(ReportDestination.destination_user_id == receiver_user_id)
            .distinct()
        )
        
        query = (
            select(Report)
            .options(selectinload(Report.incident_type))
            .where(
                and_(
                    Report.id.in_(dest_subq),
                    Report.deleted_at.is_(None),
                )
            )
        )
        
        # Apply filters
        if status:
            query = query.where(Report.status == status)
        if severity_level:
            query = query.where(Report.severity_level == severity_level)
        if incident_type_id:
            query = query.where(Report.incident_type_id == incident_type_id)
        if from_date:
            query = query.where(Report.submitted_at >= from_date)
        if to_date:
            query = query.where(Report.submitted_at <= to_date)
        
        result = await self.session.execute(
            query.order_by(Report.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def is_receiver(self, report_id: int, user_id: int) -> bool:
        """Check if user is a destination for this report."""
        result = await self.session.execute(
            select(ReportDestination.id)
            .where(
                and_(
                    ReportDestination.report_id == report_id,
                    ReportDestination.destination_user_id == user_id,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def update_status(
        self,
        report_id: int,
        new_status: str,
    ) -> Report | None:
        """Update report status."""
        report = await self.get_by_id(report_id)
        if report:
            report.status = new_status
            report.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(report)
        return report
    
    async def update_ai_result(
        self,
        report_id: int,
        severity_level: str,
        ai_guidance: str | None,
    ) -> Report | None:
        """Update cached AI analysis result."""
        report = await self.get_by_id(report_id)
        if report:
            report.severity_level = severity_level
            report.ai_guidance = ai_guidance
            report.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(report)
        return report


class ReportAIAnalysisRepository(BaseRepository[ReportAIAnalysis]):
    """Repository for ReportAIAnalysis."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ReportAIAnalysis, session)
    
    async def get_latest_for_report(self, report_id: int) -> ReportAIAnalysis | None:
        """Get latest AI analysis for a report."""
        result = await self.session.execute(
            select(ReportAIAnalysis)
            .where(ReportAIAnalysis.report_id == report_id)
            .order_by(ReportAIAnalysis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ReportDestinationRepository(BaseRepository[ReportDestination]):
    """Repository for ReportDestination."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ReportDestination, session)
    
    async def list_by_report(self, report_id: int) -> list[ReportDestination]:
        """Get all destinations for a report."""
        result = await self.session.execute(
            select(ReportDestination)
            .where(ReportDestination.report_id == report_id)
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        destination_id: int,
        status: str,
        error: str | None = None,
    ) -> ReportDestination | None:
        """Update destination delivery status."""
        dest = await self.get_by_id(destination_id)
        if dest:
            dest.status = status
            dest.last_error = error
            if status == "SENT":
                dest.sent_at = datetime.utcnow()
            dest.updated_at = datetime.utcnow()
            await self.session.commit()
        return dest


class ReportAttachmentRepository(BaseRepository[ReportAttachment]):
    """Repository for ReportAttachment."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ReportAttachment, session)
    
    async def list_by_report(self, report_id: int) -> list[ReportAttachment]:
        """Get all attachments for a report."""
        result = await self.session.execute(
            select(ReportAttachment)
            .options(selectinload(ReportAttachment.file))
            .where(ReportAttachment.report_id == report_id)
        )
        return list(result.scalars().all())
    
    async def get_by_file_id(self, file_id: int) -> ReportAttachment | None:
        """Find attachment by file ID."""
        result = await self.session.execute(
            select(ReportAttachment)
            .where(ReportAttachment.file_id == file_id)
        )
        return result.scalar_one_or_none()


class ReportStatusHistoryRepository(BaseRepository[ReportStatusHistory]):
    """Repository for ReportStatusHistory."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ReportStatusHistory, session)
    
    async def list_by_report(self, report_id: int) -> list[ReportStatusHistory]:
        """Get status history for a report."""
        result = await self.session.execute(
            select(ReportStatusHistory)
            .where(ReportStatusHistory.report_id == report_id)
            .order_by(ReportStatusHistory.changed_at)
        )
        return list(result.scalars().all())
    
    async def add_entry(
        self,
        report_id: int,
        from_status: str | None,
        to_status: str,
        changed_by_user_id: int | None,
        note: str | None = None,
    ) -> ReportStatusHistory:
        """Add a new status history entry."""
        return await self.create({
            "report_id": report_id,
            "from_status": from_status,
            "to_status": to_status,
            "changed_by_user_id": changed_by_user_id,
            "note": note,
        })
