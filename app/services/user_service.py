"""
Service cho User - Xu ly logic nghiep vu lien quan den nguoi dung.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import (
    UserRepository,
    StudentProfileRepository,
    TeacherProfileRepository,
)
from app.repositories.role_repository import RoleRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    Service xu ly cac nghiep vu lien quan den User.
    Dieu phoi giua cac repository, thuc thi business rules.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Khoi tao service voi database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.student_profile_repo = StudentProfileRepository(session)
        self.teacher_profile_repo = TeacherProfileRepository(session)
        self.role_repo = RoleRepository(session)
    
    async def get_user(self, user_id: int) -> User | None:
        """Lay thong tin user theo ID."""
        return await self.user_repo.get_by_id_with_profiles(user_id)
    
    async def get_user_by_username(self, username: str) -> User | None:
        """Lay user theo ten dang nhap."""
        return await self.user_repo.get_by_username(username)
    
    async def create_user_with_profile(self, data: UserCreate) -> User:
        """
        Tao user moi kem profile tuong ung.
        
        Quy tac:
        - Neu role la STUDENT va co student_profile -> tao StudentProfile
        - Neu role la TEACHER/COUNSELOR va co teacher_profile -> tao TeacherProfile
        
        Args:
            data: Du lieu tao user
            
        Returns:
            User da tao (kem profile neu co)
        """
        # Kiem tra username da ton tai chua
        if data.username:
            existing = await self.user_repo.get_by_username(data.username)
            if existing:
                raise ValueError(f"Username '{data.username}' da ton tai")
        
        # Hash password (TODO: su dung bcrypt trong thuc te)
        password_hash = f"hashed_{data.password}"  # Placeholder
        
        # Tao user
        user_data = data.model_dump(exclude={"password", "student_profile", "teacher_profile"})
        user_data["password_hash"] = password_hash
        
        user = await self.user_repo.create(user_data)
        
        # Tao profile neu co
        role = await self.role_repo.get_by_id(data.role_id)
        
        if role and role.code == "STUDENT" and data.student_profile:
            profile_data = data.student_profile.model_dump()
            profile_data["user_id"] = user.id
            await self.student_profile_repo.create(profile_data)
        
        elif role and role.code in ("TEACHER", "COUNSELOR") and data.teacher_profile:
            profile_data = data.teacher_profile.model_dump()
            profile_data["user_id"] = user.id
            await self.teacher_profile_repo.create(profile_data)
        
        # Refresh de load relationships
        return await self.user_repo.get_by_id_with_profiles(user.id)
    
    async def update_user(self, user_id: int, data: UserUpdate) -> User | None:
        """Cap nhat thong tin user."""
        update_data = data.model_dump(exclude_unset=True, exclude={"password"})
        
        # Hash password moi neu co
        if data.password:
            update_data["password_hash"] = f"hashed_{data.password}"
        
        return await self.user_repo.update(user_id, update_data)
    
    async def list_users_by_school(
        self,
        school_id: int,
        role_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Lay danh sach user theo truong va vai tro."""
        return await self.user_repo.list_by_school_and_role(
            school_id, role_id, skip, limit
        )
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Xoa user (soft delete).
        Thay vi xoa han, danh dau deleted_at.
        """
        from datetime import datetime
        return await self.user_repo.update(user_id, {
            "deleted_at": datetime.utcnow(),
            "status": "DELETED",
        }) is not None
