"""
Repository cho File.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.repositories.base import BaseRepository


class FileRepository(BaseRepository[File]):
    """Repository quan ly File."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(File, session)
    
    async def list_by_owner(
        self,
        owner_user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[File]:
        """
        Lay danh sach file cua nguoi dung.
        
        Args:
            owner_user_id: ID nguoi so huu
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach file
        """
        result = await self.session.execute(
            select(File)
            .where(File.owner_user_id == owner_user_id)
            .order_by(File.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_storage_path(self, storage_path: str) -> File | None:
        """Tim file theo duong dan luu tru."""
        result = await self.session.execute(
            select(File).where(File.storage_path == storage_path)
        )
        return result.scalar_one_or_none()
    
    async def mark_anonymized(
        self,
        id: int,
        anonymized_path: str,
        checksum: str | None = None,
    ) -> File | None:
        """
        Danh dau file da an danh hoa.
        
        Args:
            id: File ID
            anonymized_path: Duong dan file da xu ly
            checksum: Ma bam file moi
            
        Returns:
            File da cap nhat
        """
        return await self.update(id, {
            "is_anonymized": True,
            "anonymized_path": anonymized_path,
            "checksum": checksum,
        })
