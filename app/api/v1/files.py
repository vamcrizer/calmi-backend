"""
Router for File Serving - Download files with permission check.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.repositories.file_repository import FileRepository
from app.repositories.report_repository import ReportRepository, ReportAttachmentRepository
from app.schemas.common import api_response, api_error

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download file by ID.
    
    Permission rules:
    - Student can only download files from their own reports
    - Receiver can download files from reports sent to them
    - Admin can download any file
    """
    file_repo = FileRepository(db)
    report_repo = ReportRepository(db)
    attach_repo = ReportAttachmentRepository(db)
    
    # Get file
    file = await file_repo.get_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("File khong ton tai", 404),
        )
    
    # Check permission
    has_access = False
    
    # Admin can access any file
    if current_user.role and current_user.role.code in ["SYSTEM_ADMIN", "SCHOOL_ADMIN"]:
        has_access = True
    
    # Check if user is owner
    if file.owner_user_id == current_user.id:
        has_access = True
    
    # Check if user is student who submitted the report
    if not has_access:
        # Find report containing this file
        attachment = await attach_repo.get_by_file_id(file_id)
        if attachment:
            report = await report_repo.get_by_id(attachment.report_id)
            if report:
                # Student who submitted
                if report.reporter_user_id == current_user.id:
                    has_access = True
                # Receiver
                is_receiver = await report_repo.is_receiver(report.id, current_user.id)
                if is_receiver:
                    has_access = True
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_error("Ban khong co quyen truy cap file nay", 403),
        )
    
    # Get file path (use anonymized if available)
    file_path = file.anonymized_path or file.storage_path
    
    # Check file exists
    if not Path(file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("File khong ton tai tren server", 404),
        )
    
    # Return file
    return FileResponse(
        path=file_path,
        media_type=file.mime_type or "application/octet-stream",
        filename=file.original_filename,
    )


@router.get("/{file_id}/info")
async def get_file_info(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get file metadata without downloading.
    """
    file_repo = FileRepository(db)
    file = await file_repo.get_by_id(file_id)
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error("File khong ton tai", 404),
        )
    
    return api_response(
        data={
            "id": file.id,
            "original_filename": file.original_filename,
            "mime_type": file.mime_type,
            "size_bytes": file.size_bytes,
            "is_anonymized": file.is_anonymized,
        },
        message="Lay thong tin file thanh cong",
    )
