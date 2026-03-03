"""
Cau hinh ket noi database PostgreSQL voi async SQLAlchemy.
Cung cap session maker va dependency injection cho FastAPI.

OPTIMIZED: Connection pooling + keep direct connection (port 5432 faster than pooler).
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Direct connection (port 5432) - faster than Supabase pooler for our use case
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL echo even in debug (reduces log noise)
    future=True,
    # Connection pool optimization
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Keep for connection reliability
    pool_recycle=3600,
    pool_timeout=30,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection - async session per request."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
