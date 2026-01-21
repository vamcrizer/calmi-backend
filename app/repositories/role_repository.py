"""
Repository cho Role.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository quan ly Role."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)
    
    async def get_by_code(self, code: str) -> Role | None:
        """
        Tim role theo ma code.
        
        Args:
            code: Ma role (VD: STUDENT, TEACHER)
            
        Returns:
            Role instance hoac None
        """
        result = await self.session.execute(
            select(Role).where(Role.code == code)
        )
        return result.scalar_one_or_none()
