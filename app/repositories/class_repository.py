"""
Repository cho Class.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_ import Class
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository[Class]):
    """Repository quan ly Class."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Class, session)
    
    async def get_by_id_with_teacher(self, id: int) -> Class | None:
        """
        Lay lop kem thong tin giao vien chu nhiem.
        
        Args:
            id: Class ID
            
        Returns:
            Class voi homeroom_teacher da load
        """
        result = await self.session.execute(
            select(Class)
            .options(selectinload(Class.homeroom_teacher))
            .where(Class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_school(
        self,
        school_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Class]:
        """
        Lay danh sach lop trong truong.
        
        Args:
            school_id: ID truong hoc
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach lop
        """
        result = await self.session.execute(
            select(Class)
            .options(selectinload(Class.homeroom_teacher))
            .where(Class.school_id == school_id)
            .order_by(Class.grade, Class.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_school_and_name(
        self,
        school_id: int,
        name: str,
    ) -> Class | None:
        """Tim lop theo truong va ten lop."""
        result = await self.session.execute(
            select(Class).where(
                Class.school_id == school_id,
                Class.name == name,
            )
        )
        return result.scalar_one_or_none()
