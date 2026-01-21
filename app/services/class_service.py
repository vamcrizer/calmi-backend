"""
Service cho Class - Xu ly logic nghiep vu lien quan den lop hoc.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class
from app.repositories.class_repository import ClassRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.class_ import ClassCreate, ClassUpdate


class ClassService:
    """Service xu ly cac nghiep vu lien quan den Class."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.class_repo = ClassRepository(session)
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
    
    async def get_class(self, class_id: int) -> Class | None:
        """Lay thong tin lop kem giao vien chu nhiem."""
        return await self.class_repo.get_by_id_with_teacher(class_id)
    
    async def list_classes_by_school(
        self,
        school_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Class]:
        """Lay danh sach lop trong truong."""
        return await self.class_repo.list_by_school(school_id, skip, limit)
    
    async def create_class(self, data: ClassCreate) -> Class:
        """
        Tao lop moi.
        
        Args:
            data: Du lieu lop
            
        Returns:
            Class da tao
        """
        # Kiem tra ten lop da ton tai trong truong chua
        existing = await self.class_repo.get_by_school_and_name(
            data.school_id, data.name
        )
        if existing:
            raise ValueError(f"Lop '{data.name}' da ton tai trong truong")
        
        # Kiem tra giao vien chu nhiem neu co
        if data.homeroom_teacher_id:
            await self._validate_teacher(data.homeroom_teacher_id, data.school_id)
        
        return await self.class_repo.create(data.model_dump())
    
    async def update_class(self, class_id: int, data: ClassUpdate) -> Class | None:
        """Cap nhat thong tin lop."""
        existing = await self.class_repo.get_by_id(class_id)
        if not existing:
            return None
        
        # Kiem tra giao vien chu nhiem moi
        if data.homeroom_teacher_id:
            await self._validate_teacher(data.homeroom_teacher_id, existing.school_id)
        
        update_data = data.model_dump(exclude_unset=True)
        return await self.class_repo.update(class_id, update_data)
    
    async def assign_homeroom_teacher(
        self,
        class_id: int,
        teacher_id: int,
    ) -> Class | None:
        """
        Gan giao vien chu nhiem cho lop.
        
        Quy tac:
        - Giao vien phai co role TEACHER hoac COUNSELOR
        - Giao vien phai thuoc cung truong voi lop
        
        Args:
            class_id: ID lop
            teacher_id: ID giao vien
            
        Returns:
            Class da cap nhat
        """
        class_obj = await self.class_repo.get_by_id(class_id)
        if not class_obj:
            raise ValueError("Lop khong ton tai")
        
        await self._validate_teacher(teacher_id, class_obj.school_id)
        
        return await self.class_repo.update(class_id, {
            "homeroom_teacher_id": teacher_id
        })
    
    async def _validate_teacher(self, teacher_id: int, school_id: int) -> None:
        """
        Kiem tra giao vien hop le.
        
        Raises:
            ValueError: Neu giao vien khong hop le
        """
        teacher = await self.user_repo.get_by_id_with_profiles(teacher_id)
        if not teacher:
            raise ValueError("Giao vien khong ton tai")
        
        if teacher.school_id != school_id:
            raise ValueError("Giao vien khong thuoc truong nay")
        
        role = await self.role_repo.get_by_id(teacher.role_id)
        if not role or role.code not in ("TEACHER", "COUNSELOR"):
            raise ValueError("Nguoi dung khong phai giao vien")
    
    async def delete_class(self, class_id: int) -> bool:
        """Xoa lop."""
        return await self.class_repo.delete(class_id)
