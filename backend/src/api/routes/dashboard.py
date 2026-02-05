"""Dashboard API routes for user statistics and ROI tracking."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.supabase_auth import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    days: int = Query(30, ge=7, le=365),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get user prediction statistics and ROI.

    NOTE: This endpoint requires UserBet and UserStats models to be implemented.
    Returns HTTP 503 until backend tracking is fully implemented.
    """
    # TODO: PAR-142 - Implement user stats using UserBet and UserStats models
    # User bet tracking functionality not yet implemented
    raise HTTPException(
        status_code=503,
        detail={
            "message": "User statistics tracking not yet available. Feature in development.",
            "warning_code": "FEATURE_NOT_IMPLEMENTED",
        },
    )


@router.get("/export")
async def export_user_data(
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Export user prediction data.

    NOTE: Export functionality not yet implemented.
    Returns HTTP 503 until backend tracking is fully implemented.
    """
    raise HTTPException(
        status_code=503,
        detail={
            "message": "Export feature not yet available. Feature in development.",
            "warning_code": "FEATURE_NOT_IMPLEMENTED",
        },
    )
