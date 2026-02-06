"""Database connection and session management.

Uses SQLAlchemy 2.0 async patterns with connection pooling and
proper transaction handling. Also provides sync access for background tasks.
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import settings


def _get_async_database_url(url: str) -> str:
    """Convert sync database URL to async format.

    - postgresql:// -> postgresql+asyncpg://
    - sqlite:// -> sqlite+aiosqlite://
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


# Convert URL to async format if needed
_database_url = _get_async_database_url(settings.database_url)

# Check if using SQLite (for tests)
_is_sqlite = _database_url.startswith("sqlite")

# Determine pool class based on environment
# Use NullPool for serverless/testing/SQLite, QueuePool (default) for production PostgreSQL
_pool_class = NullPool if (settings.app_env == "test" or _is_sqlite) else None  # type: ignore[comparison-overlap]

# Create async engine with optimized settings
# SQLite doesn't support pool_size/max_overflow, so we skip them
_engine_kwargs: dict[str, Any] = {
    "echo": settings.debug,
    "poolclass": _pool_class,
}

if not _is_sqlite:
    # PostgreSQL-specific pool settings (optimized for 1 CPU, 2GB RAM)
    _engine_kwargs.update(
        {
            "pool_pre_ping": True,  # Verify connections before use
            "pool_size": 3 if _pool_class is None else 0,
            "max_overflow": 5 if _pool_class is None else 0,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }
    )

engine = create_async_engine(_database_url, **_engine_kwargs)

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


# =============================================================================
# Sync Database Access (for background tasks that can't use async)
# =============================================================================

# Create sync engine for use in background tasks
_sync_database_url = settings.database_url  # Use original URL (not async)
_sync_engine = create_engine(
    _sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    pool_recycle=3600,
)

# Sync session factory
_sync_session_maker = sessionmaker(
    bind=_sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Sync context manager for database sessions.

    For use in background tasks or sync code that needs database access.

    Usage:
        with get_db_context() as db:
            result = db.execute(text("SELECT * FROM teams"))
            db.commit()
    """
    session = _sync_session_maker()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
