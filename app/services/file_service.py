"""
Service cho File - Xu ly upload va an danh hoa file.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.repositories.file_repository import FileRepository
from app.schemas.file import FileCreate


class FileService:
    """Service xu ly cac nghiep vu lien quan den File."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FileRepository(session)
    
    async def get_file(self, file_id: int) -> File | None:
        """Lay thong tin file."""
        return await self.repo.get_by_id(file_id)
    
    async def list_user_files(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[File]:
        """Lay danh sach file cua nguoi dung."""
        return await self.repo.list_by_owner(user_id, skip, limit)
    
    async def create_file_record(self, data: FileCreate) -> File:
        """
        Tao ban ghi file moi.
        Luu y: Method nay chi tao record trong DB.
        Viec upload file thuc te can xu ly rieng.
        """
        return await self.repo.create(data.model_dump())
    
    async def anonymize_file(
        self,
        file_id: int,
        anonymized_path: str,
        checksum: str | None = None,
    ) -> File | None:
        """
        Danh dau file da an danh hoa.
        
        Identity Firewall se xu ly:
        1. Xoa metadata (EXIF, GPS, ...)
        2. Luu file da xu ly vao anonymized_path
        3. Goi method nay de cap nhat record
        
        Args:
            file_id: File ID
            anonymized_path: Duong dan file da xu ly
            checksum: Ma bam file moi
            
        Returns:
            File da cap nhat
        """
        return await self.repo.mark_anonymized(file_id, anonymized_path, checksum)
    
    async def delete_file(self, file_id: int) -> bool:
        """
        Xoa record file.
        Luu y: Can xoa file vat ly rieng.
        """
        return await self.repo.delete(file_id)
