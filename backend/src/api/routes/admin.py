"""Admin dashboard endpoints.

Provides endpoints for admin-only operations and statistics.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser
from src.data.database import get_db_stats
from src.data.quality_monitor import AlertLevel, run_quality_check, send_slack_alert
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
    db_stats = get_db_stats()

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
        report = run_quality_check()
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
        report = run_quality_check()

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


@router.post("/notifications/check-alerts", response_model=AlertCheckResponse, responses=ADMIN_RESPONSES)
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
