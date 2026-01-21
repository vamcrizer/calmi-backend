"""
Cau hinh ket noi database PostgreSQL voi async SQLAlchemy.
Cung cap session maker va dependency injection cho FastAPI.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from app.core.config import get_settings

settings = get_settings()

# Tao async engine ket noi PostgreSQL
# echo=True de log cac cau SQL trong che do debug
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# Tao session factory
# expire_on_commit=False de tranh loi khi truy cap attribute sau commit
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection cho FastAPI.
    Cung cap mot async session cho moi request.
    Tu dong dong session sau khi request hoan thanh.
    
    Su dung:
        @router.get("/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
