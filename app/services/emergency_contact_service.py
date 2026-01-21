"""
Service cho EmergencyContact - Xu ly logic lien he khan cap cho SOS.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency_contact import EmergencyContact
from app.repositories.emergency_contact_repository import EmergencyContactRepository
from app.schemas.emergency_contact import EmergencyContactCreate, EmergencyContactUpdate


class EmergencyContactService:
    """Service xu ly cac nghiep vu lien quan den EmergencyContact."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = EmergencyContactRepository(session)
    
    async def get_contact(self, contact_id: int) -> EmergencyContact | None:
        """Lay thong tin lien he khan cap."""
        return await self.repo.get_by_id(contact_id)
    
    async def get_available_for_location(
        self,
        province: str | None = None,
        district: str | None = None,
        school_id: int | None = None,
    ) -> list[EmergencyContact]:
        """
        Lay danh sach lien he khan cap cho vi tri cu the.
        
        Thu tu uu tien:
        1. Lien he quoc gia (111)
        2. Lien he cua truong (neu co school_id)
        3. Lien he trong tinh/thanh pho
        
        Args:
            province: Tinh/Thanh pho
            district: Quan/Huyen
            school_id: ID truong hoc
            
        Returns:
            Danh sach lien he sap xep theo priority
        """
        contacts = []
        
        # Lay lien he theo vi tri (bao gom quoc gia)
        location_contacts = await self.repo.find_by_location(
            province=province,
            district=district,
            include_national=True,
        )
        contacts.extend(location_contacts)
        
        # Them lien he cua truong
        if school_id:
            school_contacts = await self.repo.find_by_school(school_id)
            # Tranh trung lap
            existing_ids = {c.id for c in contacts}
            for contact in school_contacts:
                if contact.id not in existing_ids:
                    contacts.append(contact)
        
        # Sap xep lai theo priority
        contacts.sort(key=lambda c: (c.priority, c.contact_type))
        
        return contacts
    
    async def list_by_school(self, school_id: int) -> list[EmergencyContact]:
        """Lay danh sach lien he cua truong."""
        return await self.repo.find_by_school(school_id)
    
    async def list_by_type(
        self,
        contact_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EmergencyContact]:
        """Lay danh sach lien he theo loai."""
        return await self.repo.find_active_by_type(contact_type, skip, limit)
    
    async def create_contact(self, data: EmergencyContactCreate) -> EmergencyContact:
        """Tao lien he khan cap moi."""
        return await self.repo.create(data.model_dump())
    
    async def update_contact(
        self,
        contact_id: int,
        data: EmergencyContactUpdate,
    ) -> EmergencyContact | None:
        """Cap nhat lien he khan cap."""
        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(contact_id, update_data)
    
    async def delete_contact(self, contact_id: int) -> bool:
        """Xoa lien he khan cap."""
        return await self.repo.delete(contact_id)
    
    async def deactivate_contact(self, contact_id: int) -> EmergencyContact | None:
        """Vo hieu hoa lien he (thay vi xoa)."""
        return await self.repo.update(contact_id, {"is_active": False})
