"""Dashboard API routes for user statistics and ROI tracking."""

import csv
import io
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.db.services.user_service import BetService

router = APIRouter()


class DashboardStats(BaseModel):
    """User dashboard statistics."""

    # Betting stats
    total_bets: int
    won_bets: int
    lost_bets: int
    pending_bets: int
    win_rate: float

    # Financial stats
    total_staked: float
    total_returns: float
    profit_loss: float
    roi_percentage: float

    # Bankroll
    initial_bankroll: float
    current_bankroll: float

    # Streaks
    current_streak: int
    best_streak: int

    # Followed predictions
    followed_predictions: int
    followed_wins: int
    followed_win_rate: float


@router.get("/stats", response_model=DashboardStats, responses=AUTH_RESPONSES)
async def get_user_stats(
    days: int = Query(30, ge=7, le=365),
    user: AuthenticatedUser | None = None,
) -> DashboardStats:
    """Get user betting statistics and ROI.

    Returns comprehensive statistics including:
    - Win/loss record
    - ROI and profit/loss
    - Bankroll tracking
    - Streak information
    """
    user_id = user.get("sub", "")

    # Get bankroll summary from BetService
    bankroll = await BetService.get_bankroll_summary(user_id)

    return DashboardStats(
        total_bets=bankroll["total_bets"],
        won_bets=bankroll["won_bets"],
        lost_bets=bankroll["lost_bets"],
        pending_bets=bankroll["pending_bets"],
        win_rate=bankroll["win_rate"],
        total_staked=bankroll["total_staked"],
        total_returns=bankroll["total_returned"],
        profit_loss=bankroll["profit_loss"],
        roi_percentage=bankroll["roi_pct"],
        initial_bankroll=bankroll["initial_bankroll"],
        current_bankroll=bankroll["current_bankroll"],
        current_streak=0,  # See PAR-170 for streak tracking
        best_streak=0,  # See PAR-170 for streak tracking
        followed_predictions=0,  # See PAR-170 for prediction following tracking
        followed_wins=0,
        followed_win_rate=0.0,
    )


@router.get("/export", response_model=None, responses=AUTH_RESPONSES)
async def export_user_data(
    format: str = Query("csv", pattern="^(csv|json)$"),
    user: AuthenticatedUser | None = None,
) -> dict[str, Any] | StreamingResponse:
    """Export user betting data.

    Supports CSV and JSON formats.
    """
    user_id = user.get("sub", "")

    # Get all bets
    bets = await BetService.list_bets(user_id, limit=1000)

    if format == "json":
        return {
            "bets": bets,
            "total": len(bets),
            "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        }

    # CSV export
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "match_id",
            "prediction",
            "odds",
            "amount",
            "status",
            "potential_return",
            "actual_return",
            "created_at",
        ],
    )
    writer.writeheader()
    for bet in bets:
        writer.writerow(bet)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bets-export-{user_id[:8]}.csv"},
    )
