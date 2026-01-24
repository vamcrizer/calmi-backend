"""
Cau hinh ket noi database PostgreSQL voi async SQLAlchemy.
Cung cap session maker va dependency injection cho FastAPI.

OPTIMIZED: Connection pooling for better performance.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# OPTIMIZED: Async engine với connection pool settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # Connection pool optimization
    pool_size=10,  # Base pool size
    max_overflow=20,  # Extra connections when pool is full
    pool_pre_ping=True,  # Check connection health before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Wait max 30s for connection
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
