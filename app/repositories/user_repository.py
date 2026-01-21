"""
Repository cho User va cac Profile.
"""
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, StudentProfile, TeacherProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository quan ly User."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def get_by_id_with_profiles(self, id: int) -> User | None:
        """
        Lay user kem theo cac profile.
        
        Args:
            id: User ID
            
        Returns:
            User voi student_profile va teacher_profile da load
        """
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.teacher_profile),
                selectinload(User.role),
                selectinload(User.school),
            )
            .where(User.id == id)
            .where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> User | None:
        """
        Tim user theo ten dang nhap.
        
        Args:
            username: Ten dang nhap
            
        Returns:
            User instance hoac None
        """
        result = await self.session.execute(
            select(User)
            .where(User.username == username)
            .where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> User | None:
        """
        Tim user theo email.
        
        Args:
            email: Dia chi email
            
        Returns:
            User instance hoac None
        """
        result = await self.session.execute(
            select(User)
            .where(User.email == email)
            .where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def get_by_username_or_email(self, identifier: str) -> User | None:
        """
        Tim user theo username hoac email.
        Dung cho login flow.
        
        Args:
            identifier: Username hoac email
            
        Returns:
            User instance hoac None
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role))
            .where(
                and_(
                    or_(
                        User.username == identifier,
                        User.email == identifier,
                    ),
                    User.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_active_user_by_id(self, user_id: int) -> User | None:
        """
        Lay user active (khong bi xoa, status = ACTIVE).
        Dung cho authentication.
        
        Args:
            user_id: User ID
            
        Returns:
            User neu active, None neu khong
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role))
            .where(
                and_(
                    User.id == user_id,
                    User.status == "ACTIVE",
                    User.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: int) -> bool:
        """
        Cap nhat thoi gian dang nhap cuoi.
        
        Args:
            user_id: User ID
            
        Returns:
            True neu thanh cong
        """
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.session.commit()
            return True
        return False
    
    async def update_password_hash(self, user_id: int, password_hash: str) -> bool:
        """
        Cap nhat password hash.
        
        Args:
            user_id: User ID
            password_hash: Password da hash
            
        Returns:
            True neu thanh cong
        """
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = password_hash
            await self.session.commit()
            return True
        return False
    
    async def list_by_school_and_role(
        self,
        school_id: int,
        role_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """
        Lay danh sach user theo truong va vai tro.
        
        Args:
            school_id: ID truong hoc
            role_id: ID vai tro (tuy chon)
            skip: So ban ghi bo qua
            limit: So ban ghi toi da
            
        Returns:
            Danh sach user
        """
        query = select(User).where(
            and_(
                User.school_id == school_id,
                User.deleted_at.is_(None),
                User.status == "ACTIVE",
            )
        )
        
        if role_id:
            query = query.where(User.role_id == role_id)
        
        result = await self.session.execute(
            query.offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_by_school(self, school_id: int) -> int:
        """Dem so user trong truong."""
        result = await self.session.execute(
            select(func.count(User.id)).where(
                and_(
                    User.school_id == school_id,
                    User.deleted_at.is_(None),
                )
            )
        )
        return result.scalar() or 0


class StudentProfileRepository(BaseRepository[StudentProfile]):
    """Repository quan ly StudentProfile."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(StudentProfile, session)
    
    async def get_by_user_id(self, user_id: int) -> StudentProfile | None:
        """Tim profile theo user ID."""
        result = await self.session.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_class(
        self,
        class_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[StudentProfile]:
        """Lay danh sach hoc sinh trong lop."""
        result = await self.session.execute(
            select(StudentProfile)
            .options(selectinload(StudentProfile.user))
            .where(StudentProfile.class_id == class_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class TeacherProfileRepository(BaseRepository[TeacherProfile]):
    """Repository quan ly TeacherProfile."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(TeacherProfile, session)
    
    async def get_by_user_id(self, user_id: int) -> TeacherProfile | None:
        """Tim profile theo user ID."""
        result = await self.session.execute(
            select(TeacherProfile).where(TeacherProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

