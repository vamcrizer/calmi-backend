"""
Repository cho SystemSetting.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """Repository quan ly SystemSetting."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(SystemSetting, session)
    
    async def get_by_key(self, key: str) -> SystemSetting | None:
        """
        Lay cau hinh theo khoa.
        
        Args:
            key: Khoa cau hinh
            
        Returns:
            SystemSetting instance hoac None
        """
        result = await self.session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        return result.scalar_one_or_none()
    
    async def get_value(self, key: str, default: str | None = None) -> str | None:
        """
        Lay gia tri cau hinh theo khoa.
        
        Args:
            key: Khoa cau hinh
            default: Gia tri mac dinh neu khong tim thay
            
        Returns:
            Gia tri cau hinh hoac default
        """
        setting = await self.get_by_key(key)
        return setting.value if setting else default
    
    async def set_value(self, key: str, value: str, description: str | None = None) -> SystemSetting:
        """
        Thiet lap gia tri cau hinh.
        Tao moi neu chua ton tai, cap nhat neu da co.
        
        Args:
            key: Khoa cau hinh
            value: Gia tri
            description: Mo ta (chi dung khi tao moi)
            
        Returns:
            SystemSetting instance
        """
        existing = await self.get_by_key(key)
        if existing:
            return await self.update(existing.id, {"value": value})
        
        return await self.create({
            "key": key,
            "value": value,
            "description": description,
        })
