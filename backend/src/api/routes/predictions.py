"""Prediction endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class PredictionProbabilities(BaseModel):
    """Match outcome probabilities."""

    home_win: float = Field(..., ge=0, le=1, description="Probability of home win")
    draw: float = Field(..., ge=0, le=1, description="Probability of draw")
    away_win: float = Field(..., ge=0, le=1, description="Probability of away win")


class ModelContributions(BaseModel):
    """Individual model contributions to the prediction."""

    poisson: PredictionProbabilities
    xgboost: PredictionProbabilities
    xg_model: PredictionProbabilities
    elo: PredictionProbabilities


class LLMAdjustments(BaseModel):
    """LLM-derived adjustment factors."""

    injury_impact_home: float = Field(0.0, ge=-0.3, le=0.0)
    injury_impact_away: float = Field(0.0, ge=-0.3, le=0.0)
    sentiment_home: float = Field(0.0, ge=-0.1, le=0.1)
    sentiment_away: float = Field(0.0, ge=-0.1, le=0.1)
    tactical_edge: float = Field(0.0, ge=-0.05, le=0.05)
    total_adjustment: float = Field(0.0, ge=-0.5, le=0.5)
    reasoning: str = ""


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

    # Metadata
    created_at: datetime
    is_daily_pick: bool = False


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


class PredictionStatsResponse(BaseModel):
    """Historical prediction performance stats."""

    total_predictions: int
    correct_predictions: int
    accuracy: float
    roi_simulated: float
    by_competition: dict[str, dict]
    by_bet_type: dict[str, dict]
    last_updated: datetime


@router.get("/daily", response_model=DailyPicksResponse)
async def get_daily_picks(
    date: str | None = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
) -> DailyPicksResponse:
    """
    Get the 5 best picks for the day.

    Selection criteria:
    - Minimum 5% value vs bookmaker odds
    - Minimum 60% confidence
    - Diversified across competitions
    """
    # TODO: Implement prediction logic
    return DailyPicksResponse(
        date=date or datetime.now().strftime("%Y-%m-%d"),
        picks=[],
        total_matches_analyzed=0,
    )


@router.get("/{match_id}", response_model=PredictionResponse)
async def get_prediction(
    match_id: int,
    include_model_details: bool = Query(False, description="Include individual model contributions"),
) -> PredictionResponse:
    """Get detailed prediction for a specific match."""
    # TODO: Implement
    raise NotImplementedError("Prediction not implemented yet")


@router.get("/stats", response_model=PredictionStatsResponse)
async def get_prediction_stats(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
) -> PredictionStatsResponse:
    """Get historical prediction performance statistics."""
    # TODO: Implement from database
    return PredictionStatsResponse(
        total_predictions=0,
        correct_predictions=0,
        accuracy=0.0,
        roi_simulated=0.0,
        by_competition={},
        by_bet_type={},
        last_updated=datetime.now(),
    )


@router.post("/{match_id}/refresh")
async def refresh_prediction(match_id: int) -> dict[str, str]:
    """Force refresh a prediction (admin only)."""
    # TODO: Implement with auth
    return {"status": "queued", "match_id": str(match_id)}
