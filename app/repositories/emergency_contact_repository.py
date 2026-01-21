"""
Repository cho EmergencyContact - Lien he khan cap.
"""
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.emergency_contact import EmergencyContact
from app.repositories.base import BaseRepository


class EmergencyContactRepository(BaseRepository[EmergencyContact]):
    """Repository quan ly EmergencyContact."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(EmergencyContact, session)
    
    async def find_by_location(
        self,
        province: str | None = None,
        district: str | None = None,
        include_national: bool = True,
    ) -> list[EmergencyContact]:
        """
        Tim lien he khan cap theo vi tri.
        
        Tra ve cac lien he:
        - Lien he quoc gia (neu include_national=True)
        - Lien he cung tinh/thanh pho
        - Lien he cung quan/huyen (neu co)
        
        Args:
            province: Tinh/Thanh pho
            district: Quan/Huyen
            include_national: Co bao gom lien he quoc gia khong
            
        Returns:
            Danh sach lien he sap xep theo priority
        """
        conditions = [EmergencyContact.is_active == True]
        
        location_conditions = []
        
        # Lien he quoc gia (province = NULL)
        if include_national:
            location_conditions.append(EmergencyContact.province.is_(None))
        
        # Lien he theo tinh/thanh pho
        if province:
            location_conditions.append(EmergencyContact.province == province)
        
        if location_conditions:
            conditions.append(or_(*location_conditions))
        
        result = await self.session.execute(
            select(EmergencyContact)
            .options(selectinload(EmergencyContact.support_organization))
            .where(and_(*conditions))
            .order_by(
                EmergencyContact.priority,
                EmergencyContact.contact_type,
            )
        )
        return list(result.scalars().all())
    
    async def find_by_school(self, school_id: int) -> list[EmergencyContact]:
        """
        Lay lien he khan cap cua truong.
        
        Args:
            school_id: ID truong hoc
            
        Returns:
            Danh sach lien he cua truong
        """
        result = await self.session.execute(
            select(EmergencyContact)
            .where(
                and_(
                    EmergencyContact.school_id == school_id,
                    EmergencyContact.is_active == True,
                )
            )
            .order_by(EmergencyContact.priority)
        )
        return list(result.scalars().all())
    
    async def find_active_by_type(
        self,
        contact_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EmergencyContact]:
        """
        Tim lien he theo loai.
        
        Args:
            contact_type: Loai lien he (NATIONAL_111, POLICE, ...)
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach lien he
        """
        result = await self.session.execute(
            select(EmergencyContact)
            .where(
                and_(
                    EmergencyContact.contact_type == contact_type,
                    EmergencyContact.is_active == True,
                )
            )
            .order_by(EmergencyContact.priority)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
