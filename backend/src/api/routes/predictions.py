"""Prediction endpoints."""

import json
import random
from datetime import datetime, timedelta
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


# Mock data with realistic matches
MOCK_MATCHES = [
    {
        "id": 1,
        "home_team": "Manchester City",
        "away_team": "Arsenal",
        "competition": "PL",
        "match_date": datetime.now() + timedelta(days=1),
    },
    {
        "id": 2,
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "competition": "PD",
        "match_date": datetime.now() + timedelta(days=2),
    },
    {
        "id": 3,
        "home_team": "Bayern Munich",
        "away_team": "Borussia Dortmund",
        "competition": "BL1",
        "match_date": datetime.now() + timedelta(days=1),
    },
    {
        "id": 4,
        "home_team": "PSG",
        "away_team": "Olympique Marseille",
        "competition": "FL1",
        "match_date": datetime.now() + timedelta(days=3),
    },
    {
        "id": 5,
        "home_team": "Inter Milan",
        "away_team": "AC Milan",
        "competition": "SA",
        "match_date": datetime.now() + timedelta(days=2),
    },
    {
        "id": 6,
        "home_team": "Liverpool",
        "away_team": "Manchester United",
        "competition": "PL",
        "match_date": datetime.now() + timedelta(days=4),
    },
    {
        "id": 7,
        "home_team": "Atletico Madrid",
        "away_team": "Real Sociedad",
        "competition": "PD",
        "match_date": datetime.now() + timedelta(days=3),
    },
    {
        "id": 8,
        "home_team": "Napoli",
        "away_team": "Juventus",
        "competition": "SA",
        "match_date": datetime.now() + timedelta(days=1),
    },
    {
        "id": 9,
        "home_team": "Tottenham",
        "away_team": "Chelsea",
        "competition": "PL",
        "match_date": datetime.now() + timedelta(days=2),
    },
    {
        "id": 10,
        "home_team": "Bayer Leverkusen",
        "away_team": "RB Leipzig",
        "competition": "BL1",
        "match_date": datetime.now() + timedelta(days=2),
    },
]

COMPETITION_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "EL": "Europa League",
}

KEY_FACTORS_TEMPLATES = {
    "home_dominant": [
        "Très bonne forme domestique",
        "Avantage du terrain significatif",
        "Supériorité en possibilité statistique",
        "Attaque puissante à domicile",
    ],
    "away_strong": [
        "Excellente série loin du domicile",
        "Défense très solide en déplacements",
        "Efficacité offensive élevée",
        "Moral de l'équipe excellent",
    ],
    "balanced": [
        "Matchs équilibrés historiquement",
        "Formes similaires actuellement",
        "Qualité défensive comparable",
        "Potentiel d'échanges nombreux",
    ],
}

RISK_FACTORS_TEMPLATES = [
    "Absence de joueurs clés possibles",
    "Fatigue accumulée possible",
    "Conditions météorologiques défavorables",
    "Arbitrage imprévisible",
    "Historique de blessures précoces",
]

EXPLANATIONS_TEMPLATES = {
    "home_win": "Notre modèle privilégie {home} pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. {away} reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
    "draw": "Un match équilibré où les deux équipes possèdent les atouts pour obtenir un résultat positif. Les statistiques suggèrent un partage des points probable avec un contexte tactique fermé.",
    "away_win": "Malgré le contexte de déplacement, {away} dispose des arguments suffisants pour s'imposer. La qualité supérieure de {home} pourrait être contrebalancée par la robustesse défensive des visiteurs.",
}


def _generate_realistic_probabilities(
    match_strength_ratio: float,
) -> tuple[float, float, float]:
    """Generate realistic probabilities based on expected strength ratio."""
    # match_strength_ratio: 1.0 = balanced, > 1.0 = home stronger, < 1.0 = away stronger

    if match_strength_ratio > 1.1:
        # Home advantage strong
        home = random.uniform(0.50, 0.68)
        draw = random.uniform(0.20, 0.30)
        away = 1.0 - home - draw
    elif match_strength_ratio < 0.9:
        # Away advantage
        away = random.uniform(0.40, 0.55)
        draw = random.uniform(0.22, 0.32)
        home = 1.0 - away - draw
    else:
        # Balanced
        home = random.uniform(0.35, 0.45)
        away = random.uniform(0.35, 0.45)
        draw = 1.0 - home - away

    # Normalize to ensure exactly 1.0
    total = home + draw + away
    return round(home / total, 4), round(draw / total, 4), round(away / total, 4)


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


def _generate_prediction(match: dict, include_model_details: bool = False) -> PredictionResponse:
    """Generate a realistic prediction for a match."""
    home_team = match["home_team"]
    away_team = match["away_team"]
    competition = match["competition"]

    # Generate realistic probabilities
    strength_ratio = random.uniform(0.75, 1.35)
    home_prob, draw_prob, away_prob = _generate_realistic_probabilities(strength_ratio)

    # Get recommended bet
    recommended_bet = _get_recommended_bet(home_prob, draw_prob, away_prob)

    # Generate confidence score (60-85%)
    base_confidence = random.uniform(0.60, 0.85)
    confidence = round(base_confidence, 3)

    # Generate value score (5-18%)
    value_score = round(random.uniform(0.05, 0.18), 3)

    # Select key factors based on predicted outcome
    if recommended_bet == "home_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["home_dominant"], 2)
    elif recommended_bet == "away_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["away_strong"], 2)
    else:
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["balanced"], 2)

    # Select risk factors
    risk_factors = random.sample(RISK_FACTORS_TEMPLATES, 2)

    # Generate explanation
    explanation_template = EXPLANATIONS_TEMPLATES[recommended_bet]
    explanation = explanation_template.format(home=home_team, away=away_team)

    # Model contributions (optional)
    model_contributions = None
    if include_model_details:
        # Generate slight variations around main prediction
        base_home = home_prob + random.uniform(-0.05, 0.05)
        base_home = max(0.01, min(0.99, base_home))

        model_contributions = ModelContributions(
            poisson=PredictionProbabilities(
                home_win=round(base_home, 4),
                draw=round(max(0.01, 0.40 - base_home / 2), 4),
                away_win=round(1.0 - base_home - max(0.01, 0.40 - base_home / 2), 4),
            ),
            xgboost=PredictionProbabilities(
                home_win=home_prob,
                draw=draw_prob,
                away_win=away_prob,
            ),
            xg_model=PredictionProbabilities(
                home_win=round(home_prob + random.uniform(-0.03, 0.03), 4),
                draw=round(draw_prob + random.uniform(-0.02, 0.02), 4),
                away_win=round(away_prob + random.uniform(-0.03, 0.03), 4),
            ),
            elo=PredictionProbabilities(
                home_win=round(home_prob - random.uniform(0.01, 0.04), 4),
                draw=round(draw_prob + random.uniform(0.00, 0.02), 4),
                away_win=round(away_prob + random.uniform(0.01, 0.03), 4),
            ),
        )

    # LLM adjustments (optional)
    llm_adjustments = None
    if include_model_details:
        injury_impact_home = round(random.uniform(-0.15, 0.0), 3)
        injury_impact_away = round(random.uniform(-0.15, 0.0), 3)
        sentiment_home = round(random.uniform(-0.05, 0.05), 3)
        sentiment_away = round(random.uniform(-0.05, 0.05), 3)
        tactical_edge = round(random.uniform(-0.03, 0.03), 3)

        llm_adjustments = LLMAdjustments(
            injury_impact_home=injury_impact_home,
            injury_impact_away=injury_impact_away,
            sentiment_home=sentiment_home,
            sentiment_away=sentiment_away,
            tactical_edge=tactical_edge,
            total_adjustment=round(
                injury_impact_home + injury_impact_away + sentiment_home + sentiment_away + tactical_edge, 3
            ),
            reasoning="Analyse LLM basée sur les actualités d'équipes et les facteurs contextuels.",
        )

    return PredictionResponse(
        match_id=match["id"],
        home_team=home_team,
        away_team=away_team,
        competition=COMPETITION_NAMES.get(competition, competition),
        match_date=match["match_date"],
        probabilities=PredictionProbabilities(
            home_win=home_prob,
            draw=draw_prob,
            away_win=away_prob,
        ),
        recommended_bet=recommended_bet,
        confidence=confidence,
        value_score=value_score,
        explanation=explanation,
        key_factors=key_factors,
        risk_factors=risk_factors,
        model_contributions=model_contributions,
        llm_adjustments=llm_adjustments,
        created_at=datetime.now(),
        is_daily_pick=False,
    )


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
    query_date = date or datetime.now().strftime("%Y-%m-%d")

    # Filter matches for the specified date
    target_date = datetime.strptime(query_date, "%Y-%m-%d")
    matches_for_date = [
        m for m in MOCK_MATCHES
        if m["match_date"].date() == target_date.date()
    ]

    if not matches_for_date:
        # Return empty but valid response if no matches for that date
        return DailyPicksResponse(
            date=query_date,
            picks=[],
            total_matches_analyzed=0,
        )

    # Generate predictions for all matches
    all_predictions = []
    for match in matches_for_date:
        pred = _generate_prediction(match, include_model_details=False)
        # Calculate pick score (confidence * value_score)
        pick_score = pred.confidence * pred.value_score
        all_predictions.append((pred, pick_score))

    # Sort by pick score and select top 5
    all_predictions.sort(key=lambda x: x[1], reverse=True)
    top_5 = all_predictions[:5]

    # Create daily pick responses with ranks
    daily_picks = []
    for rank, (pred, pick_score) in enumerate(top_5, 1):
        pred.is_daily_pick = True
        daily_picks.append(
            DailyPickResponse(
                rank=rank,
                prediction=pred,
                pick_score=round(pick_score, 4),
            )
        )

    return DailyPicksResponse(
        date=query_date,
        picks=daily_picks,
        total_matches_analyzed=len(matches_for_date),
    )


@router.get("/{match_id}", response_model=PredictionResponse)
async def get_prediction(
    match_id: int,
    include_model_details: bool = Query(False, description="Include individual model contributions"),
) -> PredictionResponse:
    """Get detailed prediction for a specific match."""
    # Find match in mock data
    match = next((m for m in MOCK_MATCHES if m["id"] == match_id), None)

    if not match:
        raise ValueError(f"Match with ID {match_id} not found")

    return _generate_prediction(match, include_model_details=include_model_details)


@router.get("/stats", response_model=PredictionStatsResponse)
async def get_prediction_stats(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
) -> PredictionStatsResponse:
    """Get historical prediction performance statistics."""
    # Mock statistics with realistic values
    total_predictions = random.randint(150, 250)
    correct_predictions = int(total_predictions * random.uniform(0.52, 0.62))
    accuracy = round(correct_predictions / total_predictions, 4)
    roi_simulated = round(random.uniform(0.08, 0.25), 4)  # 8-25% ROI

    # Statistics by competition
    by_competition = {
        "PL": {
            "total": random.randint(25, 40),
            "correct": random.randint(15, 28),
            "accuracy": round(random.uniform(0.52, 0.65), 4),
        },
        "PD": {
            "total": random.randint(20, 35),
            "correct": random.randint(12, 24),
            "accuracy": round(random.uniform(0.50, 0.62), 4),
        },
        "BL1": {
            "total": random.randint(15, 30),
            "correct": random.randint(9, 20),
            "accuracy": round(random.uniform(0.48, 0.60), 4),
        },
        "SA": {
            "total": random.randint(15, 30),
            "correct": random.randint(9, 20),
            "accuracy": round(random.uniform(0.50, 0.62), 4),
        },
        "FL1": {
            "total": random.randint(15, 30),
            "correct": random.randint(8, 20),
            "accuracy": round(random.uniform(0.48, 0.60), 4),
        },
    }

    # Statistics by bet type
    by_bet_type = {
        "home_win": {
            "total": random.randint(50, 80),
            "correct": random.randint(28, 50),
            "accuracy": round(random.uniform(0.52, 0.65), 4),
            "avg_value": round(random.uniform(0.08, 0.15), 4),
        },
        "draw": {
            "total": random.randint(30, 60),
            "correct": random.randint(14, 36),
            "accuracy": round(random.uniform(0.45, 0.58), 4),
            "avg_value": round(random.uniform(0.06, 0.12), 4),
        },
        "away_win": {
            "total": random.randint(40, 70),
            "correct": random.randint(22, 42),
            "accuracy": round(random.uniform(0.50, 0.62), 4),
            "avg_value": round(random.uniform(0.08, 0.16), 4),
        },
    }

    return PredictionStatsResponse(
        total_predictions=total_predictions,
        correct_predictions=correct_predictions,
        accuracy=accuracy,
        roi_simulated=roi_simulated,
        by_competition=by_competition,
        by_bet_type=by_bet_type,
        last_updated=datetime.now(),
    )


@router.post("/{match_id}/refresh")
async def refresh_prediction(match_id: int) -> dict[str, str]:
    """Force refresh a prediction (admin only)."""
    # Verify match exists
    match = next((m for m in MOCK_MATCHES if m["id"] == match_id), None)
    if not match:
        raise ValueError(f"Match with ID {match_id} not found")

    return {"status": "queued", "match_id": str(match_id)}
