"""Admin dashboard endpoints.

Provides endpoints for admin-only operations and statistics.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser
from src.data.quality_monitor import AlertLevel, run_quality_check, send_slack_alert
from src.db.services.stats_service import StatsService
from src.notifications.alert_scheduler import get_alert_scheduler
from src.notifications.push_service import PushPayload, get_push_service

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
    # Get database stats
    db_stats = await StatsService.get_db_stats()

    # TODO: Fetch real user stats from Supabase admin API
    # For now, return placeholder data combined with real DB stats
    return AdminStatsResponse(
        total_users=0,  # Would come from Supabase
        premium_users=0,  # Would come from Supabase
        total_predictions=0,  # Would come from predictions table
        success_rate=0.0,  # Would be calculated from verified predictions
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
    # TODO: Implement actual user listing from Supabase admin API
    # For now, return empty list
    return UserListResponse(
        users=[],
        total=0,
        page=page,
        per_page=per_page,
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

    # TODO: Implement actual role update via Supabase admin API
    return {
        "status": "success",
        "message": f"Role updated to {role}",
        "user_id": user_id,
    }


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
        raise HTTPException(status_code=500, detail=f"Alert check failed: {str(e)}")


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


@router.post("/verify-predictions", response_model=VerifyPredictionsResponse, responses=ADMIN_RESPONSES)
async def verify_all_predictions(user: AdminUser) -> VerifyPredictionsResponse:
    """
    Force verification of all unverified predictions.

    Checks all finished matches with predictions and verifies
    if the prediction was correct.
    Admin role required.
    """
    from src.db.services.prediction_service import PredictionService
    from src.db.repositories import get_uow

    try:
        # Get count of unverified before
        async with get_uow() as uow:
            unverified_matches = await uow.matches.get_finished_unverified()
            total_unverified = len(unverified_matches)

        # Run verification
        verified_count = await PredictionService.verify_all_finished()

        # Get count of already verified
        async with get_uow() as uow:
            from sqlalchemy import select, func
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
