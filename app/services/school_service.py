"""
Service cho School - Xu ly logic nghiep vu lien quan den truong hoc.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School
from app.repositories.school_repository import SchoolRepository
from app.schemas.school import SchoolCreate, SchoolUpdate


class SchoolService:
    """Service xu ly cac nghiep vu lien quan den School."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.school_repo = SchoolRepository(session)
    
    async def get_school(self, school_id: int) -> School | None:
        """Lay thong tin truong theo ID."""
        return await self.school_repo.get_by_id(school_id)
    
    async def get_school_by_code(self, code: str) -> School | None:
        """Lay truong theo ma code."""
        return await self.school_repo.get_by_code(code)
    
    async def list_schools(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[School]:
        """Lay danh sach truong."""
        return await self.school_repo.get_all(skip, limit)
    
    async def list_schools_by_province(
        self,
        province: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[School]:
        """Lay danh sach truong theo tinh/thanh pho."""
        return await self.school_repo.get_by_province(province, skip, limit)
    
    async def create_school(self, data: SchoolCreate) -> School:
        """
        Tao truong moi.
        
        Args:
            data: Du lieu truong
            
        Returns:
            School da tao
        """
        # Kiem tra code da ton tai chua
        if data.code:
            existing = await self.school_repo.get_by_code(data.code)
            if existing:
                raise ValueError(f"Ma truong '{data.code}' da ton tai")
        
        return await self.school_repo.create(data.model_dump())
    
    async def update_school(self, school_id: int, data: SchoolUpdate) -> School | None:
        """Cap nhat thong tin truong."""
        update_data = data.model_dump(exclude_unset=True)
        return await self.school_repo.update(school_id, update_data)
    
    async def delete_school(self, school_id: int) -> bool:
        """Xoa truong."""
        return await self.school_repo.delete(school_id)
    
    async def count_schools(self) -> int:
        """Dem so truong dang hoat dong."""
        return await self.school_repo.count_active()
