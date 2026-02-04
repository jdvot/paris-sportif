"""Database connection and session management.

Uses SQLAlchemy 2.0 async patterns with connection pooling and
proper transaction handling.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import settings

# Determine pool class based on environment
# Use NullPool for serverless/testing, QueuePool (default) for production
_pool_class = NullPool if settings.app_env == "test" else None

# Create async engine with optimized settings
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=5 if _pool_class is None else 0,
    max_overflow=10 if _pool_class is None else 0,
    poolclass=_pool_class,
)

# Session factory - used directly and by Unit of Work
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
    autocommit=False,
    autoflush=False,  # Manual flush for better control
)

# Alias for Unit of Work compatibility
async_session_factory = async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting database sessions.

    For use outside of FastAPI dependency injection, e.g., in background tasks.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(Team))
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables."""
    from src.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
