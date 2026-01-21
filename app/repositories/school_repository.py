"""
Repository cho School.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School
from app.repositories.base import BaseRepository


class SchoolRepository(BaseRepository[School]):
    """Repository quan ly School."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(School, session)
    
    async def get_by_code(self, code: str) -> School | None:
        """
        Tim truong theo ma code.
        
        Args:
            code: Ma truong (VD: THPT_HOABINH)
            
        Returns:
            School instance hoac None
        """
        result = await self.session.execute(
            select(School).where(School.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_province(
        self,
        province: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[School]:
        """
        Lay danh sach truong theo tinh/thanh pho.
        
        Args:
            province: Ten tinh/thanh pho
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach truong
        """
        result = await self.session.execute(
            select(School)
            .where(School.province == province)
            .where(School.status == "ACTIVE")
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_active(self) -> int:
        """Dem so truong dang hoat dong."""
        result = await self.session.execute(
            select(func.count(School.id)).where(School.status == "ACTIVE")
        )
        return result.scalar() or 0
