"""Background scheduler for automatic tasks.

Runs:
- Weekly match/standings sync (Sundays 20:00 UTC)
- Daily sync check (every day 06:00 UTC for score updates)
- Team stats recalculation (after each sync)
"""

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def sync_weekly_task():
    """Weekly sync: matches + standings + team stats."""
    from src.api.routes.sync import (
        _recalculate_all_team_stats,
        _sync_all_standings,
        _sync_matches_for_week,
    )
    from src.db.services.prediction_service import PredictionService
    from src.db.services.stats_service import SyncServiceAsync

    logger.info("Starting weekly automatic sync...")

    try:
        # Sync matches for next 7 days + past 3 days
        matches_synced, match_errors = await _sync_matches_for_week(days=7, include_past_days=3)
        logger.info(f"Synced {matches_synced} matches")

        # Sync standings
        standings_synced, standings_errors = await _sync_all_standings()
        logger.info(f"Synced {standings_synced} standings")

        # Verify predictions
        verified = await PredictionService.verify_all_finished()
        logger.info(f"Verified {verified} predictions")

        # Recalculate team stats
        teams_updated = await _recalculate_all_team_stats()
        logger.info(f"Updated stats for {teams_updated} teams")

        # Log sync
        all_errors = match_errors + standings_errors
        status = "success" if not all_errors else "partial"
        await SyncServiceAsync.log_sync("weekly_auto", status, matches_synced + standings_synced)

        logger.info(
            f"Weekly sync complete: {matches_synced} matches, "
            f"{standings_synced} standings, {teams_updated} teams"
        )

    except Exception as e:
        logger.error(f"Weekly sync failed: {e}")


async def generate_daily_picks_task():
    """Daily task: generate predictions for today's matches at 09:00 UTC."""
    from src.db.services.prediction_service import PredictionService

    logger.info("Starting daily picks generation...")

    try:
        # Generate daily picks for today
        picks = await PredictionService.generate_daily_picks()
        logger.info(f"Daily picks generated: {len(picks)} picks for today")

    except Exception as e:
        logger.error(f"Daily picks generation failed: {e}")


async def sync_daily_scores_task():
    """Daily task: sync finished match scores."""
    from src.api.routes.sync import _recalculate_all_team_stats
    from src.core.exceptions import FootballDataAPIError, RateLimitError
    from src.data.sources.football_data import COMPETITIONS, get_football_data_client
    from src.db.services.match_service import MatchService
    from src.db.services.prediction_service import PredictionService

    logger.info("Starting daily score sync...")

    try:
        client = get_football_data_client()
        today = date.today()
        date_from = today - timedelta(days=3)

        total_synced = 0

        for comp_code in COMPETITIONS.keys():
            try:
                matches = await client.get_matches(
                    competition=comp_code,
                    date_from=date_from,
                    date_to=today,
                    status="FINISHED",
                )
                matches_dict = [m.model_dump() for m in matches]
                synced = await MatchService.save_matches(matches_dict)
                total_synced += synced
            except (RateLimitError, FootballDataAPIError) as e:
                logger.warning(f"Error syncing {comp_code}: {e}")
                continue

        # Verify predictions
        verified = await PredictionService.verify_all_finished()

        # Update team stats
        teams_updated = await _recalculate_all_team_stats()

        logger.info(
            f"Daily sync complete: {total_synced} matches, "
            f"{verified} verified, {teams_updated} teams updated"
        )

    except Exception as e:
        logger.error(f"Daily sync failed: {e}")


def init_scheduler():
    """Initialize and start the background scheduler."""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler

    scheduler = AsyncIOScheduler()

    # Weekly sync: Sundays at 20:00 UTC
    scheduler.add_job(
        sync_weekly_task,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_sync",
        replace_existing=True,
        name="Weekly match & standings sync",
    )

    # Daily score sync: Every day at 06:00 UTC
    scheduler.add_job(
        sync_daily_scores_task,
        CronTrigger(hour=6, minute=0),
        id="daily_sync",
        replace_existing=True,
        name="Daily score updates",
    )

    # Daily picks generation: Every day at 09:00 UTC
    scheduler.add_job(
        generate_daily_picks_task,
        CronTrigger(hour=9, minute=0),
        id="daily_picks",
        replace_existing=True,
        name="Daily picks generation",
    )

    scheduler.start()
    logger.info("Background scheduler started")
    logger.info("  - Weekly sync: Sundays 20:00 UTC")
    logger.info("  - Daily sync: Every day 06:00 UTC")
    logger.info("  - Daily picks: Every day 09:00 UTC")

    return scheduler


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown complete")


def get_scheduler_status() -> dict:
    """Get scheduler status and next run times."""
    if not scheduler:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
        )

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
