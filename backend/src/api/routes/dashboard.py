"""Dashboard API routes for user statistics and ROI tracking."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.supabase_auth import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    days: int = Query(30, ge=7, le=365),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get user prediction statistics and ROI."""
    # TODO: PAR-142 - Implement user stats using UserBet and UserStats models
    # For now, return demo stats as the user_predictions table migration is pending
    return _get_demo_stats(days)


def _get_demo_stats(days: int) -> dict[str, Any]:
    """Return demo statistics when no database connection."""
    return {
        "period_days": days,
        "summary": {
            "total_predictions": 47,
            "won": 28,
            "lost": 15,
            "pending": 4,
            "win_rate": 65.1,
            "roi": 12.5,
            "total_stake": 470.0,
            "total_return": 528.75,
            "profit": 58.75,
        },
        "by_competition": [
            {"competition": "Premier League", "total": 18, "won": 12, "lost": 6, "win_rate": 66.7},
            {"competition": "Ligue 1", "total": 12, "won": 7, "lost": 5, "win_rate": 58.3},
            {"competition": "La Liga", "total": 9, "won": 5, "lost": 4, "win_rate": 55.6},
            {"competition": "Serie A", "total": 8, "won": 4, "lost": 0, "win_rate": 100.0},
        ],
        "roi_history": [
            {"week": "2026-01-06", "roi": 5.2, "cumulative_profit": 15.0},
            {"week": "2026-01-13", "roi": 8.1, "cumulative_profit": 32.0},
            {"week": "2026-01-20", "roi": 6.5, "cumulative_profit": 28.0},
            {"week": "2026-01-27", "roi": 12.5, "cumulative_profit": 58.75},
        ],
        "recent_predictions": [],
    }


@router.get("/export")
async def export_user_data(
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Export user prediction data."""
    # For now, return a placeholder
    return {
        "message": "Export feature coming soon",
        "format": format,
    }
