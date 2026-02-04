"""Dashboard API routes for user statistics and ROI tracking."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.supabase_auth import get_current_user
from src.data.database import get_db_connection

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    days: int = Query(30, ge=7, le=365),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get user prediction statistics and ROI."""
    user_id = current_user.get("id")

    conn = get_db_connection()
    if not conn:
        return _get_demo_stats(days)

    try:
        cursor = conn.cursor()
        start_date = datetime.now() - timedelta(days=days)

        # Get user predictions with results
        cursor.execute(
            """
            SELECT 
                p.id,
                p.match_id,
                p.prediction_type,
                p.predicted_outcome,
                p.confidence,
                p.odds,
                p.stake,
                p.is_correct,
                p.created_at,
                m.home_team,
                m.away_team,
                m.competition
            FROM user_predictions p
            LEFT JOIN matches m ON p.match_id = m.id
            WHERE p.user_id = %s AND p.created_at >= %s
            ORDER BY p.created_at DESC
            """,
            (user_id, start_date),
        )
        predictions = cursor.fetchall()

        # Calculate stats
        total = len(predictions)
        won = sum(1 for p in predictions if p[7] is True)
        lost = sum(1 for p in predictions if p[7] is False)
        pending = sum(1 for p in predictions if p[7] is None)

        # Calculate ROI
        total_stake = sum(p[6] or 1.0 for p in predictions if p[7] is not None)
        total_return = sum((p[5] or 2.0) * (p[6] or 1.0) if p[7] else 0 for p in predictions)
        roi = ((total_return - total_stake) / total_stake * 100) if total_stake > 0 else 0

        # Stats by competition
        competition_stats: dict[str, dict[str, int]] = {}
        for p in predictions:
            comp = p[11] or "Unknown"
            if comp not in competition_stats:
                competition_stats[comp] = {"total": 0, "won": 0, "lost": 0}
            competition_stats[comp]["total"] += 1
            if p[7] is True:
                competition_stats[comp]["won"] += 1
            elif p[7] is False:
                competition_stats[comp]["lost"] += 1

        # ROI over time (weekly buckets)
        roi_history = _calculate_roi_history(predictions, days)

        return {
            "period_days": days,
            "summary": {
                "total_predictions": total,
                "won": won,
                "lost": lost,
                "pending": pending,
                "win_rate": (won / (won + lost) * 100) if (won + lost) > 0 else 0,
                "roi": round(roi, 2),
                "total_stake": round(total_stake, 2),
                "total_return": round(total_return, 2),
                "profit": round(total_return - total_stake, 2),
            },
            "by_competition": [
                {
                    "competition": comp,
                    "total": stats["total"],
                    "won": stats["won"],
                    "lost": stats["lost"],
                    "win_rate": (
                        round(stats["won"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
                    ),
                }
                for comp, stats in sorted(
                    competition_stats.items(), key=lambda x: x[1]["total"], reverse=True
                )
            ],
            "roi_history": roi_history,
            "recent_predictions": [
                {
                    "id": p[0],
                    "match": f"{p[9]} vs {p[10]}",
                    "competition": p[11],
                    "prediction": p[3],
                    "confidence": p[4],
                    "odds": p[5],
                    "is_correct": p[7],
                    "date": p[8].isoformat() if p[8] else None,
                }
                for p in predictions[:10]
            ],
        }
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return _get_demo_stats(days)
    finally:
        conn.close()


def _calculate_roi_history(predictions: list, days: int) -> list[dict[str, Any]]:
    """Calculate ROI history in weekly buckets."""
    if not predictions:
        return []

    # Group by week
    weeks: dict[str, dict[str, float]] = {}
    for p in predictions:
        if p[7] is None:  # Skip pending
            continue
        date = p[8]
        if not date:
            continue
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")

        if week_key not in weeks:
            weeks[week_key] = {"stake": 0, "return": 0}

        stake = p[6] or 1.0
        weeks[week_key]["stake"] += stake
        if p[7]:  # Won
            weeks[week_key]["return"] += (p[5] or 2.0) * stake

    # Convert to list with cumulative ROI
    result = []
    cumulative_stake = 0
    cumulative_return = 0

    for week in sorted(weeks.keys()):
        cumulative_stake += weeks[week]["stake"]
        cumulative_return += weeks[week]["return"]
        roi = (
            ((cumulative_return - cumulative_stake) / cumulative_stake * 100)
            if cumulative_stake > 0
            else 0
        )
        result.append(
            {
                "week": week,
                "roi": round(roi, 2),
                "cumulative_profit": round(cumulative_return - cumulative_stake, 2),
            }
        )

    return result


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
