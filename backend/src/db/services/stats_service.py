"""Stats service for database statistics and cache operations."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from src.db.models import CachedData, Standing
from src.db.repositories import get_uow

logger = logging.getLogger(__name__)


class StatsService:
    """Service for database statistics."""

    @staticmethod
    async def get_db_stats() -> dict[str, Any]:
        """Get database statistics.

        Replaces: src.data.database.get_db_stats()
        """
        async with get_uow() as uow:
            # Count matches
            match_count = await uow.matches.count()

            # Count distinct competitions with standings
            from sqlalchemy import distinct

            stmt = select(func.count(distinct(Standing.competition_code)))
            result = await uow._session.execute(stmt)
            standings_count = result.scalar_one()

            # Get last sync times
            last_match_sync = await uow.sync_logs.get_last_successful_sync("matches")
            last_standings_sync = await uow.sync_logs.get_last_successful_sync("standings")

            return {
                "total_matches": match_count,
                "competitions_with_standings": standings_count,
                "last_match_sync": (
                    last_match_sync.completed_at.isoformat()
                    if last_match_sync and last_match_sync.completed_at
                    else None
                ),
                "last_standings_sync": (
                    last_standings_sync.completed_at.isoformat()
                    if last_standings_sync and last_standings_sync.completed_at
                    else None
                ),
            }

    @staticmethod
    async def get_cache_status() -> list[dict[str, Any]]:
        """Get all cached items with their status."""
        async with get_uow() as uow:
            stmt = select(CachedData).order_by(CachedData.cache_type, CachedData.cache_key)
            result = await uow._session.execute(stmt)
            items = result.scalars().all()

            now = datetime.now()
            return [
                {
                    "key": item.cache_key,
                    "type": item.cache_type,
                    "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "is_expired": now > item.expires_at if item.expires_at else True,
                }
                for item in items
            ]


class SyncServiceAsync:
    """Async service for sync operations."""

    @staticmethod
    async def log_sync(
        sync_type: str,
        status: str,
        records: int,
        error: str | None = None,
    ) -> None:
        """Log a sync operation.

        Replaces: src.data.database.log_sync()
        """
        async with get_uow() as uow:
            await uow.sync_logs.create(
                sync_type=sync_type,
                status=status,
                records_synced=records,
                started_at=datetime.now(),
                completed_at=datetime.now() if status != "running" else None,
                error_message=error,
            )
            await uow.commit()

    @staticmethod
    async def get_last_sync(sync_type: str) -> dict[str, Any] | None:
        """Get last successful sync info.

        Replaces: src.data.database.get_last_sync()
        """
        async with get_uow() as uow:
            sync = await uow.sync_logs.get_last_successful_sync(sync_type)
            if not sync:
                return None
            return {
                "id": sync.id,
                "sync_type": sync.sync_type,
                "status": sync.status,
                "records_synced": sync.records_synced,
                "started_at": sync.started_at.isoformat() if sync.started_at else None,
                "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
                "error_message": sync.error_message,
            }
