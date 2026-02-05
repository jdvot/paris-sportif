"""Stats service for database statistics and cache operations."""

import logging
from datetime import datetime, timezone
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

            now = datetime.now(timezone.utc)
            return [
                {
                    "key": item.cache_key,
                    "type": item.cache_type,
                    "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "is_expired": (
                        now > item.expires_at.replace(tzinfo=timezone.utc)
                        if item.expires_at and item.expires_at.tzinfo is None
                        else now > item.expires_at if item.expires_at else True
                    ),
                }
                for item in items
            ]

    @staticmethod
    async def get_detailed_data_status() -> dict[str, Any]:
        """Get detailed fill rates for all important data columns."""
        from sqlalchemy import text

        async with get_uow() as uow:
            session = uow._session

            # Teams table analysis
            teams_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(country) as country,
                    COUNT(form) as form,
                    COUNT(elo_rating) as elo_rating,
                    COUNT(rest_days) as rest_days,
                    COUNT(fixture_congestion) as fixture_congestion,
                    COUNT(avg_goals_scored_home) as avg_goals_home,
                    COUNT(avg_goals_scored_away) as avg_goals_away,
                    COUNT(avg_xg_for) as xg_for,
                    COUNT(avg_xg_against) as xg_against
                FROM teams
            """))
            teams_row = teams_result.fetchone()

            # Matches table analysis
            matches_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'FINISHED') as finished,
                    COUNT(*) FILTER (WHERE status IN ('SCHEDULED', 'TIMED')) as upcoming,
                    COUNT(matchday) as matchday,
                    COUNT(home_score_ht) as ht_scores,
                    COUNT(home_xg) as xg,
                    COUNT(odds_home) as odds
                FROM matches
            """))
            matches_row = matches_result.fetchone()

            # Predictions table analysis
            predictions_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_daily_pick = true) as daily_picks,
                    COUNT(*) FILTER (WHERE llm_adjustments IS NOT NULL) as with_llm,
                    COUNT(*) FILTER (WHERE explanation IS NOT NULL) as with_explanation
                FROM predictions
            """))
            predictions_row = predictions_result.fetchone()

            # News items table analysis
            news_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_injury_news = true) as injury_news,
                    COUNT(*) FILTER (WHERE llm_analysis IS NOT NULL) as analyzed,
                    COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '7 days') as recent
                FROM news_items
            """))
            news_row = news_result.fetchone()

            # Sync log analysis
            sync_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'success') as success,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    MAX(completed_at) as last_sync
                FROM sync_log
            """))
            sync_row = sync_result.fetchone()

            # ML models analysis
            ml_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_active = true) as active,
                    COUNT(*) FILTER (WHERE model_binary IS NOT NULL) as with_binary,
                    MAX(trained_at) as last_trained
                FROM ml_models
            """))
            ml_row = ml_result.fetchone()

            # Standings table analysis
            standings_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT competition_code) as competitions,
                    COUNT(form) as with_form,
                    MAX(synced_at) as last_sync
                FROM standings
            """))
            standings_row = standings_result.fetchone()

            return {
                "teams": {
                    "total": teams_row.total if teams_row else 0,
                    "fill_rates": {
                        "country": f"{(teams_row.country / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                        "form": f"{(teams_row.form / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                        "elo_rating": f"{(teams_row.elo_rating / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                        "rest_days": f"{(teams_row.rest_days / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                        "avg_goals": f"{(teams_row.avg_goals_home / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                        "xg": f"{(teams_row.xg_for / teams_row.total * 100):.1f}%" if teams_row and teams_row.total > 0 else "0%",
                    },
                    "raw_counts": {
                        "country": teams_row.country if teams_row else 0,
                        "form": teams_row.form if teams_row else 0,
                        "elo_rating": teams_row.elo_rating if teams_row else 0,
                        "rest_days": teams_row.rest_days if teams_row else 0,
                        "xg": teams_row.xg_for if teams_row else 0,
                    }
                },
                "matches": {
                    "total": matches_row.total if matches_row else 0,
                    "finished": matches_row.finished if matches_row else 0,
                    "upcoming": matches_row.upcoming if matches_row else 0,
                    "fill_rates": {
                        "matchday": f"{(matches_row.matchday / matches_row.total * 100):.1f}%" if matches_row and matches_row.total > 0 else "0%",
                        "ht_scores": f"{(matches_row.ht_scores / matches_row.finished * 100):.1f}%" if matches_row and matches_row.finished > 0 else "0%",
                        "xg": f"{(matches_row.xg / matches_row.finished * 100):.1f}%" if matches_row and matches_row.finished > 0 else "0%",
                        "odds": f"{(matches_row.odds / matches_row.total * 100):.1f}%" if matches_row and matches_row.total > 0 else "0%",
                    }
                },
                "predictions": {
                    "total": predictions_row.total if predictions_row else 0,
                    "daily_picks": predictions_row.daily_picks if predictions_row else 0,
                    "with_llm": predictions_row.with_llm if predictions_row else 0,
                    "with_explanation": predictions_row.with_explanation if predictions_row else 0,
                },
                "news_items": {
                    "total": news_row.total if news_row else 0,
                    "injury_news": news_row.injury_news if news_row else 0,
                    "analyzed": news_row.analyzed if news_row else 0,
                    "recent_7d": news_row.recent if news_row else 0,
                },
                "sync_log": {
                    "total": sync_row.total if sync_row else 0,
                    "success": sync_row.success if sync_row else 0,
                    "failed": sync_row.failed if sync_row else 0,
                    "last_sync": (
                        sync_row.last_sync.isoformat() if sync_row and sync_row.last_sync and hasattr(sync_row.last_sync, 'isoformat')
                        else str(sync_row.last_sync) if sync_row and sync_row.last_sync else None
                    ),
                },
                "ml_models": {
                    "total": ml_row.total if ml_row else 0,
                    "active": ml_row.active if ml_row else 0,
                    "with_binary": ml_row.with_binary if ml_row else 0,
                    "last_trained": (
                        ml_row.last_trained.isoformat() if ml_row and ml_row.last_trained and hasattr(ml_row.last_trained, 'isoformat')
                        else str(ml_row.last_trained) if ml_row and ml_row.last_trained else None
                    ),
                },
                "standings": {
                    "total": standings_row.total if standings_row else 0,
                    "competitions": standings_row.competitions if standings_row else 0,
                    "with_form": standings_row.with_form if standings_row else 0,
                    "last_sync": (
                        standings_row.last_sync.isoformat() if standings_row and standings_row.last_sync and hasattr(standings_row.last_sync, 'isoformat')
                        else str(standings_row.last_sync) if standings_row and standings_row.last_sync else None
                    ),
                },
            }


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
