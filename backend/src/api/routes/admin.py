"""Admin dashboard endpoints.

Provides endpoints for admin-only operations and statistics.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.data.quality_monitor import AlertLevel, run_quality_check, send_slack_alert
from src.data.sources.football_data import COMPETITIONS, get_football_data_client
from src.db.services.match_service import MatchService
from src.db.services.stats_service import StatsService
from src.notifications.alert_scheduler import get_alert_scheduler
from src.notifications.push_service import PushPayload, get_push_service
from src.services.supabase_admin_service import SupabaseAdminService

logger = logging.getLogger(__name__)

router = APIRouter()


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""

    total_users: int
    premium_users: int
    total_predictions: int
    success_rate: float
    # Database stats
    total_matches: int
    competitions_with_standings: int
    last_match_sync: str | None
    last_standings_sync: str | None


class UserListItem(BaseModel):
    """User list item for admin view."""

    id: str
    email: str
    role: str
    created_at: str


class UserListResponse(BaseModel):
    """User list response."""

    users: list[UserListItem]
    total: int
    page: int
    per_page: int


@router.get("/stats", response_model=AdminStatsResponse, responses=ADMIN_RESPONSES)
async def get_admin_stats(user: AdminUser) -> AdminStatsResponse:
    """
    Get admin dashboard statistics.

    Returns platform-wide statistics for the admin dashboard.
    Admin role required.
    """
    # Fetch database stats and Supabase user counts concurrently
    from src.db.services.prediction_service import PredictionService

    db_stats, user_counts, pred_stats = await asyncio.gather(
        StatsService.get_db_stats(),
        SupabaseAdminService.get_user_counts(),
        PredictionService.get_statistics(days=365),
    )

    if user_counts.get("warning"):
        logger.warning(f"Supabase user counts warning: {user_counts['warning']}")

    total_predictions = pred_stats.get("total_predictions", 0)
    correct = pred_stats.get("correct_predictions", 0)
    success_rate = (correct / total_predictions * 100) if total_predictions > 0 else 0.0

    return AdminStatsResponse(
        total_users=user_counts.get("total_users", 0),
        premium_users=user_counts.get("premium_users", 0),
        total_predictions=total_predictions,
        success_rate=round(success_rate, 1),
        total_matches=db_stats.get("total_matches", 0),
        competitions_with_standings=db_stats.get("competitions_with_standings", 0),
        last_match_sync=db_stats.get("last_match_sync"),
        last_standings_sync=db_stats.get("last_standings_sync"),
    )


@router.get("/users", response_model=UserListResponse, responses=ADMIN_RESPONSES)
async def list_users(
    user: AdminUser,
    page: int = 1,
    per_page: int = 20,
) -> UserListResponse:
    """
    List all users (admin only).

    Returns a paginated list of all users.
    Admin role required.
    """
    result = await SupabaseAdminService.list_users(page=page, per_page=per_page)

    if result.get("warning"):
        logger.warning(f"Supabase list_users warning: {result['warning']}")

    users = [UserListItem(**u) for u in result.get("users", [])]

    return UserListResponse(
        users=users,
        total=result.get("total", 0),
        page=result.get("page", page),
        per_page=result.get("per_page", per_page),
    )


@router.post("/users/{user_id}/role", responses=ADMIN_RESPONSES)
async def update_user_role(
    user: AdminUser,
    user_id: str,
    role: str,
) -> dict[str, Any]:
    """
    Update a user's role (admin only).

    Changes a user's role (free, premium, admin).
    Admin role required.
    """
    if role not in ["free", "premium", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    logger.info(
        "Role change: admin=%s target_user=%s new_role=%s",
        user.id,
        user_id,
        role,
    )

    result = await SupabaseAdminService.update_user_role(user_id, role)

    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("message", "Unknown error"))

    return result


class DataQualityCheckResponse(BaseModel):
    """Single data quality check result."""

    name: str
    status: str
    message: str
    value: float | int | str | None = None
    threshold: float | int | str | None = None
    details: dict[str, Any] = {}


class DataQualityResponse(BaseModel):
    """Complete data quality report."""

    timestamp: str
    overall_status: str
    freshness: DataQualityCheckResponse
    completeness: DataQualityCheckResponse
    range_validation: DataQualityCheckResponse
    consistency: DataQualityCheckResponse
    anomalies: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}


@router.get("/data-quality", response_model=DataQualityResponse, responses=ADMIN_RESPONSES)
async def get_data_quality_status(user: AdminUser) -> DataQualityResponse:
    """
    Get data quality status report.

    Runs comprehensive data quality checks and returns results.
    Admin role required.

    Checks include:
    - Freshness: How recently data was updated
    - Completeness: Percentage of populated fields
    - Range validation: Values within expected bounds
    - Consistency: Duplicates and conflicts
    """
    try:
        report = await run_quality_check()
        return DataQualityResponse(**report.to_dict())
    except Exception as e:
        logger.error(f"Error running data quality check: {e}")
        raise HTTPException(status_code=500, detail="Failed to run data quality check")


@router.post("/data-quality/alert", responses=ADMIN_RESPONSES)
async def trigger_data_quality_alert(
    user: AdminUser,
    force: bool = False,
) -> dict[str, Any]:
    """
    Run data quality check and send Slack alert if critical issues.

    Args:
        force: Send alert even if status is not critical

    Returns:
        Report summary and alert status
    """
    try:
        report = await run_quality_check()

        # Send alert if critical or forced
        alert_sent = False
        if report.overall_status == AlertLevel.CRITICAL or force:
            alert_sent = await send_slack_alert(report)

        return {
            "status": "success",
            "overall_status": report.overall_status.value,
            "alert_sent": alert_sent,
            "checks": {
                "freshness": report.freshness.status.value,
                "completeness": report.completeness.status.value,
                "range_validation": report.range_validation.status.value,
                "consistency": report.consistency.status.value,
            },
            "anomaly_count": len(report.anomalies),
        }
    except Exception as e:
        logger.error(f"Error in data quality alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to run data quality check")


# ============================================================================
# Notification endpoints
# ============================================================================


class NotificationRequest(BaseModel):
    """Manual notification request."""

    title: str
    body: str
    url: str = "/"
    preference_filter: str | None = None


class AlertCheckResponse(BaseModel):
    """Alert check response."""

    match_alerts: list[dict[str, Any]]
    daily_picks: dict[str, Any] | None
    timestamp: str


@router.post("/notifications/broadcast", responses=ADMIN_RESPONSES)
async def broadcast_notification(
    user: AdminUser,
    notification: NotificationRequest,
) -> dict[str, Any]:
    """
    Send a broadcast notification to all subscribed users.

    Admin role required.

    Args:
        notification: Notification content and settings
    """
    logger.info(
        "Broadcast notification triggered by admin %s: title=%s",
        user.id,
        notification.title,
    )

    push_service = get_push_service()

    payload = PushPayload(
        title=notification.title,
        body=notification.body,
        url=notification.url,
    )

    result = await push_service.broadcast_notification(
        payload=payload,
        preference=notification.preference_filter,
    )

    logger.info(
        "Broadcast complete: sent=%d, failed=%d, admin=%s",
        result["sent"],
        result["failed"],
        user.id,
    )

    return {
        "status": "success",
        "sent": result["sent"],
        "failed": result["failed"],
        "total": result["total"],
    }


@router.post(
    "/notifications/check-alerts", response_model=AlertCheckResponse, responses=ADMIN_RESPONSES
)
async def run_alert_check(user: AdminUser) -> AlertCheckResponse:
    """
    Manually trigger alert check for upcoming matches.

    Admin role required.
    Checks for matches starting within the alert window and sends notifications.
    """
    scheduler = get_alert_scheduler()

    try:
        result = await scheduler.run_alert_check()
        return AlertCheckResponse(
            match_alerts=result.get("match_alerts", []),
            daily_picks=result.get("daily_picks"),
            timestamp=result["timestamp"],
        )
    except Exception as e:
        logger.error(f"Error running alert check: {e}")
        raise HTTPException(status_code=500, detail="Alert check failed")


@router.post("/notifications/daily-picks", responses=ADMIN_RESPONSES)
async def send_daily_picks_notification(user: AdminUser) -> dict[str, Any]:
    """
    Send daily picks notification to subscribed users.

    Admin role required.
    """
    scheduler = get_alert_scheduler()

    try:
        result = await scheduler.send_daily_picks_alert()
        return {
            "status": "success",
            "sent": result.get("sent", 0),
            "already_sent": result.get("already_sent", False),
        }
    except Exception as e:
        logger.error(f"Error sending daily picks notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


# ============================================================================
# Cache management endpoints
# ============================================================================


class CacheRefreshResponse(BaseModel):
    """Cache refresh response."""

    status: str
    success: list[str]
    failed: list[str]
    timestamp: str


@router.post("/cache/refresh", response_model=CacheRefreshResponse, responses=ADMIN_RESPONSES)
async def refresh_cache(user: AdminUser) -> CacheRefreshResponse:
    """
    Refresh all cached data.

    Manually triggers the daily cache calculation:
    - Prediction statistics
    - League standings for all competitions
    - Teams data
    - Upcoming matches

    Admin role required.
    """
    from src.services.cache_service import init_cache_table, run_daily_cache_calculation

    try:
        # Ensure cache table exists (now async)
        await init_cache_table()

        # Run cache calculation
        result = await run_daily_cache_calculation()

        return CacheRefreshResponse(
            status="success",
            success=result["success"],
            failed=result["failed"],
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")


@router.get("/cache/status", responses=ADMIN_RESPONSES)
async def get_cache_status(user: AdminUser) -> dict[str, Any]:
    """
    Get cache status and expiration times.

    Admin role required.
    """
    try:
        cached_items = await StatsService.get_cache_status()

        return {
            "status": "success",
            "cached_items": cached_items,
            "total_cached": len(cached_items),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")


# ============================================================================
# Data prefill endpoints
# ============================================================================


class PrefillResponse(BaseModel):
    """Data prefill response."""

    status: str
    team_data: dict[str, int]
    elo_ratings: int
    predictions: int
    redis_cache: int
    duration_seconds: float
    timestamp: str


@router.post("/prefill", response_model=PrefillResponse, responses=ADMIN_RESPONSES)
async def run_data_prefill(user: AdminUser) -> PrefillResponse:
    """
    Run complete data prefill pipeline.

    This pre-calculates and caches all data for optimal performance:
    - Team stats (country, form, rest_days, avg_goals, ELO)
    - Predictions for upcoming matches
    - Redis cache warm-up

    Admin role required.
    """
    from src.services.data_prefill_service import DataPrefillService

    try:
        result = await DataPrefillService.run_full_prefill()

        return PrefillResponse(
            status="success",
            team_data=result["team_data"],
            elo_ratings=result["elo_ratings"],
            predictions=result["predictions"],
            redis_cache=result["redis_cache"],
            duration_seconds=result["duration_seconds"],
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error running prefill: {e}")
        raise HTTPException(status_code=500, detail=f"Prefill failed: {str(e)}")


@router.get("/data-status", responses=ADMIN_RESPONSES)
async def get_data_status(user: AdminUser) -> dict[str, Any]:
    """
    Get detailed status of all data tables.

    Shows fill rates for all important columns.
    Admin role required.
    """
    try:
        stats = await StatsService.get_detailed_data_status()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {str(e)}")


class VerifyPredictionsResponse(BaseModel):
    """Response for prediction verification."""

    status: str
    verified_count: int
    already_verified: int
    total_unverified: int
    timestamp: str


@router.post(
    "/verify-predictions", response_model=VerifyPredictionsResponse, responses=ADMIN_RESPONSES
)
async def verify_all_predictions(user: AdminUser) -> VerifyPredictionsResponse:
    """
    Force verification of all unverified predictions.

    Checks all finished matches with predictions and verifies
    if the prediction was correct.
    Admin role required.
    """
    from src.db.repositories import get_uow
    from src.db.services.prediction_service import PredictionService

    try:
        # Get count of unverified before
        async with get_uow() as uow:
            unverified_matches = await uow.matches.get_finished_unverified()
            total_unverified = len(unverified_matches)

        # Run verification
        verified_count = await PredictionService.verify_all_finished()

        # Get count of already verified
        async with get_uow() as uow:
            from sqlalchemy import func, select

            from src.db.models import PredictionResult

            result = await uow.session.execute(select(func.count(PredictionResult.id)))
            already_verified = result.scalar() or 0

        return VerifyPredictionsResponse(
            status="success",
            verified_count=verified_count,
            already_verified=already_verified,
            total_unverified=total_unverified,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error verifying predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


# ============================================================================
# Multi-season historical data sync
# ============================================================================


class TestimonialCreateRequest(BaseModel):
    """Request to create a testimonial."""

    author_name: str
    author_role: str | None = None
    content: str
    rating: int = 5
    avatar_url: str | None = None


class TestimonialCreateResponse(BaseModel):
    """Response after creating a testimonial."""

    id: int
    author_name: str
    content: str
    is_approved: bool
    created_at: str


@router.post(
    "/testimonials",
    response_model=TestimonialCreateResponse,
    responses=ADMIN_RESPONSES,
)
async def create_testimonial(
    user: AdminUser,
    payload: TestimonialCreateRequest,
) -> TestimonialCreateResponse:
    """
    Create a new testimonial (admin only).

    The testimonial is auto-approved when created by an admin.
    """
    from src.db.database import get_session
    from src.db.models import Testimonial

    async with get_session() as session:
        testimonial = Testimonial(
            author_name=payload.author_name,
            author_role=payload.author_role,
            content=payload.content,
            rating=payload.rating,
            avatar_url=payload.avatar_url,
            is_approved=True,
        )
        session.add(testimonial)
        await session.flush()
        await session.refresh(testimonial)

        return TestimonialCreateResponse(
            id=testimonial.id,
            author_name=testimonial.author_name,
            content=testimonial.content,
            is_approved=testimonial.is_approved,
            created_at=testimonial.created_at.isoformat(),
        )


# ============================================================================
# Multi-season historical data sync
# ============================================================================


class HistoricalSyncSeasonResult(BaseModel):
    """Result for a single season sync."""

    season: str
    matches_synced: int
    errors: list[str] = []


class HistoricalSyncResponse(BaseModel):
    """Response for multi-season historical sync."""

    status: str
    total_matches_synced: int
    seasons_synced: int
    per_season: list[HistoricalSyncSeasonResult]
    errors: list[str] = []
    timestamp: str


@router.post(
    "/sync/historical",
    response_model=HistoricalSyncResponse,
    responses=ADMIN_RESPONSES,
)
async def sync_historical_data(
    user: AdminUser,
    seasons: int = Query(
        3,
        ge=1,
        le=5,
        description="Number of past seasons to fetch (1-5)",
    ),
) -> HistoricalSyncResponse:
    """
    Sync historical match data for multiple past seasons.

    Fetches FINISHED matches for each past season from football-data.org
    to build a larger training dataset for ML models.

    The football-data.org API `season` parameter takes the start year
    (e.g. 2023 for the 2023-2024 season).

    WARNING: This is a long-running operation due to API rate limits
    (10 req/min). Each season requires one API call per competition.
    Expect ~7 seconds between calls.

    Args:
        seasons: Number of past seasons to fetch (default: 3, max: 5)
    """
    client = get_football_data_client()
    today = date.today()

    # Determine the current season start year
    # If we're in Aug-Dec, current season = this year
    # If we're in Jan-Jul, current season = last year
    current_season_year = today.year if today.month >= 8 else today.year - 1

    # Build list of past season years to fetch
    # e.g. if current=2025 and seasons=3: fetch 2024, 2023, 2022
    season_years = [current_season_year - i for i in range(1, seasons + 1)]

    total_matches = 0
    all_errors: list[str] = []
    per_season_results: list[HistoricalSyncSeasonResult] = []

    logger.info(
        f"Starting multi-season historical sync: "
        f"seasons={season_years}, "
        f"competitions={list(COMPETITIONS.keys())}"
    )

    for season_year in season_years:
        season_label = f"{season_year}-{season_year + 1}"
        season_matches = 0
        season_errors: list[str] = []

        logger.info(f"Syncing season {season_label}...")

        for comp_code in COMPETITIONS.keys():
            try:
                logger.info(f"Fetching {comp_code} season {season_label}...")

                matches = await client.get_matches(
                    competition=comp_code,
                    status="FINISHED",
                    season=season_year,
                )

                matches_dict = [m.model_dump() for m in matches]
                synced = await MatchService.save_matches(matches_dict)
                season_matches += synced

                logger.info(f"Synced {synced} matches for " f"{comp_code} {season_label}")

                # Respect rate limits: 10 req/min
                await asyncio.sleep(7)

            except RateLimitError as e:
                error_msg = f"Rate limit for {comp_code} {season_label}: {e}"
                logger.warning(error_msg)
                season_errors.append(error_msg)
                # Wait 60s on rate limit before continuing
                await asyncio.sleep(60)

            except FootballDataAPIError as e:
                error_msg = f"API error for {comp_code} {season_label}: {e}"
                logger.error(error_msg)
                season_errors.append(error_msg)

            except Exception as e:
                error_msg = f"Error for {comp_code} {season_label}: {e}"
                logger.error(error_msg)
                season_errors.append(error_msg)

        total_matches += season_matches
        all_errors.extend(season_errors)

        per_season_results.append(
            HistoricalSyncSeasonResult(
                season=season_label,
                matches_synced=season_matches,
                errors=season_errors,
            )
        )

        logger.info(f"Season {season_label} complete: " f"{season_matches} matches synced")

    status = "success" if not all_errors else "partial"

    logger.info(
        f"Multi-season historical sync complete: "
        f"{total_matches} total matches "
        f"across {len(season_years)} seasons"
    )

    return HistoricalSyncResponse(
        status=status,
        total_matches_synced=total_matches,
        seasons_synced=len(season_years),
        per_season=per_season_results,
        errors=all_errors,
        timestamp=datetime.now().isoformat(),
    )


class SportSyncResponse(BaseModel):
    """Response for sport-specific sync triggers."""

    status: str
    message: str
    timestamp: str


@router.post(
    "/sync/tennis",
    response_model=SportSyncResponse,
    responses=ADMIN_RESPONSES,
)
async def sync_tennis(user: AdminUser) -> SportSyncResponse:  # type: ignore[arg-type]
    """Trigger a manual tennis sync (players, matches, odds, predictions, daily picks)."""
    from src.services.tennis_sync_service import sync_tennis_matches

    logger.info(f"Admin {user.id} triggered manual tennis sync")
    try:
        await sync_tennis_matches()
        return SportSyncResponse(
            status="success",
            message="Tennis sync completed successfully",
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Manual tennis sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Tennis sync failed") from e


@router.post(
    "/sync/nba",
    response_model=SportSyncResponse,
    responses=ADMIN_RESPONSES,
)
async def sync_nba(user: AdminUser) -> SportSyncResponse:  # type: ignore[arg-type]
    """Trigger a manual NBA sync (teams, standings, games, odds, predictions, daily picks)."""
    from src.services.nba_sync_service import sync_nba_games

    logger.info(f"Admin {user.id} triggered manual NBA sync")
    try:
        await sync_nba_games()
        return SportSyncResponse(
            status="success",
            message="NBA sync completed successfully",
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Manual NBA sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="NBA sync failed") from e
