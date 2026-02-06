"""Sync log repository for tracking data synchronization."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SyncLog
from src.db.repositories.base import BaseRepository


class SyncLogRepository(BaseRepository[SyncLog]):
    """Repository for SyncLog operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SyncLog, session)

    async def start_sync(
        self,
        sync_type: str,
        *,
        triggered_by: str | None = None,
    ) -> SyncLog:
        """Start a new sync operation."""
        return await self.create(
            sync_type=sync_type,
            status="running",
            records_synced=0,
            started_at=datetime.now(),
            triggered_by=triggered_by,
        )

    async def complete_sync(
        self,
        sync_log: SyncLog,
        records_synced: int,
    ) -> SyncLog:
        """Mark a sync operation as completed."""
        sync_log.status = "success"
        sync_log.records_synced = records_synced
        sync_log.completed_at = datetime.now()
        await self.session.flush()
        await self.session.refresh(sync_log)
        return sync_log

    async def fail_sync(
        self,
        sync_log: SyncLog,
        error_message: str,
        *,
        error_details: str | None = None,
    ) -> SyncLog:
        """Mark a sync operation as failed."""
        sync_log.status = "failed"
        sync_log.completed_at = datetime.now()
        sync_log.error_message = error_message
        sync_log.error_details = error_details
        await self.session.flush()
        await self.session.refresh(sync_log)
        return sync_log

    async def get_last_successful_sync(self, sync_type: str) -> SyncLog | None:
        """Get the last successful sync for a type."""
        stmt = (
            select(SyncLog)
            .where(SyncLog.sync_type == sync_type, SyncLog.status == "success")
            .order_by(SyncLog.completed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return cast(SyncLog | None, result.scalar_one_or_none())

    async def get_recent_syncs(
        self,
        sync_type: str | None = None,
        *,
        limit: int = 10,
    ) -> Sequence[SyncLog]:
        """Get recent sync operations."""
        stmt = select(SyncLog)
        if sync_type:
            stmt = stmt.where(SyncLog.sync_type == sync_type)
        stmt = stmt.order_by(SyncLog.started_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return cast(Sequence[SyncLog], result.scalars().all())

    async def get_running_syncs(self) -> Sequence[SyncLog]:
        """Get currently running sync operations."""
        stmt = (
            select(SyncLog).where(SyncLog.status == "running").order_by(SyncLog.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return cast(Sequence[SyncLog], result.scalars().all())

    async def is_sync_running(self, sync_type: str) -> bool:
        """Check if a sync of the given type is currently running."""
        stmt = (
            select(SyncLog)
            .where(SyncLog.sync_type == sync_type, SyncLog.status == "running")
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_sync_stats(self, sync_type: str, *, days: int = 7) -> dict[str, Any]:
        """Get sync statistics for a type over recent days."""
        from datetime import timedelta

        from sqlalchemy import func

        cutoff = datetime.now() - timedelta(days=days)

        # Count by status
        stmt = (
            select(
                SyncLog.status,
                func.count(SyncLog.id).label("count"),
                func.sum(SyncLog.records_synced).label("total_records"),
            )
            .where(SyncLog.sync_type == sync_type, SyncLog.started_at >= cutoff)
            .group_by(SyncLog.status)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        stats = {
            "success_count": 0,
            "failed_count": 0,
            "running_count": 0,
            "total_records_synced": 0,
        }
        for row in rows:
            if row.status == "success":
                stats["success_count"] = row.count
                stats["total_records_synced"] = row.total_records or 0
            elif row.status == "failed":
                stats["failed_count"] = row.count
            elif row.status == "running":
                stats["running_count"] = row.count

        return stats
