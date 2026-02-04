"""Sync endpoints for weekly data synchronization.

Admin only endpoints - require admin role.
Run this every Sunday evening to sync data for the next 7 days.
Can also be triggered manually.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from src.auth import ADMIN_RESPONSES, AdminUser
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.data.sources.football_data import COMPETITIONS, get_football_data_client
from src.db import get_db_context
from src.db.services.match_service import MatchService, StandingService
from src.db.services.prediction_service import PredictionService
from src.db.services.stats_service import StatsService, SyncServiceAsync

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sync_form_from_standings() -> int:
    """
    Copy form data from standings to teams table.

    Updates teams.form and teams.form_score from standings.
    form_score = points from form string / 15 (max points for 5 matches)
    """
    try:
        with get_db_context() as db:
            query = text("""
                UPDATE teams t
                SET
                    form = s.form,
                    form_score = (
                        -- Calculate form score: W=3, D=1, L=0, max=15
                        (LENGTH(s.form) - LENGTH(REPLACE(s.form, 'W', ''))) * 3 +
                        (LENGTH(s.form) - LENGTH(REPLACE(s.form, 'D', ''))) * 1
                    ) / 15.0,
                    updated_at = NOW()
                FROM standings s
                WHERE t.id = s.team_id
                    AND s.form IS NOT NULL
                    AND s.form != ''
            """)
            result = db.execute(query)
            db.commit()
            updated = result.rowcount
            logger.info(f"Synced form data for {updated} teams from standings")
            return updated
    except Exception as e:
        logger.error(f"Failed to sync form from standings: {e}")
        return 0


async def _recalculate_all_team_stats() -> int:
    """
    Recalculate all team stats from match history.

    Updates teams table with:
    - avg_goals_scored_home/away (attack strength)
    - avg_goals_conceded_home/away (defense weakness)
    - rest_days (days since last match)
    - fixture_congestion (matches in last 14 days / 4)
    - last_match_date

    Returns number of teams updated.
    """
    try:
        with get_db_context() as db:
            # Calculate and update all stats for teams with finished matches
            query = text("""
                WITH home_stats AS (
                    SELECT
                        home_team_id as team_id,
                        AVG(home_score) as avg_scored,
                        AVG(away_score) as avg_conceded,
                        COUNT(*) as matches
                    FROM matches
                    WHERE status = 'FINISHED' AND home_score IS NOT NULL
                    GROUP BY home_team_id
                ),
                away_stats AS (
                    SELECT
                        away_team_id as team_id,
                        AVG(away_score) as avg_scored,
                        AVG(home_score) as avg_conceded,
                        COUNT(*) as matches
                    FROM matches
                    WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    GROUP BY away_team_id
                ),
                last_match AS (
                    -- Get last match date for each team
                    SELECT team_id, MAX(match_date) as last_date
                    FROM (
                        SELECT home_team_id as team_id, match_date FROM matches WHERE status = 'FINISHED'
                        UNION ALL
                        SELECT away_team_id as team_id, match_date FROM matches WHERE status = 'FINISHED'
                    ) all_matches
                    GROUP BY team_id
                ),
                congestion AS (
                    -- Count matches in last 14 days
                    SELECT team_id, COUNT(*) as matches_14d
                    FROM (
                        SELECT home_team_id as team_id, match_date FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                        UNION ALL
                        SELECT away_team_id as team_id, match_date FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                    ) recent
                    GROUP BY team_id
                ),
                elo_calc AS (
                    -- Simple ELO: start at 1500, +/- based on results
                    -- Win vs higher = +20, Win vs lower = +10, Loss = opposite
                    SELECT
                        team_id,
                        1500 + SUM(elo_change) as new_elo
                    FROM (
                        SELECT
                            home_team_id as team_id,
                            CASE
                                WHEN home_score > away_score THEN 15  -- Win
                                WHEN home_score = away_score THEN 0   -- Draw
                                ELSE -15                               -- Loss
                            END as elo_change
                        FROM matches WHERE status = 'FINISHED' AND home_score IS NOT NULL
                        UNION ALL
                        SELECT
                            away_team_id as team_id,
                            CASE
                                WHEN away_score > home_score THEN 15  -- Win
                                WHEN away_score = home_score THEN 0   -- Draw
                                ELSE -15                               -- Loss
                            END as elo_change
                        FROM matches WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    ) results
                    GROUP BY team_id
                )
                UPDATE teams t
                SET
                    avg_goals_scored_home = COALESCE(h.avg_scored, 1.0),
                    avg_goals_conceded_home = COALESCE(h.avg_conceded, 1.0),
                    avg_goals_scored_away = COALESCE(a.avg_scored, 1.0),
                    avg_goals_conceded_away = COALESCE(a.avg_conceded, 1.0),
                    last_match_date = lm.last_date,
                    rest_days = COALESCE(EXTRACT(DAY FROM NOW() - lm.last_date)::INTEGER, 7),
                    fixture_congestion = LEAST(1.0, COALESCE(c.matches_14d, 0) / 4.0),
                    elo_rating = COALESCE(e.new_elo, 1500),
                    updated_at = NOW()
                FROM home_stats h
                FULL OUTER JOIN away_stats a ON h.team_id = a.team_id
                LEFT JOIN last_match lm ON COALESCE(h.team_id, a.team_id) = lm.team_id
                LEFT JOIN congestion c ON COALESCE(h.team_id, a.team_id) = c.team_id
                LEFT JOIN elo_calc e ON COALESCE(h.team_id, a.team_id) = e.team_id
                WHERE t.id = COALESCE(h.team_id, a.team_id)
            """)

            result = db.execute(query)
            db.commit()

            updated_count = result.rowcount
            logger.info(f"Recalculated stats for {updated_count} teams")
            return updated_count

    except Exception as e:
        logger.error(f"Failed to recalculate team stats: {e}")
        return 0


class SyncResponse(BaseModel):
    """Response for sync operations."""

    status: str
    message: str
    matches_synced: int = 0
    standings_synced: int = 0
    errors: list[str] = []


class DbStatsResponse(BaseModel):
    """Database statistics response."""

    total_matches: int
    competitions_with_standings: int
    last_match_sync: str | None
    last_standings_sync: str | None


async def _sync_matches_for_week(
    days: int = 7, include_past_days: int = 3
) -> tuple[int, list[str]]:
    """Sync matches for the next N days and past N days for score verification."""
    client = get_football_data_client()
    today = date.today()
    # Include past days to get finished match scores
    date_from = today - timedelta(days=include_past_days)
    date_to = today + timedelta(days=days)

    total_synced = 0
    errors = []

    # Sync each competition separately to stay within rate limits
    for comp_code in COMPETITIONS.keys():
        try:
            logger.info(f"Syncing matches for {comp_code} ({date_from} to {date_to})...")
            matches = await client.get_matches(
                competition=comp_code,
                date_from=date_from,
                date_to=date_to,
            )

            # Convert to dict for storage
            matches_dict = [m.model_dump() for m in matches]
            synced = await MatchService.save_matches(matches_dict)
            total_synced += synced
            logger.info(f"Synced {synced} matches for {comp_code}")

        except RateLimitError as e:
            error_msg = f"Rate limit for {comp_code}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            # Wait a bit and continue with next competition
            import asyncio

            await asyncio.sleep(15)  # Wait 15 seconds before next request

        except FootballDataAPIError as e:
            error_msg = f"API error for {comp_code}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error for {comp_code}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return total_synced, errors


async def _sync_all_standings() -> tuple[int, list[str]]:
    """Sync standings for all competitions."""
    client = get_football_data_client()
    total_synced = 0
    errors = []

    # Only sync league competitions (not CL/EL for standings)
    league_competitions = ["PL", "PD", "BL1", "SA", "FL1"]

    for comp_code in league_competitions:
        try:
            logger.info(f"Syncing standings for {comp_code}...")

            # Get raw standings data from API
            data = await client._request("GET", f"/competitions/{comp_code}/standings")

            for standing_group in data.get("standings", []):
                if standing_group.get("type") == "TOTAL":
                    standings_list = standing_group.get("table", [])
                    synced = await StandingService.save_standings(comp_code, standings_list)
                    total_synced += synced
                    break

            logger.info(f"Synced standings for {comp_code}")

        except RateLimitError as e:
            error_msg = f"Rate limit for {comp_code} standings: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            import asyncio

            await asyncio.sleep(15)

        except FootballDataAPIError as e:
            error_msg = f"API error for {comp_code} standings: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error for {comp_code} standings: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return total_synced, errors


@router.post("/weekly", response_model=SyncResponse, responses=ADMIN_RESPONSES)
async def sync_weekly_data(
    user: AdminUser,
    background_tasks: BackgroundTasks,
    days: int = Query(7, ge=1, le=14, description="Number of days to sync"),
    include_standings: bool = Query(True, description="Also sync standings"),
) -> SyncResponse:
    """
    Trigger weekly data synchronization.

    This should be called every Sunday evening (e.g., via cron job).
    Syncs matches for the next 7 days and all standings.

    Cron example: 0 20 * * 0 curl -X POST https://api/sync/weekly
    """
    try:
        await SyncServiceAsync.log_sync("weekly", "running", 0)

        # Sync matches
        matches_synced, match_errors = await _sync_matches_for_week(days)

        # Sync standings if requested
        standings_synced = 0
        standings_errors: list[str] = []
        if include_standings:
            standings_synced, standings_errors = await _sync_all_standings()

        # Automatically verify predictions for finished matches
        verified_count = 0
        try:
            verified_count = await PredictionService.verify_all_finished()
            logger.info(f"Auto-verified {verified_count} predictions")
        except Exception as e:
            logger.warning(f"Failed to verify predictions: {e}")

        # Recalculate team stats from match history
        teams_updated = 0
        try:
            teams_updated = await _recalculate_all_team_stats()
            logger.info(f"Recalculated stats for {teams_updated} teams")
        except Exception as e:
            logger.warning(f"Failed to recalculate team stats: {e}")

        # Sync form data from standings to teams
        form_synced = 0
        try:
            form_synced = await _sync_form_from_standings()
            logger.info(f"Synced form for {form_synced} teams")
        except Exception as e:
            logger.warning(f"Failed to sync form data: {e}")

        all_errors = match_errors + standings_errors
        status = "success" if not all_errors else "partial"

        await SyncServiceAsync.log_sync(
            "weekly",
            status,
            matches_synced + standings_synced,
            "; ".join(all_errors) if all_errors else None,
        )

        return SyncResponse(
            status=status,
            message=f"Synchronized {matches_synced} matches, {standings_synced} standings, {teams_updated} team stats, {form_synced} form scores",
            matches_synced=matches_synced,
            standings_synced=standings_synced,
            errors=all_errors,
        )

    except Exception as e:
        error_msg = str(e)
        await SyncServiceAsync.log_sync("weekly", "error", 0, error_msg)
        raise HTTPException(status_code=500, detail=f"Sync failed: {error_msg}")


@router.post("/matches", response_model=SyncResponse, responses=ADMIN_RESPONSES)
async def sync_matches_only(
    user: AdminUser,
    days: int = Query(7, ge=1, le=14, description="Number of days to sync"),
) -> SyncResponse:
    """Sync only matches (no standings)."""
    try:
        matches_synced, errors = await _sync_matches_for_week(days)

        # Automatically verify predictions for finished matches
        verified_count = 0
        try:
            verified_count = await PredictionService.verify_all_finished()
            logger.info(f"Auto-verified {verified_count} predictions")
        except Exception as e:
            logger.warning(f"Failed to verify predictions: {e}")

        status = "success" if not errors else "partial"
        await SyncServiceAsync.log_sync(
            "matches", status, matches_synced, "; ".join(errors) if errors else None
        )

        return SyncResponse(
            status=status,
            message=f"Synchronized {matches_synced} matches, verified {verified_count} predictions",
            matches_synced=matches_synced,
            errors=errors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/standings", response_model=SyncResponse, responses=ADMIN_RESPONSES)
async def sync_standings_only(user: AdminUser) -> SyncResponse:
    """Sync only standings (no matches)."""
    try:
        standings_synced, errors = await _sync_all_standings()

        status = "success" if not errors else "partial"
        await SyncServiceAsync.log_sync(
            "standings", status, standings_synced, "; ".join(errors) if errors else None
        )

        return SyncResponse(
            status=status,
            message=f"Synchronized {standings_synced} standings",
            standings_synced=standings_synced,
            errors=errors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=DbStatsResponse, responses=ADMIN_RESPONSES)
async def get_sync_status(user: AdminUser) -> DbStatsResponse:
    """Get database sync status and statistics."""
    stats = await StatsService.get_db_stats()
    return DbStatsResponse(**stats)


@router.get("/last", responses=ADMIN_RESPONSES)
async def get_last_sync_info(
    user: AdminUser,
    sync_type: str = Query("weekly", description="Type of sync to check"),
) -> dict[str, Any]:
    """Get info about the last successful sync."""
    last = await SyncServiceAsync.get_last_sync(sync_type)
    if last:
        return last
    return {"message": f"No successful {sync_type} sync found"}


@router.post("/verify-predictions", response_model=SyncResponse, responses=ADMIN_RESPONSES)
async def sync_and_verify_predictions(
    user: AdminUser,
    past_days: int = Query(7, ge=1, le=30, description="Days to look back for finished matches"),
) -> SyncResponse:
    """
    Sync recent finished matches and verify predictions against actual results.

    This endpoint:
    1. Fetches matches from the past N days to get final scores
    2. Updates local database with match results
    3. Verifies predictions against actual outcomes
    """
    try:
        client = get_football_data_client()
        today = date.today()
        date_from = today - timedelta(days=past_days)

        total_synced = 0
        verified_count = 0
        errors = []

        # Sync each competition
        for comp_code in COMPETITIONS.keys():
            try:
                logger.info(f"Syncing finished matches for {comp_code}...")
                matches = await client.get_matches(
                    competition=comp_code,
                    date_from=date_from,
                    date_to=today,
                    status="FINISHED",
                )

                # Save to database
                matches_dict = [m.model_dump() for m in matches]
                synced = await MatchService.save_matches(matches_dict)
                total_synced += synced

            except RateLimitError as e:
                error_msg = f"Rate limit for {comp_code}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                import asyncio

                await asyncio.sleep(15)

            except Exception as e:
                error_msg = f"Error syncing {comp_code}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Now verify predictions
        verified_count = await PredictionService.verify_all_finished()

        status = "success" if not errors else "partial"
        await SyncServiceAsync.log_sync("verify", status, verified_count)

        return SyncResponse(
            status=status,
            message=f"Synced {total_synced} finished matches, verified {verified_count} predictions",
            matches_synced=total_synced,
            standings_synced=verified_count,  # Reusing field for verified count
            errors=errors,
        )

    except Exception as e:
        error_msg = str(e)
        await SyncServiceAsync.log_sync("verify", "error", 0, error_msg)
        raise HTTPException(status_code=500, detail=f"Verification failed: {error_msg}")
