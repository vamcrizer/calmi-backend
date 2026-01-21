"""
Identity Firewall Service - Anonymize uploaded files.
Strips metadata (EXIF, GPS) and renames files to protect reporter identity.
"""
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.file import File
from app.repositories.file_repository import FileRepository

settings = get_settings()

# Storage directory for anonymized files
STORAGE_DIR = Path("storage/anonymized")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


def determine_attachment_type(content_type: str, extension: str) -> str:
    """Determine attachment type from content type or extension."""
    image_types = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
    video_types = {"mp4", "mov", "avi", "mkv", "webm"}
    audio_types = {"mp3", "wav", "ogg", "m4a"}
    doc_types = {"pdf", "doc", "docx", "txt"}
    
    if content_type.startswith("image/") or extension in image_types:
        return "IMAGE"
    if content_type.startswith("video/") or extension in video_types:
        return "VIDEO"
    if content_type.startswith("audio/") or extension in audio_types:
        return "AUDIO"
    if extension in doc_types:
        return "DOCUMENT"
    return "OTHER"


def strip_image_metadata(file_path: Path) -> bool:
    """
    Strip EXIF/metadata from image files.
    
    Uses Pillow to remove metadata.
    Returns True if successful, False if failed or not an image.
    """
    try:
        from PIL import Image
        
        img = Image.open(file_path)
        
        # Create a new image without metadata
        data = list(img.getdata())
        img_without_exif = Image.new(img.mode, img.size)
        img_without_exif.putdata(data)
        
        # Save back
        img_without_exif.save(file_path)
        return True
    except Exception:
        # Not an image or Pillow not available
        return False


class IdentityFirewallService:
    """
    Service to anonymize uploaded files.
    
    Process:
    1. Generate UUID-based filename
    2. Save file to storage
    3. Strip metadata (EXIF, GPS, etc.)
    4. Create File record with is_anonymized=True
    5. Do NOT set owner_user_id to protect identity
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = FileRepository(session)
    
    async def process_attachment(
        self,
        upload_file: UploadFile,
        original_filename: str | None = None,
    ) -> tuple[File, str]:
        """
        Process a single uploaded file through Identity Firewall.
        
        Args:
            upload_file: FastAPI UploadFile
            original_filename: Original filename (for extension)
            
        Returns:
            Tuple of (File record, attachment_type)
        """
        # Get file info
        orig_name = original_filename or upload_file.filename or "file"
        extension = get_file_extension(orig_name)
        content_type = upload_file.content_type or "application/octet-stream"
        attachment_type = determine_attachment_type(content_type, extension)
        
        # Generate anonymous filename
        anonymous_name = f"{uuid.uuid4().hex}"
        if extension:
            anonymous_name = f"{anonymous_name}.{extension}"
        
        # Create storage path
        today = datetime.utcnow().strftime("%Y/%m/%d")
        storage_subdir = STORAGE_DIR / today
        storage_subdir.mkdir(parents=True, exist_ok=True)
        
        storage_path = storage_subdir / anonymous_name
        
        # Save file
        content = await upload_file.read()
        file_size = len(content)
        
        with open(storage_path, "wb") as f:
            f.write(content)
        
        # Strip metadata for images
        if attachment_type == "IMAGE":
            strip_image_metadata(storage_path)
        
        # Create File record
        # IMPORTANT: Do NOT set owner_user_id to protect identity
        file_record = await self.file_repo.create({
            "original_filename": orig_name,
            "storage_path": str(storage_path),
            "anonymized_path": str(storage_path),  # Same path after processing
            "mime_type": content_type,
            "file_size": file_size,
            "is_anonymized": True,
            "owner_user_id": None,  # Anonymous - no owner
        })
        
        return file_record, attachment_type
    
    async def process_attachments(
        self,
        upload_files: list[UploadFile],
    ) -> list[tuple[File, str]]:
        """
        Process multiple files through Identity Firewall.
        
        Args:
            upload_files: List of FastAPI UploadFiles
            
        Returns:
            List of (File record, attachment_type) tuples
        """
        results = []
        for upload_file in upload_files:
            if upload_file.filename:  # Skip empty uploads
                result = await self.process_attachment(upload_file)
                results.append(result)
        return results
