"""Prediction endpoints - Using real match data from football-data.org.

Enhanced with advanced statistical models:
- Dixon-Coles: Handles low-score bias and time decay
- Advanced ELO: Dynamic K-factor and recent form
- Multiple ensemble: Combines best approaches

All endpoints require authentication.
See /src/prediction_engine/ensemble_advanced.py for details.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas import ErrorResponse
from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.core.cache import cache_get, cache_set
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.core.messages import api_msg, detect_language_from_header
from src.core.rate_limit import RATE_LIMITS, limiter
from src.data.sources.football_data import get_football_data_client
from src.db.repositories import get_uow
from src.db.services.prediction_service import PredictionService

# Data source type for beta feedback
DataSourceType = Literal["live_api", "cache", "database"]

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_language(request: Request) -> str:
    """Detect user's preferred language from Accept-Language header.

    Returns "fr" or "en" (default "fr"). Delegates to shared helper.
    """
    return detect_language_from_header(request.headers.get("Accept-Language", ""))


class DataSourceInfo(BaseModel):
    """Information about data source and any warnings (Beta feature)."""

    source: DataSourceType = "live_api"
    is_fallback: bool = False
    warning: str | None = None
    warning_code: str | None = None
    details: str | None = None
    retry_after_seconds: int | None = None


# Redis cache TTL for predictions (30 minutes for quick access)
PREDICTION_CACHE_TTL = 1800  # 30 minutes


async def _get_prediction_from_redis(match_id: int) -> dict[str, Any] | None:
    """Get prediction from Redis cache."""
    try:
        cache_key = f"prediction:{match_id}"
        cached = await cache_get(cache_key)
        if cached:
            return cast(dict[str, Any], json.loads(cached))
    except Exception as e:
        logger.debug(f"Redis cache miss for match {match_id}: {e}")
    return None


async def _cache_prediction_to_redis(match_id: int, prediction_data: dict[str, Any]) -> None:
    """Cache prediction to Redis."""
    try:
        cache_key = f"prediction:{match_id}"
        await cache_set(cache_key, json.dumps(prediction_data, default=str), PREDICTION_CACHE_TTL)
        logger.debug(f"Cached prediction for match {match_id} in Redis")
    except Exception as e:
        logger.warning(f"Failed to cache prediction in Redis: {e}")


class PredictionProbabilities(BaseModel):
    """Match outcome probabilities."""

    home_win: float = Field(..., ge=0, le=1, description="Probability of home win")
    draw: float = Field(..., ge=0, le=1, description="Probability of draw")
    away_win: float = Field(..., ge=0, le=1, description="Probability of away win")


class ModelContributions(BaseModel):
    """Individual model contributions to the prediction."""

    poisson: PredictionProbabilities | None = None
    xgboost: PredictionProbabilities | None = None
    xg_model: PredictionProbabilities | None = None
    elo: PredictionProbabilities | None = None


class LLMAdjustments(BaseModel):
    """LLM-derived adjustment factors."""

    injury_impact_home: float = Field(0.0, ge=-0.3, le=0.0)
    injury_impact_away: float = Field(0.0, ge=-0.3, le=0.0)
    sentiment_home: float = Field(0.0, ge=-0.1, le=0.1)
    sentiment_away: float = Field(0.0, ge=-0.1, le=0.1)
    tactical_edge: float = Field(0.0, ge=-0.05, le=0.05)
    total_adjustment: float = Field(0.0, ge=-0.5, le=0.5)
    reasoning: str = ""


class TeamFatigueInfo(BaseModel):
    """Fatigue information for a single team."""

    rest_days_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Rest days score (0=fatigued, 1=well-rested)"
    )
    fixture_congestion_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Fixture congestion score (0=congested, 1=light)"
    )
    combined_score: float = Field(0.5, ge=0.0, le=1.0, description="Combined fatigue score")


class WeatherInfo(BaseModel):
    """Weather information for match day."""

    available: bool = False
    temperature: float | None = Field(None, description="Temperature in Celsius")
    feels_like: float | None = Field(None, description="Feels like temperature")
    humidity: int | None = Field(None, description="Humidity percentage")
    description: str | None = Field(None, description="Weather description (e.g., 'Cloudy')")
    wind_speed: float | None = Field(None, description="Wind speed in m/s")
    rain_probability: float | None = Field(None, description="Rain probability 0-100")
    impact: str | None = Field(None, description="Impact on match: low, moderate, high")


class FatigueInfo(BaseModel):
    """Fatigue information for both teams in a match."""

    home_team: TeamFatigueInfo
    away_team: TeamFatigueInfo
    fatigue_advantage: float = Field(
        0.0, ge=-1.0, le=1.0, description="Home team advantage (positive = home more rested)"
    )


# Multi-Markets Response Models
class OverUnderResponse(BaseModel):
    """Over/Under market response."""

    line: float = Field(..., description="Goal line (1.5, 2.5, 3.5)")
    over_prob: float = Field(..., ge=0, le=1, description="Probability of over")
    under_prob: float = Field(..., ge=0, le=1, description="Probability of under")
    over_odds: float | None = Field(None, description="Bookmaker odds for over")
    under_odds: float | None = Field(None, description="Bookmaker odds for under")
    over_value: float | None = Field(None, description="Value score for over (positive = value)")
    under_value: float | None = Field(None, description="Value score for under (positive = value)")
    recommended: str = Field("over", description="Recommended bet: over or under")


class BttsResponse(BaseModel):
    """Both Teams To Score response."""

    yes_prob: float = Field(..., ge=0, le=1, description="Probability both teams score")
    no_prob: float = Field(..., ge=0, le=1, description="Probability one team blanks")
    yes_odds: float | None = Field(None, description="Fair odds for BTTS Yes")
    no_odds: float | None = Field(None, description="Fair odds for BTTS No")
    recommended: str = Field("yes", description="Recommended bet: yes or no")


class DoubleChanceResponse(BaseModel):
    """Double Chance market response."""

    home_or_draw: float = Field(..., ge=0, le=1, alias="1X", description="Home/Draw prob")
    away_or_draw: float = Field(..., ge=0, le=1, alias="X2", description="Away/Draw prob")
    home_or_away: float = Field(..., ge=0, le=1, alias="12", description="Home/Away prob")
    home_or_draw_odds: float | None = Field(None, description="Fair odds for 1X")
    away_or_draw_odds: float | None = Field(None, description="Fair odds for X2")
    home_or_away_odds: float | None = Field(None, description="Fair odds for 12")
    recommended: str = Field("1X", description="Recommended bet: 1X, X2, or 12")

    model_config = ConfigDict(populate_by_name=True)


class CorrectScoreResponse(BaseModel):
    """Correct Score prediction response."""

    scores: dict[str, float] = Field(..., description="Top 6 most likely scores with probabilities")
    most_likely: str = Field(..., description="Most likely score")
    most_likely_prob: float = Field(..., ge=0, le=1, description="Probability of most likely score")


class MultiMarketsResponse(BaseModel):
    """Complete multi-markets prediction response."""

    over_under_15: OverUnderResponse = Field(..., description="Over/Under 1.5 goals")
    over_under_25: OverUnderResponse = Field(..., description="Over/Under 2.5 goals")
    over_under_35: OverUnderResponse = Field(..., description="Over/Under 3.5 goals")
    btts: BttsResponse = Field(..., description="Both Teams To Score")
    double_chance: DoubleChanceResponse = Field(..., description="Double Chance markets")
    correct_score: CorrectScoreResponse = Field(..., description="Top correct score predictions")
    expected_home_goals: float = Field(..., description="Expected goals for home team")
    expected_away_goals: float = Field(..., description="Expected goals for away team")
    expected_total_goals: float = Field(..., description="Expected total goals")


class PredictionResponse(BaseModel):
    """Full prediction response for a match."""

    match_id: int
    home_team: str
    away_team: str
    competition: str
    match_date: datetime

    # Final prediction
    probabilities: PredictionProbabilities
    recommended_bet: Literal["home_win", "draw", "away_win"]
    confidence: float = Field(..., ge=0, le=1)
    value_score: float = Field(..., description="Value vs bookmaker odds")

    # Analysis
    explanation: str
    key_factors: list[str]
    risk_factors: list[str]

    # Model details (optional, for transparency)
    model_contributions: ModelContributions | None = None
    llm_adjustments: LLMAdjustments | None = None

    # Fatigue analysis (optional)
    fatigue_info: FatigueInfo | None = None

    # Weather info (optional)
    weather: WeatherInfo | None = None

    # Multi-markets predictions (optional)
    multi_markets: MultiMarketsResponse | None = None

    # Match context summary (RAG-generated)
    match_context_summary: str | None = Field(
        None, description="LLM-generated match context analysis"
    )
    news_sources: list[dict[str, str]] | None = Field(
        None, description="News sources used for context"
    )

    # Metadata
    created_at: datetime
    is_daily_pick: bool = False

    # Verification status (filled after match completion)
    is_verified: bool = Field(False, description="Whether the match result has been verified")
    is_correct: bool | None = Field(
        None, description="Whether prediction was correct (null if not verified)"
    )
    actual_score: str | None = Field(None, description="Actual match score (e.g., '2-1')")

    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class DailyPickResponse(BaseModel):
    """Daily pick with additional info."""

    rank: int = Field(..., ge=1, le=5)
    prediction: PredictionResponse
    pick_score: float = Field(..., description="Combined value × confidence score")


class DailyPicksResponse(BaseModel):
    """Response for daily picks endpoint."""

    date: str
    picks: list[DailyPickResponse]
    total_matches_analyzed: int
    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class PredictionStatsResponse(BaseModel):
    """Historical prediction performance stats."""

    total_predictions: int
    verified_predictions: int  # Number of predictions with verified results
    correct_predictions: int
    accuracy: float
    roi_simulated: float
    by_competition: dict[str, dict[str, Any]]
    by_bet_type: dict[str, dict[str, Any]]
    last_updated: datetime


class DailyStatsItem(BaseModel):
    """Single day's prediction statistics."""

    date: str
    predictions: int
    correct: int
    accuracy: float


class DailyStatsResponse(BaseModel):
    """Daily breakdown of prediction statistics for charting."""

    data: list[DailyStatsItem]
    total_days: int


# Import centralized competition names
from src.core.constants import COMPETITION_NAMES


def _build_multi_markets_response(mm: dict[str, Any]) -> MultiMarketsResponse:
    """Build MultiMarketsResponse from model_details multi_markets data.

    The data comes from dataclasses.asdict(MultiMarketsPrediction), so keys
    match the dataclass field names (over_under_15, btts, double_chance, etc.).
    """
    ou15 = mm.get("over_under_15", {})
    ou25 = mm.get("over_under_25", {})
    ou35 = mm.get("over_under_35", {})
    btts_data = mm.get("btts", {})
    dc_data = mm.get("double_chance", {})
    cs_data = mm.get("correct_score", {})

    exp_home = float(mm.get("expected_home_goals", 1.3))
    exp_away = float(mm.get("expected_away_goals", 1.0))

    def _ou(data: dict[str, Any], line: float) -> OverUnderResponse:
        over = float(data.get("over_prob", 0.5))
        under = float(data.get("under_prob", 1.0 - over))
        return OverUnderResponse(
            line=line,
            over_prob=over,
            under_prob=under,
            recommended=data.get("recommended", "over" if over > 0.5 else "under"),
        )

    # Correct score
    scores = cs_data.get("scores", {})
    most_likely = cs_data.get("most_likely", "1-0")
    ml_prob = float(cs_data.get("most_likely_prob", 0.1))

    # Double chance: asdict uses home_or_draw_prob, away_or_draw_prob, etc.
    dc_1x = float(dc_data.get("home_or_draw_prob", 0.5))
    dc_x2 = float(dc_data.get("away_or_draw_prob", 0.5))
    dc_12 = float(dc_data.get("home_or_away_prob", 0.5))

    return MultiMarketsResponse(
        over_under_15=_ou(ou15, 1.5),
        over_under_25=_ou(ou25, 2.5),
        over_under_35=_ou(ou35, 3.5),
        btts=BttsResponse(
            yes_prob=float(btts_data.get("yes_prob", 0.5)),
            no_prob=float(btts_data.get("no_prob", 0.5)),
            recommended=btts_data.get(
                "recommended",
                "yes" if float(btts_data.get("yes_prob", 0.5)) > 0.5 else "no",
            ),
        ),
        double_chance=DoubleChanceResponse(
            **{
                "1X": dc_1x,
                "X2": dc_x2,
                "12": dc_12,
            },
            recommended=dc_data.get(
                "recommended",
                "1X" if dc_1x >= dc_x2 and dc_1x >= dc_12 else ("X2" if dc_x2 >= dc_12 else "12"),
            ),
        ),
        correct_score=CorrectScoreResponse(
            scores=scores,
            most_likely=most_likely,
            most_likely_prob=ml_prob,
        ),
        expected_home_goals=exp_home,
        expected_away_goals=exp_away,
        expected_total_goals=exp_home + exp_away,
    )


def _get_recommended_bet(
    home_prob: float, draw_prob: float, away_prob: float
) -> Literal["home_win", "draw", "away_win"]:
    """Get recommended bet based on highest probability."""
    max_prob = max(home_prob, draw_prob, away_prob)
    if max_prob == home_prob:
        return "home_win"
    elif max_prob == away_prob:
        return "away_win"
    return "draw"


@router.get(
    "/daily",
    response_model=DailyPicksResponse,
    responses={
        **AUTH_RESPONSES,
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    operation_id="getDailyPicks",
)
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def get_daily_picks(
    request: Request,
    user: AuthenticatedUser,
    query_date: str | None = Query(None, alias="date", description="Date YYYY-MM-DD"),
) -> DailyPicksResponse:
    """
    Get the 5 best picks for the specified date ONLY.

    Selection criteria:
    - Minimum 5% value vs bookmaker odds
    - Minimum 60% confidence
    - Diversified across competitions

    Uses database caching to persist predictions across server restarts.
    """
    try:
        target_date_str = query_date or datetime.now().strftime("%Y-%m-%d")
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

        # Check Redis cache first (5-minute TTL for daily picks)
        redis_cache_key = f"daily_picks:{target_date_str}"
        cached_response = await cache_get(redis_cache_key)
        if cached_response:
            try:
                cached_data = json.loads(cached_response)
                logger.debug(f"Redis HIT for daily picks {target_date_str}")
                return DailyPicksResponse(**cached_data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Invalid Redis cache for daily picks: {e}")

        # Check if we have cached predictions in DB
        cached_predictions = await PredictionService.get_predictions_for_date_with_details(
            target_date
        )
        if cached_predictions:
            logger.info(f"Found {len(cached_predictions)} cached predictions for {target_date_str}")
            # Convert cached predictions to response format
            all_predictions = []
            for cached in cached_predictions:
                comp_code = cached.get("competition_code") or "UNKNOWN"
                # Map service outcome format to API format
                # Service returns: home, draw, away
                # API expects: home_win, draw, away_win
                recommendation = cached.get("recommendation", "")
                outcome_map: dict[str, Literal["home_win", "draw", "away_win"]] = {
                    "home": "home_win",
                    "draw": "draw",
                    "away": "away_win",
                    "home_win": "home_win",
                    "away_win": "away_win",
                }
                recommended_bet: Literal["home_win", "draw", "away_win"] = outcome_map.get(
                    recommendation, "draw"
                )
                # Get cached key_factors/risk_factors if available
                cached_key_factors = cached.get("key_factors")
                cached_risk_factors = cached.get("risk_factors")
                cached_value_score = cached.get("value_score")

                pred = PredictionResponse(
                    match_id=cached["match_id"],
                    home_team=cached.get("home_team") or "Unknown",
                    away_team=cached.get("away_team") or "Unknown",
                    competition=COMPETITION_NAMES.get(comp_code, comp_code),
                    match_date=datetime.fromisoformat(cached["match_date"]),
                    probabilities=PredictionProbabilities(
                        home_win=cached["home_win_prob"],
                        draw=cached["draw_prob"],
                        away_win=cached["away_win_prob"],
                    ),
                    recommended_bet=recommended_bet,
                    confidence=cached["confidence"],
                    value_score=cached_value_score if cached_value_score else 0.10,
                    explanation=cached.get("explanation") or "",
                    key_factors=(
                        cached_key_factors if cached_key_factors else ["Statistical analysis"]
                    ),
                    risk_factors=cached_risk_factors if cached_risk_factors else ["Cached data"],
                    created_at=datetime.fromisoformat(cached["created_at"]),
                    is_daily_pick=True,
                    # Verification fields from database
                    is_verified=cached.get("is_verified", False),
                    is_correct=cached.get("is_correct"),
                    actual_score=cached.get("actual_score"),
                )
                pick_score = pred.confidence * pred.value_score
                all_predictions.append((pred, pick_score))

            # Sort and return top 5
            all_predictions.sort(key=lambda x: x[1], reverse=True)
            daily_picks = [
                DailyPickResponse(rank=i + 1, prediction=p, pick_score=round(s, 4))
                for i, (p, s) in enumerate(all_predictions[:5])
            ]
            response = DailyPicksResponse(
                date=target_date_str,
                picks=daily_picks,
                total_matches_analyzed=len(cached_predictions),
            )
            # Cache in Redis for 5 minutes
            try:
                await cache_set(
                    redis_cache_key, json.dumps(response.model_dump(mode="json"), default=str), 300
                )
            except Exception as e:
                logger.debug(f"Failed to cache daily picks in Redis: {e}")
            return response

        # No cached predictions — all predictions are pre-computed by cron
        logger.info(f"No predictions in DB for {target_date_str}, returning empty picks")
        return DailyPicksResponse(
            date=target_date_str,
            picks=[],
            total_matches_analyzed=0,
        )

    except RateLimitError as e:
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        lang = _detect_language(request)
        raise HTTPException(
            status_code=429,
            detail={
                "message": api_msg("rate_limit_reached", lang),
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
                "tip": api_msg("rate_limit_tip", lang),
            },
        )
    except FootballDataAPIError as e:
        lang = _detect_language(request)
        raise HTTPException(
            status_code=502,
            detail={
                "message": api_msg("api_error", lang, detail=str(e)[:100]),
                "warning_code": "EXTERNAL_API_ERROR",
                "tip": api_msg("api_unavailable_tip", lang),
            },
        )


class PredictionDebugResponse(BaseModel):
    """Debug info about predictions data."""

    total_predictions: int
    verified_predictions: int
    finished_matches_with_predictions: int
    pending_verification: int
    message: str


@router.get(
    "/debug",
    response_model=PredictionDebugResponse,
    responses=AUTH_RESPONSES,
    operation_id="getPredictionDebug",
)
async def get_prediction_debug(
    user: AuthenticatedUser,
    days: int = Query(7, ge=1, le=30),
) -> PredictionDebugResponse:
    """Debug endpoint to check prediction data state."""
    try:
        async with get_uow() as uow:
            from datetime import timedelta

            from sqlalchemy import func, select

            from src.db.models import Match, Prediction, PredictionResult

            cutoff = datetime.now() - timedelta(days=days)

            # Count predictions
            pred_count = await uow.session.scalar(
                select(func.count(Prediction.id)).where(Prediction.created_at >= cutoff)
            )

            # Count verified (have PredictionResult)
            verified_count = await uow.session.scalar(
                select(func.count(PredictionResult.id))
                .join(Prediction)
                .where(PredictionResult.created_at >= cutoff)
            )

            # Count finished matches with predictions
            finished_with_pred = await uow.session.scalar(
                select(func.count(Match.id))
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.status.in_(["FINISHED", "finished"]),
                    Match.home_score.isnot(None),
                    Match.match_date >= cutoff,
                )
            )

            # Run verification
            verify_count = await PredictionService.verify_all_finished()

            return PredictionDebugResponse(
                total_predictions=pred_count or 0,
                verified_predictions=verified_count or 0,
                finished_matches_with_predictions=finished_with_pred or 0,
                pending_verification=verify_count,
                message=(
                    f"Last {days} days: {pred_count} predictions, "
                    f"{verified_count} verified, "
                    f"{finished_with_pred} finished w/ predictions, "
                    f"{verify_count} newly verified"
                ),
            )
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return PredictionDebugResponse(
            total_predictions=0,
            verified_predictions=0,
            finished_matches_with_predictions=0,
            pending_verification=0,
            message=f"Error: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=PredictionStatsResponse,
    responses=AUTH_RESPONSES,
    operation_id="getPredictionStats",
)
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def get_prediction_stats(
    request: Request,
    user: AuthenticatedUser,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    force_refresh: bool = Query(False, description="Force recalculation, bypass cache"),
) -> PredictionStatsResponse:
    """Get historical prediction performance statistics.

    Stats are pre-calculated daily at 6am and cached.
    Use force_refresh=true to bypass cache.
    """
    # Try to get cached data first (only for default 30 days)
    if days == 30 and not force_refresh:
        try:
            from src.services.cache_service import get_cached_data

            cached = await get_cached_data("prediction_stats_30d")
            if cached:
                logger.debug("Returning cached prediction stats")
                return PredictionStatsResponse(
                    total_predictions=cached.get("total_predictions", 0),
                    verified_predictions=cached.get("verified_predictions", 0),
                    correct_predictions=cached.get("correct_predictions", 0),
                    accuracy=cached.get("accuracy", 0.0),
                    roi_simulated=cached.get("roi_simulated", 0.0),
                    by_competition=cached.get("by_competition", {}),
                    by_bet_type=cached.get("by_bet_type", {}),
                    last_updated=datetime.fromisoformat(
                        cached.get("calculated_at", datetime.now().isoformat())
                    ),
                )
        except Exception as e:
            logger.warning(f"Cache lookup failed, falling back to live calculation: {e}")

    # First, verify any finished matches that haven't been verified
    await PredictionService.verify_all_finished()

    # Get the statistics
    stats = await PredictionService.get_statistics(days)

    # If no verified predictions, generate simulated stats from unverified predictions
    if stats["total_predictions"] == 0:
        simulated_stats = await PredictionService.get_all_statistics(days)
        if simulated_stats["total_predictions"] > 0:
            return PredictionStatsResponse(
                total_predictions=simulated_stats["total_predictions"],
                verified_predictions=0,  # No verified predictions yet
                correct_predictions=0,  # Not yet verified
                accuracy=0.0,  # Will be calculated after verification
                roi_simulated=0.0,
                by_competition=simulated_stats["by_competition"],
                by_bet_type=simulated_stats["by_bet_type"],
                last_updated=datetime.now(),
            )

    return PredictionStatsResponse(
        total_predictions=stats["total_predictions"],
        verified_predictions=stats.get("verified_predictions", stats["total_predictions"]),
        correct_predictions=stats["correct_predictions"],
        accuracy=stats["accuracy"],
        roi_simulated=stats["roi_simulated"],
        by_competition=stats["by_competition"],
        by_bet_type=stats["by_bet_type"],
        last_updated=datetime.now(),
    )


@router.get(
    "/stats/daily",
    response_model=DailyStatsResponse,
    responses=AUTH_RESPONSES,
    operation_id="getDailyStats",
)
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def get_daily_stats(
    request: Request,
    user: AuthenticatedUser,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
) -> DailyStatsResponse:
    """Get daily breakdown of prediction statistics.

    Returns stats grouped by day for charting accuracy over time.
    Each day includes: date, predictions count, correct count, accuracy.
    """
    try:
        async with get_uow() as uow:
            daily_data = await uow.predictions.get_daily_breakdown(days=days)

            return DailyStatsResponse(
                data=[DailyStatsItem(**day) for day in daily_data],
                total_days=len(daily_data),
            )
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return DailyStatsResponse(data=[], total_days=0)


async def _get_match_info_from_db(match_id: int) -> dict[str, Any] | None:
    """Try to get basic match info from database for fallback predictions."""
    try:
        async with get_uow() as uow:
            match = await uow.matches.get_by_id(match_id)
            if match:
                home_team = (
                    await uow.teams.get_by_id(match.home_team_id) if match.home_team_id else None
                )
                away_team = (
                    await uow.teams.get_by_id(match.away_team_id) if match.away_team_id else None
                )
                return {
                    "home_team": home_team.name if home_team else None,
                    "away_team": away_team.name if away_team else None,
                    "competition": (
                        COMPETITION_NAMES.get(match.competition_code, match.competition_code)
                        if match.competition_code
                        else None
                    ),
                    "match_date": match.match_date,
                }
    except Exception as e:
        logger.debug(f"Could not fetch match {match_id} from DB: {e}")
    return None


# ============================================================================
# Calibration Endpoint
# ============================================================================


class CalibrationBucket(BaseModel):
    """Single calibration bucket with predicted vs actual win rate."""

    confidence_range: str = Field(..., description="Confidence range, e.g., '60-70%'")
    predicted_confidence: float = Field(..., description="Average predicted confidence in bucket")
    actual_win_rate: float = Field(..., description="Actual win rate in this bucket")
    count: int = Field(..., description="Number of predictions in bucket")
    overconfidence: float = Field(
        ..., description="Difference: predicted - actual (positive = overconfident)"
    )


class CalibrationByBet(BaseModel):
    """Calibration data for a specific bet type."""

    bet_type: str = Field(..., description="home_win, draw, or away_win")
    total_predictions: int
    correct: int
    accuracy: float
    avg_confidence: float
    buckets: list[CalibrationBucket]


class CalibrationResponse(BaseModel):
    """Complete calibration analysis."""

    model_config = ConfigDict(populate_by_name=True)

    total_verified: int = Field(..., description="Total verified predictions")
    overall_accuracy: float = Field(..., description="Overall accuracy rate")
    overall_calibration_error: float = Field(
        ..., description="Mean calibration error (lower is better)"
    )
    by_bet_type: list[CalibrationByBet] = Field(..., description="Calibration by bet type")
    by_confidence: list[CalibrationBucket] = Field(
        ..., description="Calibration by confidence bucket"
    )
    by_competition: dict[str, dict[str, Any]] = Field(..., description="Performance by competition")
    period: str = Field(..., description="Analysis period")
    generated_at: datetime


@router.get(
    "/calibration",
    response_model=CalibrationResponse,
    responses=AUTH_RESPONSES,
    operation_id="getCalibration",
)
async def get_calibration(
    user: AuthenticatedUser,
    days: int = Query(90, ge=7, le=365, description="Number of days to analyze"),
) -> CalibrationResponse:
    """
    Get calibration analysis for prediction accuracy.

    Compares predicted confidence levels with actual outcomes to assess
    how well-calibrated the predictions are. A well-calibrated model
    should have 70% accuracy when it predicts 70% confidence.

    Returns:
        - Overall accuracy and calibration error
        - Breakdown by bet type (home_win, draw, away_win)
        - Breakdown by confidence buckets (50-60%, 60-70%, etc.)
        - Performance by competition
    """
    from sqlalchemy import and_, select

    from src.db.models import Match, PredictionResult

    async with get_uow() as uow:
        cutoff_date = datetime.now() - timedelta(days=days)

        # Get all verified predictions with their results
        query = (
            select(PredictionResult, Match)
            .join(Match, PredictionResult.match_id == Match.id)
            .where(
                and_(
                    PredictionResult.created_at >= cutoff_date,
                    Match.status == "FINISHED",
                )
            )
        )

        result = await uow.session.execute(query)
        rows = result.all()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail="No verified predictions found for this period",
            )

        # Process predictions
        predictions_data = []
        for pred, match in rows:
            # Determine actual outcome
            if match.home_score is not None and match.away_score is not None:
                if match.home_score > match.away_score:
                    actual_outcome = "home_win"
                elif match.home_score < match.away_score:
                    actual_outcome = "away_win"
                else:
                    actual_outcome = "draw"
            else:
                continue  # Skip if no score

            predicted = pred.predicted_outcome
            confidence = float(pred.confidence) if pred.confidence else 0.5
            is_correct = predicted == actual_outcome

            predictions_data.append(
                {
                    "predicted": predicted,
                    "actual": actual_outcome,
                    "confidence": confidence,
                    "is_correct": is_correct,
                    "competition": match.competition_code,
                }
            )

        total_verified = len(predictions_data)
        total_correct = sum(1 for p in predictions_data if p["is_correct"])
        overall_accuracy = total_correct / total_verified if total_verified > 0 else 0

        # Calculate by bet type
        bet_types = ["home_win", "draw", "away_win"]
        by_bet_type = []
        for bet in bet_types:
            bt_preds = [p for p in predictions_data if p["predicted"] == bet]
            bt_correct = sum(1 for p in bt_preds if p["is_correct"])
            bt_count = len(bt_preds)
            bt_accuracy = bt_correct / bt_count if bt_count > 0 else 0
            bt_avg_conf = sum(p["confidence"] for p in bt_preds) / bt_count if bt_count > 0 else 0

            # Buckets for this bet type
            buckets = _calculate_buckets(bt_preds)

            by_bet_type.append(
                CalibrationByBet(
                    bet_type=bet,
                    total_predictions=bt_count,
                    correct=bt_correct,
                    accuracy=bt_accuracy,
                    avg_confidence=bt_avg_conf,
                    buckets=buckets,
                )
            )

        # Calculate overall confidence buckets
        overall_buckets = _calculate_buckets(predictions_data)

        # Calculate mean calibration error
        calibration_errors = []
        for bucket in overall_buckets:
            if bucket.count > 0:
                calibration_errors.append(abs(bucket.overconfidence))
        mean_calibration_error = (
            sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0
        )

        # Calculate by competition
        by_competition: dict[str, dict[str, Any]] = {}
        competitions = set(p["competition"] for p in predictions_data if p["competition"])
        for comp in competitions:
            comp_preds = [p for p in predictions_data if p["competition"] == comp]
            comp_correct = sum(1 for p in comp_preds if p["is_correct"])
            comp_count = len(comp_preds)
            by_competition[comp] = {
                "total": comp_count,
                "correct": comp_correct,
                "accuracy": comp_correct / comp_count if comp_count > 0 else 0,
                "avg_confidence": (
                    sum(p["confidence"] for p in comp_preds) / comp_count if comp_count > 0 else 0
                ),
            }

        return CalibrationResponse(
            total_verified=total_verified,
            overall_accuracy=overall_accuracy,
            overall_calibration_error=mean_calibration_error,
            by_bet_type=by_bet_type,
            by_confidence=overall_buckets,
            by_competition=by_competition,
            period=f"Last {days} days",
            generated_at=datetime.now(),
        )


def _calculate_buckets(predictions: list[dict[str, Any]]) -> list[CalibrationBucket]:
    """Calculate calibration buckets for a set of predictions."""
    bucket_ranges = [
        (0.50, 0.55, "50-55%"),
        (0.55, 0.60, "55-60%"),
        (0.60, 0.65, "60-65%"),
        (0.65, 0.70, "65-70%"),
        (0.70, 0.75, "70-75%"),
        (0.75, 0.80, "75-80%"),
        (0.80, 0.85, "80-85%"),
        (0.85, 1.00, "85-100%"),
    ]

    buckets = []
    for low, high, label in bucket_ranges:
        bucket_preds = [p for p in predictions if low <= p["confidence"] < high]
        count = len(bucket_preds)
        if count > 0:
            avg_conf = sum(p["confidence"] for p in bucket_preds) / count
            actual_rate = sum(1 for p in bucket_preds if p["is_correct"]) / count
            overconfidence = avg_conf - actual_rate
        else:
            avg_conf = (low + high) / 2
            actual_rate = 0
            overconfidence = 0

        buckets.append(
            CalibrationBucket(
                confidence_range=label,
                predicted_confidence=avg_conf,
                actual_win_rate=actual_rate,
                count=count,
                overconfidence=overconfidence,
            )
        )

    return buckets


@router.get(
    "/{match_id}",
    response_model=PredictionResponse,
    responses={
        **AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Match not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    operation_id="getPrediction",
)
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def get_prediction(
    request: Request,
    match_id: int,
    user: AuthenticatedUser,
    include_model_details: bool = Query(False, description="Include model details"),
) -> PredictionResponse:
    """Get detailed prediction for a specific match.

    Cache strategy: Redis (30min) -> DB (permanent) -> Generate -> Save both
    """
    # 1. First, check Redis cache (fastest)
    try:
        redis_cached = await _get_prediction_from_redis(match_id)
        if redis_cached:
            logger.info(f"Redis cache HIT for match {match_id}")
            return PredictionResponse(**redis_cached)
    except Exception as e:
        logger.debug(f"Redis cache check failed: {e}")

    # 2. Check DB cache
    try:
        cached = await PredictionService.get_prediction(match_id)
        if cached:
            logger.info(f"DB cache HIT for match {match_id}")
            # Get match info from DB for team names
            async with get_uow() as uow:
                match_obj = await uow.matches.get_by_id(match_id)
                if match_obj:
                    home_team_obj = (
                        await uow.teams.get_by_id(match_obj.home_team_id)
                        if match_obj.home_team_id
                        else None
                    )
                    away_team_obj = (
                        await uow.teams.get_by_id(match_obj.away_team_id)
                        if match_obj.away_team_id
                        else None
                    )
                    home_team = home_team_obj.name if home_team_obj else "Unknown"
                    away_team = away_team_obj.name if away_team_obj else "Unknown"
                    comp_code = match_obj.competition_code or "UNKNOWN"
                    match_date_val = (
                        match_obj.match_date if match_obj.match_date else datetime.now()
                    )
                else:
                    home_team = "Unknown"
                    away_team = "Unknown"
                    comp_code = "UNKNOWN"
                    match_date_val = datetime.now()

            # Map predicted_outcome to bet format
            outcome_map: dict[str, Literal["home_win", "draw", "away_win"]] = {
                "home": "home_win",
                "draw": "draw",
                "away": "away_win",
            }
            recommended: Literal["home_win", "draw", "away_win"] = outcome_map.get(
                cached.get("predicted_outcome", "draw"), "draw"
            )

            # Use cached key_factors and risk_factors if available
            key_factors = cached.get("key_factors") or []
            risk_factors = cached.get("risk_factors") or []

            # Parse enrichment data from model_details
            cached_model_details = cached.get("model_details")
            model_contributions = None
            llm_adjustments_obj = None
            multi_markets_obj = None
            fatigue_obj = None
            weather_obj = None

            if cached_model_details and isinstance(cached_model_details, dict):
                # Parse multi-markets
                mm = cached_model_details.get("multi_markets")
                if mm and isinstance(mm, dict):
                    try:
                        multi_markets_obj = _build_multi_markets_response(mm)
                    except Exception as e:
                        logger.debug(f"Failed to parse multi_markets: {e}")

                # Parse fatigue
                fat = cached_model_details.get("fatigue")
                if fat and isinstance(fat, dict):
                    try:
                        home_fat = fat.get("home", {})
                        away_fat = fat.get("away", {})
                        h_rest = float(home_fat.get("rest_days", 3))
                        a_rest = float(away_fat.get("rest_days", 3))
                        fatigue_obj = FatigueInfo(
                            home_team=TeamFatigueInfo(
                                rest_days_score=min(1.0, h_rest / 7.0),
                                fixture_congestion_score=1.0 - float(home_fat.get("congestion", 0)),
                                combined_score=min(1.0, h_rest / 7.0) * 0.6
                                + (1.0 - float(home_fat.get("congestion", 0))) * 0.4,
                            ),
                            away_team=TeamFatigueInfo(
                                rest_days_score=min(1.0, a_rest / 7.0),
                                fixture_congestion_score=1.0 - float(away_fat.get("congestion", 0)),
                                combined_score=min(1.0, a_rest / 7.0) * 0.6
                                + (1.0 - float(away_fat.get("congestion", 0))) * 0.4,
                            ),
                            fatigue_advantage=round(
                                min(1.0, h_rest / 7.0) - min(1.0, a_rest / 7.0), 2
                            ),
                        )
                    except Exception as e:
                        logger.debug(f"Failed to parse fatigue: {e}")

                # Parse weather
                wx = cached_model_details.get("weather")
                if wx and isinstance(wx, dict) and wx.get("available"):
                    try:
                        weather_obj = WeatherInfo(
                            available=True,
                            temperature=wx.get("temperature"),
                            feels_like=wx.get("feels_like"),
                            humidity=wx.get("humidity"),
                            description=wx.get("description"),
                            wind_speed=wx.get("wind_speed"),
                            rain_probability=wx.get("rain_probability"),
                            impact=wx.get("impact"),
                        )
                    except Exception as e:
                        logger.debug(f"Failed to parse weather: {e}")

                # Parse model contributions (new array format)
                if include_model_details:
                    mc_list = cached_model_details.get("model_contributions", [])
                    if mc_list and isinstance(mc_list, list):
                        try:
                            # Map new array format to legacy response format
                            model_map: dict[str, str] = {
                                "poisson": "poisson",
                                "xgboost": "xgboost",
                                "xg": "xg_model",
                                "advanced_elo": "elo",
                                "basic_elo": "elo",
                                "dixon_coles": "poisson",
                                "random_forest": "xgboost",
                            }
                            probs_by_type: dict[str, PredictionProbabilities] = {}
                            for mc in mc_list:
                                raw = mc.get("name", "").lower()
                                name = raw.replace("-", "_").replace(" ", "_")
                                mapped = model_map.get(name)
                                if mapped and mapped not in probs_by_type:
                                    probs_by_type[mapped] = PredictionProbabilities(
                                        home_win=mc.get("home_prob", 0.33),
                                        draw=mc.get("draw_prob", 0.34),
                                        away_win=mc.get("away_prob", 0.33),
                                    )
                            model_contributions = ModelContributions(
                                poisson=probs_by_type.get("poisson"),
                                xgboost=probs_by_type.get("xgboost"),
                                xg_model=probs_by_type.get("xg_model"),
                                elo=probs_by_type.get("elo"),
                            )
                        except Exception as e:
                            logger.debug(f"Failed to parse model_contributions: {e}")

                    cached_llm_adjustments = cached.get("llm_adjustments")
                    if cached_llm_adjustments:
                        try:
                            llm_adjustments_obj = LLMAdjustments(**cached_llm_adjustments)
                        except Exception as e:
                            logger.debug(f"Failed to parse llm_adjustments: {e}")

            # Safe float conversion (handles None values)
            def safe_float(val: Any, default: float) -> float:
                if val is None:
                    return default
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            response = PredictionResponse(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                competition=COMPETITION_NAMES.get(comp_code, comp_code),
                match_date=match_date_val,
                probabilities=PredictionProbabilities(
                    home_win=safe_float(cached.get("home_win_prob"), 0.33),
                    draw=safe_float(cached.get("draw_prob"), 0.34),
                    away_win=safe_float(cached.get("away_win_prob"), 0.33),
                ),
                confidence=safe_float(cached.get("confidence"), 0.5),
                recommended_bet=recommended,
                value_score=safe_float(cached.get("value_score"), 0.10),
                explanation=cached.get("explanation") or "",
                key_factors=key_factors,
                risk_factors=risk_factors,
                model_contributions=model_contributions,
                llm_adjustments=llm_adjustments_obj,
                fatigue_info=fatigue_obj,
                weather=weather_obj,
                multi_markets=multi_markets_obj,
                match_context_summary=cached.get("match_context_summary"),
                news_sources=cached.get("news_sources"),
                created_at=datetime.now(),
                data_source=DataSourceInfo(source="database"),
            )

            # Also cache in Redis for faster future access
            try:
                await _cache_prediction_to_redis(match_id, response.model_dump(mode="json"))
            except Exception as e:
                logger.debug(f"Failed to cache prediction {match_id} in Redis: {e}")

            return response
    except Exception as e:
        logger.warning(f"DB cache lookup failed for match {match_id}: {e}")

    # 3. No prediction in DB — return 404 (all predictions are pre-computed by cron)
    lang = _detect_language(request)
    raise HTTPException(
        status_code=404,
        detail=api_msg("prediction_not_ready", lang),
    )


class VerifyPredictionRequest(BaseModel):
    """Request body for verifying a prediction."""

    home_score: int = Field(..., ge=0, description="Final home team score")
    away_score: int = Field(..., ge=0, description="Final away team score")


class VerifyPredictionResponse(BaseModel):
    """Response after verifying a prediction."""

    match_id: int
    home_score: int
    away_score: int
    actual_result: str
    was_correct: bool
    message: str


@router.post(
    "/{match_id}/verify",
    responses=AUTH_RESPONSES,
    operation_id="verifyPrediction",
    response_model=VerifyPredictionResponse,
)
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def verify_prediction_endpoint(
    request: Request,
    match_id: int,
    body: VerifyPredictionRequest,
    user: AuthenticatedUser,
) -> VerifyPredictionResponse:
    """
    Verify a prediction against actual match result.

    Updates the prediction record with actual scores and correctness.
    Used for tracking prediction accuracy and ROI.
    """
    # Verify the prediction using async service
    result = await PredictionService.verify_prediction(match_id, body.home_score, body.away_score)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No prediction found for match {match_id}",
        )

    # Map actual_outcome to actual_result format expected by response
    # Service returns: home, draw, away
    # Response expects: home_win, draw, away_win
    actual_outcome = result.get("actual_outcome", "")
    outcome_map = {"home": "home_win", "away": "away_win", "draw": "draw"}
    actual_result = outcome_map.get(actual_outcome, actual_outcome)

    return VerifyPredictionResponse(
        match_id=match_id,
        home_score=body.home_score,
        away_score=body.away_score,
        actual_result=actual_result,
        was_correct=result["was_correct"],
        message=f"Prediction for match {match_id} verified successfully",
    )


@router.post("/{match_id}/refresh", responses=AUTH_RESPONSES, operation_id="refreshPrediction")
@limiter.limit(RATE_LIMITS["predictions"])  # type: ignore[misc]
async def refresh_prediction(
    request: Request, match_id: int, user: AuthenticatedUser
) -> dict[str, str]:
    """Force refresh a prediction (admin only)."""
    try:
        # Verify match exists
        client = get_football_data_client()
        await client.get_match(match_id)
        return {"status": "queued", "match_id": str(match_id)}

    except RateLimitError as e:
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        lang = _detect_language(request)
        raise HTTPException(
            status_code=429,
            detail={
                "message": api_msg("rate_limit_reached", lang),
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
            },
        )
    except FootballDataAPIError as e:
        lang = _detect_language(request)
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 502,
            detail=(
                f"Match {match_id} not found"
                if "not found" in str(e).lower()
                else api_msg("api_error_beta", lang, detail=str(e))
            ),
        )
