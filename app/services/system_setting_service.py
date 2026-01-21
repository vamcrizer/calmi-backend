"""
Service cho SystemSetting - Quan ly cau hinh he thong.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting
from app.repositories.system_setting_repository import SystemSettingRepository
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate


class SystemSettingService:
    """Service xu ly cac nghiep vu lien quan den SystemSetting."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SystemSettingRepository(session)
    
    async def get_setting(self, setting_id: int) -> SystemSetting | None:
        """Lay cau hinh theo ID."""
        return await self.repo.get_by_id(setting_id)
    
    async def get_by_key(self, key: str) -> SystemSetting | None:
        """Lay cau hinh theo khoa."""
        return await self.repo.get_by_key(key)
    
    async def get_value(self, key: str, default: str | None = None) -> str | None:
        """Lay gia tri cau hinh."""
        return await self.repo.get_value(key, default)
    
    async def list_settings(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SystemSetting]:
        """Lay danh sach cau hinh."""
        return await self.repo.get_all(skip, limit)
    
    async def create_setting(self, data: SystemSettingCreate) -> SystemSetting:
        """Tao cau hinh moi."""
        existing = await self.repo.get_by_key(data.key)
        if existing:
            raise ValueError(f"Khoa '{data.key}' da ton tai")
        
        return await self.repo.create(data.model_dump())
    
    async def update_setting(
        self,
        setting_id: int,
        data: SystemSettingUpdate,
    ) -> SystemSetting | None:
        """Cap nhat cau hinh."""
        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(setting_id, update_data)
    
    async def set_value(
        self,
        key: str,
        value: str,
        description: str | None = None,
    ) -> SystemSetting:
        """
        Thiet lap gia tri cau hinh.
        Tao moi neu chua co, cap nhat neu da ton tai.
        """
        return await self.repo.set_value(key, value, description)
    
    async def delete_setting(self, setting_id: int) -> bool:
        """Xoa cau hinh."""
        return await self.repo.delete(setting_id)
