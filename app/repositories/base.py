"""
Base Repository - Cung cap cac thao tac CRUD co ban.
Cac repository khac se ke thua tu class nay.
"""
from typing import TypeVar, Generic, Type
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repository co ban voi cac thao tac CRUD.
    
    Su dung Generic de tai su dung cho nhieu model khac nhau.
    Cac repository cu the ke thua va mo rong them cac method rieng.
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Khoi tao repository.
        
        Args:
            model: Class SQLAlchemy model
            session: Async database session
        """
        self.model = model
        self.session = session
    
    async def get_by_id(self, id: int) -> ModelType | None:
        """
        Lay ban ghi theo ID.
        
        Args:
            id: Primary key cua ban ghi
            
        Returns:
            Model instance hoac None neu khong tim thay
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Lay danh sach ban ghi co phan trang.
        
        Args:
            skip: So ban ghi bo qua
            limit: So ban ghi toi da tra ve
            
        Returns:
            Danh sach model instances
        """
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """Dem tong so ban ghi."""
        result = await self.session.execute(
            select(func.count(self.model.id))
        )
        return result.scalar() or 0
    
    async def create(self, obj_data: dict) -> ModelType:
        """
        Tao ban ghi moi.
        
        Args:
            obj_data: Dict chua du lieu de tao ban ghi
            
        Returns:
            Model instance da tao
        """
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, id: int, obj_data: dict) -> ModelType | None:
        """
        Cap nhat ban ghi.
        
        Args:
            id: Primary key cua ban ghi
            obj_data: Dict chua du lieu cap nhat (chi cac field thay doi)
            
        Returns:
            Model instance da cap nhat hoac None
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None
        
        for key, value in obj_data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> bool:
        """
        Xoa ban ghi.
        
        Args:
            id: Primary key cua ban ghi
            
        Returns:
            True neu xoa thanh cong, False neu khong tim thay
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
        
        await self.session.delete(db_obj)
        await self.session.commit()
        return True
