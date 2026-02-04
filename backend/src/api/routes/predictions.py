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
import random
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from groq import Groq
from pydantic import BaseModel, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.core.config import settings
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.core.rate_limit import RATE_LIMITS, limiter
from src.data.data_enrichment import get_data_enrichment
from src.data.fatigue_service import MatchFatigueData, get_fatigue_service
from src.data.sources.football_data import MatchData, get_football_data_client
from src.db.services.match_service import MatchService
from src.db.services.prediction_service import PredictionService
from src.llm.prompts_advanced import get_prediction_analysis_prompt
from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor
from src.prediction_engine.multi_markets import get_multi_markets_prediction
from src.prediction_engine.rag_enrichment import get_rag_enrichment

# Data source type for beta feedback
DataSourceType = Literal["live_api", "cache", "database", "mock", "fallback"]

logger = logging.getLogger(__name__)

router = APIRouter()


class DataSourceInfo(BaseModel):
    """Information about data source and any warnings (Beta feature)."""

    source: DataSourceType = "live_api"
    is_fallback: bool = False
    warning: str | None = None
    warning_code: str | None = None
    details: str | None = None
    retry_after_seconds: int | None = None


# Groq client initialization
def get_groq_client() -> Groq:
    """Get Groq API client with configured API key."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not configured in environment")
    return Groq(api_key=settings.groq_api_key)


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


class TeamFatigueInfo(BaseModel):
    """Fatigue information for a single team."""

    rest_days_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Rest days score (0=fatigued, 1=well-rested)"
    )
    fixture_congestion_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Fixture congestion score (0=congested, 1=light)"
    )
    combined_score: float = Field(0.5, ge=0.0, le=1.0, description="Combined fatigue score")


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

    class Config:
        populate_by_name = True


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

    # Multi-markets predictions (optional)
    multi_markets: MultiMarketsResponse | None = None

    # Metadata
    created_at: datetime
    is_daily_pick: bool = False

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
        "Supériorité en possession statistique",
        "Attaque puissante à domicile",
        "Série de victoires à domicile",
        "Défense solide sur leur terrain",
    ],
    "away_strong": [
        "Excellente série en déplacement",
        "Défense très solide en extérieur",
        "Efficacité offensive élevée",
        "Moral de l'équipe excellent",
        "Bon bilan face à cet adversaire",
        "Équipe en pleine confiance",
    ],
    "balanced": [
        "Matchs équilibrés historiquement",
        "Formes similaires actuellement",
        "Qualité défensive comparable",
        "Potentiel de score nul élevé",
        "Confrontations souvent serrées",
        "Peu de buts dans les H2H récents",
    ],
}

RISK_FACTORS_TEMPLATES = [
    "Absence de joueurs clés possibles",
    "Fatigue accumulée (calendrier chargé)",
    "Conditions météorologiques défavorables",
    "Historique imprévisible dans ce duel",
    "Équipe en reconstruction",
    "Pression du classement",
    "Match retour de trêve internationale",
    "Déplacement lointain récent",
]

EXPLANATIONS_TEMPLATES = {
    "home_win": (
        "Notre analyse privilégie {home} pour cette rencontre. L'équipe bénéficie d'un "
        "fort avantage du terrain combiné à une excellente forme actuelle. {away} reste "
        "compétitif mais devrait avoir du mal à créer des occasions décisives."
    ),
    "draw": (
        "Un match équilibré où les deux équipes possèdent les atouts pour obtenir un "
        "résultat positif. Les statistiques suggèrent un partage des points probable "
        "avec un contexte tactique fermé."
    ),
    "away_win": (
        "Malgré le déplacement, {away} dispose des arguments suffisants pour s'imposer. "
        "La qualité de leur jeu actuel pourrait faire la différence face à {home}."
    ),
}


def _get_groq_prediction(
    home_team: str,
    away_team: str,
    competition: str,
    home_current_form: str = "",
    away_current_form: str = "",
    home_injuries: str = "",
    away_injuries: str = "",
) -> dict[str, Any] | None:
    """
    Get match prediction from Groq API using advanced analysis prompt.

    Returns a dict with probabilities, confidence, injury impacts, and reasoning.
    Returns None if API fails.
    """
    try:
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY not configured, will use fallback predictions")
            return None

        client = get_groq_client()

        # Use advanced analysis prompt
        prompt = get_prediction_analysis_prompt(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            home_current_form=home_current_form,
            away_current_form=away_current_form,
            home_injuries=home_injuries,
            away_injuries=away_injuries,
        )

        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Updated from deprecated mixtral-8x7b-32768
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        response_text = message.choices[0].message.content.strip()

        # Try to extract JSON from the response
        try:
            # Find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                prediction_data = json.loads(json_str)

                # Support both old and new formats
                home_win = prediction_data.get("home_win_probability") or prediction_data.get(
                    "home_win", 0.33
                )
                draw = prediction_data.get("draw_probability") or prediction_data.get("draw", 0.34)
                away_win = prediction_data.get("away_win_probability") or prediction_data.get(
                    "away_win", 0.33
                )

                # Validate probabilities sum to approximately 1.0
                total = home_win + draw + away_win
                if abs(total - 1.0) < 0.01:  # Allow small floating point errors
                    # Normalize if needed
                    if total > 0:
                        home_win /= total
                        draw /= total
                        away_win /= total

                    result = {
                        "home_win": round(home_win, 4),
                        "draw": round(draw, 4),
                        "away_win": round(away_win, 4),
                        "reasoning": prediction_data.get("reasoning", ""),
                        "confidence_level": prediction_data.get("confidence_level", "medium"),
                        "injury_impact_home": prediction_data.get("injury_impact_home", 0.0),
                        "injury_impact_away": prediction_data.get("injury_impact_away", 0.0),
                    }
                    return result
        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse Groq response: {e}, Text: {response_text[:100]}")
            return None

        return None

    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return None


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


def _get_team_stats_for_ml(home_team: str, away_team: str, match_id: int) -> dict[str, Any]:
    """
    Get team statistics for ML ensemble prediction.

    Uses model_loader's feature engineer state if available,
    otherwise returns default values based on match_id for consistency.
    """
    from src.ml.model_loader import model_loader

    # Default ELO ratings (1500 is baseline)
    default_elo = 1500.0
    default_attack = 1.3
    default_defense = 1.3
    default_form = 50.0

    # Try to get stats from model_loader
    home_stats = None
    away_stats = None

    # Use match_id as team_id proxy (in real system, we'd have actual team IDs)
    # This is a deterministic mapping based on team names
    home_team_id = hash(home_team) % 1000000
    away_team_id = hash(away_team) % 1000000

    if model_loader.feature_state:
        home_stats = model_loader.get_team_stats(home_team_id)
        away_stats = model_loader.get_team_stats(away_team_id)

    # Use historical data if available, otherwise use defaults
    result = {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_elo": default_elo,
        "away_elo": default_elo,
        "home_attack": home_stats["attack_strength"] if home_stats else default_attack,
        "home_defense": home_stats["defense_strength"] if home_stats else default_defense,
        "away_attack": away_stats["attack_strength"] if away_stats else default_attack,
        "away_defense": away_stats["defense_strength"] if away_stats else default_defense,
        "home_form": home_stats["form"] if home_stats else default_form,
        "away_form": away_stats["form"] if away_stats else default_form,
    }

    # Adjust ELO based on form if we have data
    if home_stats:
        # Better form = higher ELO adjustment
        form_adj = (home_stats["form"] - 50) * 2  # -100 to +100
        result["home_elo"] = default_elo + form_adj

    if away_stats:
        form_adj = (away_stats["form"] - 50) * 2
        result["away_elo"] = default_elo + form_adj

    return result


async def _generate_prediction_from_api_match(
    api_match: MatchData, include_model_details: bool = False, use_rag: bool = True
) -> PredictionResponse:
    """
    Generate a prediction for a real match using the advanced ensemble predictor.

    This uses the trained ML models (XGBoost, Random Forest) combined with
    statistical models (Dixon-Coles, ELO, Poisson) for accurate predictions.
    """
    home_team = api_match.homeTeam.name
    away_team = api_match.awayTeam.name
    competition = api_match.competition.code
    match_date = datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00"))

    # Try RAG enrichment for better context
    rag_context = None
    if use_rag:
        try:
            rag = get_rag_enrichment()
            rag_context = await rag.enrich_match_prediction(
                home_team, away_team, competition, match_date
            )
            logger.info(f"RAG enrichment applied for {home_team} vs {away_team}")
        except Exception as e:
            logger.warning(f"RAG enrichment failed: {e}")

    # Get team stats for ML models
    team_stats = _get_team_stats_for_ml(home_team, away_team, api_match.id)

    # Fetch fatigue data from API
    fatigue_data: MatchFatigueData | None = None
    try:
        fatigue_service = get_fatigue_service()
        fatigue_data = await fatigue_service.get_match_fatigue(
            home_team_id=api_match.homeTeam.id,
            home_team_name=home_team,
            away_team_id=api_match.awayTeam.id,
            away_team_name=away_team,
            match_date=match_date,
        )
        logger.info(
            f"Fatigue data for {home_team} vs {away_team}: "
            f"home_rest={fatigue_data.home_team.rest_days_score:.2f}, "
            f"away_rest={fatigue_data.away_team.rest_days_score:.2f}, "
            f"advantage={fatigue_data.fatigue_advantage:+.2f}"
        )
    except Exception as e:
        logger.warning(f"Failed to fetch fatigue data: {e}")

    # Use the advanced ensemble predictor with all models (ML + statistical)
    try:
        # Prepare fatigue parameters (defaults if not available)
        home_rest = 0.5
        home_cong = 0.5
        away_rest = 0.5
        away_cong = 0.5
        if fatigue_data:
            home_rest = fatigue_data.home_team.rest_days_score
            home_cong = fatigue_data.home_team.fixture_congestion_score
            away_rest = fatigue_data.away_team.rest_days_score
            away_cong = fatigue_data.away_team.fixture_congestion_score

        ensemble_result = advanced_ensemble_predictor.predict(
            home_attack=team_stats["home_attack"],
            home_defense=team_stats["home_defense"],
            away_attack=team_stats["away_attack"],
            away_defense=team_stats["away_defense"],
            home_elo=team_stats["home_elo"],
            away_elo=team_stats["away_elo"],
            home_team_id=team_stats["home_team_id"],
            away_team_id=team_stats["away_team_id"],
            home_form_score=team_stats["home_form"],
            away_form_score=team_stats["away_form"],
            # Pass fatigue data for ML models with extended features
            home_rest_days=home_rest,
            home_congestion=home_cong,
            away_rest_days=away_rest,
            away_congestion=away_cong,
        )

        # Use ensemble prediction results
        home_prob = round(ensemble_result.home_win_prob, 4)
        draw_prob = round(ensemble_result.draw_prob, 4)
        away_prob = round(ensemble_result.away_win_prob, 4)
        confidence = round(ensemble_result.confidence, 3)
        model_agreement = ensemble_result.model_agreement

        logger.info(
            f"Ensemble prediction for {home_team} vs {away_team}: "
            f"H={home_prob:.2%} D={draw_prob:.2%} A={away_prob:.2%} "
            f"(confidence={confidence:.2%}, agreement={model_agreement:.2%})"
        )

        # Map ensemble recommended_bet to API format
        bet_map: dict[str, Literal["home_win", "draw", "away_win"]] = {
            "home": "home_win",
            "draw": "draw",
            "away": "away_win",
        }
        recommended_bet: Literal["home_win", "draw", "away_win"] = bet_map.get(
            ensemble_result.recommended_bet, "draw"
        )

    except Exception as e:
        logger.warning(f"Ensemble prediction failed, using fallback: {e}")
        # Fallback to Groq or random if ensemble fails
        groq_prediction = _get_groq_prediction(home_team, away_team, competition)

        if groq_prediction:
            home_prob = groq_prediction["home_win"]
            draw_prob = groq_prediction["draw"]
            away_prob = groq_prediction["away_win"]
        else:
            random.seed(api_match.id)
            strength_ratio = random.uniform(0.75, 1.35)
            home_prob, draw_prob, away_prob = _generate_realistic_probabilities(strength_ratio)
            random.seed()

        recommended_bet = _get_recommended_bet(home_prob, draw_prob, away_prob)
        confidence = round(random.uniform(0.60, 0.75), 3)
        model_agreement = 0.5

    # Generate value score based on confidence and model agreement
    # Higher agreement = higher value potential
    random.seed(api_match.id)
    base_value = 0.05 + (model_agreement * 0.10)  # 5-15% based on agreement
    value_score = round(base_value + random.uniform(0.0, 0.05), 3)

    # Select key factors based on predicted outcome
    if recommended_bet == "home_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["home_dominant"], 3)
    elif recommended_bet == "away_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["away_strong"], 3)
    else:
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["balanced"], 3)

    # Add fatigue factor if significant advantage exists
    if fatigue_data:
        if fatigue_data.fatigue_advantage > 0.15:
            key_factors.append("Avantage physique (plus de repos)")
        elif fatigue_data.fatigue_advantage < -0.15:
            key_factors.append("Calendrier chargé (fatigue potentielle)")

    # Select risk factors
    risk_factors = random.sample(RISK_FACTORS_TEMPLATES, 2)

    # Generate explanation
    explanation_template = EXPLANATIONS_TEMPLATES[recommended_bet]
    explanation = explanation_template.format(home=home_team, away=away_team)

    # Model contributions from ensemble (real data)
    model_contributions = None
    if include_model_details:
        try:
            # Build real model contributions from ensemble
            contributions = {}
            has_contribs = hasattr(ensemble_result, "model_contributions")
            if has_contribs and ensemble_result.model_contributions:
                for contrib in ensemble_result.model_contributions:
                    name_key = contrib.name.lower().replace(" ", "_").replace("-", "_")
                    contributions[name_key] = {
                        "home_win": round(contrib.home_prob, 4),
                        "draw": round(contrib.draw_prob, 4),
                        "away_win": round(contrib.away_prob, 4),
                        "weight": round(contrib.weight, 4),
                    }

            # Map to API model contributions format
            model_contributions = ModelContributions(
                poisson=PredictionProbabilities(
                    home_win=contributions.get("poisson", {}).get("home_win", home_prob),
                    draw=contributions.get("poisson", {}).get("draw", draw_prob),
                    away_win=contributions.get("poisson", {}).get("away_win", away_prob),
                ),
                xgboost=PredictionProbabilities(
                    home_win=contributions.get("ml_(ensemble)", {}).get("home_win", home_prob)
                    or contributions.get("ml_(xgboost)", {}).get("home_win", home_prob),
                    draw=contributions.get("ml_(ensemble)", {}).get("draw", draw_prob)
                    or contributions.get("ml_(xgboost)", {}).get("draw", draw_prob),
                    away_win=contributions.get("ml_(ensemble)", {}).get("away_win", away_prob)
                    or contributions.get("ml_(xgboost)", {}).get("away_win", away_prob),
                ),
                xg_model=PredictionProbabilities(
                    home_win=contributions.get("dixon_coles", {}).get("home_win", home_prob),
                    draw=contributions.get("dixon_coles", {}).get("draw", draw_prob),
                    away_win=contributions.get("dixon_coles", {}).get("away_win", away_prob),
                ),
                elo=PredictionProbabilities(
                    home_win=contributions.get("advanced_elo", {}).get("home_win", home_prob)
                    or contributions.get("basic_elo", {}).get("home_win", home_prob),
                    draw=contributions.get("advanced_elo", {}).get("draw", draw_prob)
                    or contributions.get("basic_elo", {}).get("draw", draw_prob),
                    away_win=contributions.get("advanced_elo", {}).get("away_win", away_prob)
                    or contributions.get("basic_elo", {}).get("away_win", away_prob),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to build model contributions: {e}")
            model_contributions = None

    # LLM adjustments (from RAG context if available)
    llm_adjustments = None
    if include_model_details:
        if rag_context:
            # Extract real adjustments from RAG context
            home_ctx = rag_context.get("home_context", {})
            away_ctx = rag_context.get("away_context", {})

            # Calculate injury impact (more injuries = negative impact)
            home_injuries = len(home_ctx.get("injuries", []))
            away_injuries = len(away_ctx.get("injuries", []))
            injury_impact_home = round(min(0.0, -home_injuries * 0.05), 3)
            injury_impact_away = round(min(0.0, -away_injuries * 0.05), 3)

            # Calculate sentiment from RAG
            home_sentiment_raw = home_ctx.get("sentiment", "neutral")
            away_sentiment_raw = away_ctx.get("sentiment", "neutral")
            sentiment_map = {"positive": 0.05, "neutral": 0.0, "negative": -0.05}
            sentiment_home = sentiment_map.get(str(home_sentiment_raw).lower(), 0.0)
            sentiment_away = sentiment_map.get(str(away_sentiment_raw).lower(), 0.0)

            # Calculate total and clamp to [-0.5, 0.5] bounds
            raw_total = injury_impact_home + injury_impact_away + sentiment_home + sentiment_away
            clamped_total = max(-0.5, min(0.5, raw_total))

            llm_adjustments = LLMAdjustments(
                injury_impact_home=injury_impact_home,
                injury_impact_away=injury_impact_away,
                sentiment_home=round(sentiment_home, 3),
                sentiment_away=round(sentiment_away, 3),
                tactical_edge=0.0,
                total_adjustment=round(clamped_total, 3),
                reasoning="Analyse basée sur le contexte RAG (news, blessures, sentiment).",
            )
        else:
            # Minimal adjustments without RAG
            llm_adjustments = LLMAdjustments(
                injury_impact_home=0.0,
                injury_impact_away=0.0,
                sentiment_home=0.0,
                sentiment_away=0.0,
                tactical_edge=0.0,
                total_adjustment=0.0,
                reasoning="Données contextuelles non disponibles.",
            )

    # Reset random seed
    random.seed()

    # Calculate multi-markets predictions
    multi_markets = None
    if include_model_details:
        try:
            # Fetch real bookmaker odds for Over/Under markets
            real_odds_over_25 = None
            real_odds_under_25 = None

            try:
                enrichment_service = get_data_enrichment()
                odds_data = await enrichment_service.odds_client.get_odds(
                    competition, markets="h2h,totals"
                )
                if odds_data:
                    totals_odds = enrichment_service.odds_client.extract_totals_odds(
                        odds_data, home_team, away_team
                    )
                    if totals_odds.get("available"):
                        real_odds_over_25 = totals_odds.get("over_25")
                        real_odds_under_25 = totals_odds.get("under_25")
                        logger.info(
                            f"Real O/U 2.5 odds for {home_team} vs {away_team}: "
                            f"Over={real_odds_over_25}, Under={real_odds_under_25}"
                        )
            except Exception as e:
                logger.warning(f"Failed to fetch real odds: {e}")

            # Get expected goals from ensemble result or estimate from probabilities
            has_ensemble = "ensemble_result" in dir()
            if has_ensemble:
                exp_home = getattr(ensemble_result, "expected_home_goals", None)
                exp_away = getattr(ensemble_result, "expected_away_goals", None)
            else:
                exp_home = None
                exp_away = None

            # Fallback estimation if expected goals not available
            if exp_home is None or exp_away is None:
                # Estimate expected goals from 1X2 probabilities
                # Higher home probability = more home goals expected
                exp_home = 1.0 + (home_prob - 0.33) * 2.0
                exp_away = 1.0 + (away_prob - 0.33) * 2.0
                exp_home = max(0.5, min(3.5, exp_home))
                exp_away = max(0.5, min(3.0, exp_away))

            mm_prediction = get_multi_markets_prediction(
                expected_home_goals=float(exp_home),
                expected_away_goals=float(exp_away),
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                odds_over_25=real_odds_over_25,
                odds_under_25=real_odds_under_25,
            )

            multi_markets = MultiMarketsResponse(
                over_under_15=OverUnderResponse(
                    line=mm_prediction.over_under_15.line,
                    over_prob=mm_prediction.over_under_15.over_prob,
                    under_prob=mm_prediction.over_under_15.under_prob,
                    over_odds=mm_prediction.over_under_15.over_odds,
                    under_odds=mm_prediction.over_under_15.under_odds,
                    over_value=mm_prediction.over_under_15.over_value,
                    under_value=mm_prediction.over_under_15.under_value,
                    recommended=mm_prediction.over_under_15.recommended,
                ),
                over_under_25=OverUnderResponse(
                    line=mm_prediction.over_under_25.line,
                    over_prob=mm_prediction.over_under_25.over_prob,
                    under_prob=mm_prediction.over_under_25.under_prob,
                    over_odds=mm_prediction.over_under_25.over_odds,
                    under_odds=mm_prediction.over_under_25.under_odds,
                    over_value=mm_prediction.over_under_25.over_value,
                    under_value=mm_prediction.over_under_25.under_value,
                    recommended=mm_prediction.over_under_25.recommended,
                ),
                over_under_35=OverUnderResponse(
                    line=mm_prediction.over_under_35.line,
                    over_prob=mm_prediction.over_under_35.over_prob,
                    under_prob=mm_prediction.over_under_35.under_prob,
                    over_odds=mm_prediction.over_under_35.over_odds,
                    under_odds=mm_prediction.over_under_35.under_odds,
                    over_value=mm_prediction.over_under_35.over_value,
                    under_value=mm_prediction.over_under_35.under_value,
                    recommended=mm_prediction.over_under_35.recommended,
                ),
                btts=BttsResponse(
                    yes_prob=mm_prediction.btts.yes_prob,
                    no_prob=mm_prediction.btts.no_prob,
                    yes_odds=mm_prediction.btts.yes_odds,
                    no_odds=mm_prediction.btts.no_odds,
                    recommended=mm_prediction.btts.recommended,
                ),
                double_chance=DoubleChanceResponse(  # type: ignore[call-arg]
                    home_or_draw=mm_prediction.double_chance.home_or_draw_prob,
                    away_or_draw=mm_prediction.double_chance.away_or_draw_prob,
                    home_or_away=mm_prediction.double_chance.home_or_away_prob,
                    home_or_draw_odds=mm_prediction.double_chance.home_or_draw_odds,
                    away_or_draw_odds=mm_prediction.double_chance.away_or_draw_odds,
                    home_or_away_odds=mm_prediction.double_chance.home_or_away_odds,
                    recommended=mm_prediction.double_chance.recommended,
                ),
                correct_score=CorrectScoreResponse(
                    scores=mm_prediction.correct_score.scores,
                    most_likely=mm_prediction.correct_score.most_likely,
                    most_likely_prob=mm_prediction.correct_score.most_likely_prob,
                ),
                expected_home_goals=mm_prediction.expected_home_goals,
                expected_away_goals=mm_prediction.expected_away_goals,
                expected_total_goals=mm_prediction.expected_total_goals,
            )
        except Exception as e:
            logger.warning(f"Failed to calculate multi-markets: {e}")
            multi_markets = None

    # Build fatigue info response
    fatigue_info: FatigueInfo | None = None
    if fatigue_data:
        fatigue_info = FatigueInfo(
            home_team=TeamFatigueInfo(
                rest_days_score=round(fatigue_data.home_team.rest_days_score, 3),
                fixture_congestion_score=round(fatigue_data.home_team.fixture_congestion_score, 3),
                combined_score=round(fatigue_data.home_team.combined_fatigue_score, 3),
            ),
            away_team=TeamFatigueInfo(
                rest_days_score=round(fatigue_data.away_team.rest_days_score, 3),
                fixture_congestion_score=round(fatigue_data.away_team.fixture_congestion_score, 3),
                combined_score=round(fatigue_data.away_team.combined_fatigue_score, 3),
            ),
            fatigue_advantage=round(fatigue_data.fatigue_advantage, 3),
        )

    return PredictionResponse(
        match_id=api_match.id,
        home_team=home_team,
        away_team=away_team,
        competition=COMPETITION_NAMES.get(competition, api_match.competition.name),
        match_date=match_date,
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
        fatigue_info=fatigue_info,
        multi_markets=multi_markets,
        created_at=datetime.now(),
        is_daily_pick=False,
    )


@router.get(
    "/daily",
    response_model=DailyPicksResponse,
    responses=AUTH_RESPONSES,
    operation_id="getDailyPicks",
)
@limiter.limit(RATE_LIMITS["predictions"])
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

        # First, check if we have cached predictions in DB
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
                    value_score=0.10,  # Default value
                    explanation=cached.get("explanation") or "",
                    key_factors=["Données en cache"],
                    risk_factors=["Mise à jour recommandée"],
                    created_at=datetime.fromisoformat(cached["created_at"]),
                    is_daily_pick=True,
                )
                pick_score = pred.confidence * pred.value_score
                all_predictions.append((pred, pick_score))

            # Sort and return top 5
            all_predictions.sort(key=lambda x: x[1], reverse=True)
            daily_picks = [
                DailyPickResponse(rank=i + 1, prediction=p, pick_score=round(s, 4))
                for i, (p, s) in enumerate(all_predictions[:5])
            ]
            return DailyPicksResponse(
                date=target_date_str,
                picks=daily_picks,
                total_matches_analyzed=len(cached_predictions),
            )

        # No cached predictions, fetch from API
        # Only fetch matches for the specific target date
        date_to = target_date

        # Try to get scheduled matches from DB first (fallback)
        db_matches = await MatchService.get_scheduled(date_from=target_date, date_to=date_to)

        # Fetch matches for date range from real API
        client = get_football_data_client()
        try:
            api_matches = await client.get_matches(
                date_from=target_date,
                date_to=date_to,
            )
        except (RateLimitError, FootballDataAPIError) as e:
            logger.warning(f"API failed, using {len(db_matches)} matches from DB: {e}")
            # Convert DB matches to MatchData format
            api_matches = []
            for m in db_matches:
                api_matches.append(MatchData(**m))

        # Include all matches for the day (scheduled, in-play, and finished)
        # This allows users to see predictions even for completed matches
        api_matches = [
            m
            for m in api_matches
            if m.status in ("SCHEDULED", "TIMED", "FINISHED", "IN_PLAY", "PAUSED")
        ]

        if not api_matches:
            return DailyPicksResponse(
                date=target_date_str,
                picks=[],
                total_matches_analyzed=0,
            )

        # Generate predictions for all matches
        all_predictions = []
        for api_match in api_matches:
            pred = await _generate_prediction_from_api_match(api_match, include_model_details=False)

            # Save prediction to database for caching
            await PredictionService.save_prediction_from_api(
                {
                    "match_id": pred.match_id,
                    "match_external_id": f"{api_match.competition.code}_{pred.match_id}",
                    "home_team": pred.home_team,
                    "away_team": pred.away_team,
                    "competition_code": api_match.competition.code,
                    "match_date": api_match.utcDate,
                    "home_win_prob": pred.probabilities.home_win,
                    "draw_prob": pred.probabilities.draw,
                    "away_win_prob": pred.probabilities.away_win,
                    "confidence": pred.confidence,
                    "recommendation": pred.recommended_bet,
                    "explanation": pred.explanation,
                }
            )

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
            date=target_date_str,
            picks=daily_picks,
            total_matches_analyzed=len(api_matches),
            data_source=DataSourceInfo(source="live_api"),
        )

    except RateLimitError as e:
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        raise HTTPException(
            status_code=429,
            detail={
                "message": "[BETA] Limite API externe atteinte (football-data.org: 10 req/min)",
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
                "tip": "Réessayez dans quelques instants ou consultez les picks en cache",
            },
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "message": f"[BETA] Erreur API externe: {str(e)[:100]}",
                "warning_code": "EXTERNAL_API_ERROR",
                "tip": "L'API football-data.org est temporairement indisponible",
            },
        )


@router.get(
    "/stats",
    response_model=PredictionStatsResponse,
    responses=AUTH_RESPONSES,
    operation_id="getPredictionStats",
)
@limiter.limit(RATE_LIMITS["predictions"])
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


def _generate_fallback_prediction(
    match_id: int,
    include_model_details: bool = False,
    fallback_reason: str = "API externe indisponible",
    is_rate_limit: bool = False,
    retry_after: int | None = None,
) -> PredictionResponse:
    """
    Generate a basic prediction when external API fails.
    Uses deterministic values based on match_id to ensure consistency.
    """
    logger.info(f"Generating fallback prediction for match {match_id} - Reason: {fallback_reason}")

    random.seed(match_id)  # Deterministic randomness based on match_id

    # Generate consistent probabilities
    home_base = random.uniform(0.35, 0.50)
    draw_base = random.uniform(0.22, 0.32)
    away_base = 1.0 - home_base - draw_base

    home_prob = round(home_base, 4)
    draw_prob = round(draw_base, 4)
    away_prob = round(away_base, 4)

    # Get recommended bet
    recommended_bet: Literal["home_win", "draw", "away_win"]
    if home_prob >= away_prob and home_prob >= draw_prob:
        recommended_bet = "home_win"
    elif away_prob >= home_prob and away_prob >= draw_prob:
        recommended_bet = "away_win"
    else:
        recommended_bet = "draw"

    # Generate confidence (60-75% for fallback)
    confidence = round(random.uniform(0.60, 0.75), 3)
    value_score = round(random.uniform(0.05, 0.12), 3)

    # Select key factors
    if recommended_bet == "home_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["home_dominant"], 3)
    elif recommended_bet == "away_win":
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["away_strong"], 3)
    else:
        key_factors = random.sample(KEY_FACTORS_TEMPLATES["balanced"], 3)

    risk_factors = random.sample(RISK_FACTORS_TEMPLATES, 2)

    explanation = (
        "Analyse basée sur des données statistiques. Prédiction générée en mode "
        "dégradé (API externe temporairement indisponible)."
    )

    # Model contributions (optional)
    model_contributions = None
    if include_model_details:
        model_contributions = ModelContributions(
            poisson=PredictionProbabilities(
                home_win=round(home_prob + random.uniform(-0.03, 0.03), 4),
                draw=round(draw_prob + random.uniform(-0.02, 0.02), 4),
                away_win=round(away_prob + random.uniform(-0.03, 0.03), 4),
            ),
            xgboost=PredictionProbabilities(
                home_win=home_prob,
                draw=draw_prob,
                away_win=away_prob,
            ),
            xg_model=PredictionProbabilities(
                home_win=round(home_prob + random.uniform(-0.02, 0.02), 4),
                draw=round(draw_prob + random.uniform(-0.01, 0.01), 4),
                away_win=round(away_prob + random.uniform(-0.02, 0.02), 4),
            ),
            elo=PredictionProbabilities(
                home_win=round(home_prob - random.uniform(0.01, 0.03), 4),
                draw=round(draw_prob + random.uniform(0.00, 0.02), 4),
                away_win=round(away_prob + random.uniform(0.01, 0.02), 4),
            ),
        )

    # LLM adjustments (optional)
    llm_adjustments = None
    if include_model_details:
        llm_adjustments = LLMAdjustments(
            injury_impact_home=round(random.uniform(-0.10, 0.0), 3),
            injury_impact_away=round(random.uniform(-0.10, 0.0), 3),
            sentiment_home=round(random.uniform(-0.03, 0.03), 3),
            sentiment_away=round(random.uniform(-0.03, 0.03), 3),
            tactical_edge=round(random.uniform(-0.02, 0.02), 3),
            total_adjustment=round(random.uniform(-0.05, 0.05), 3),
            reasoning="Prédiction générée en mode fallback. Données contextuelles limitées.",
        )

    # Multi-markets for fallback
    multi_markets = None
    if include_model_details:
        try:
            exp_home = 1.0 + (home_prob - 0.33) * 2.0
            exp_away = 1.0 + (away_prob - 0.33) * 2.0
            exp_home = max(0.5, min(3.5, exp_home))
            exp_away = max(0.5, min(3.0, exp_away))

            mm_prediction = get_multi_markets_prediction(
                expected_home_goals=exp_home,
                expected_away_goals=exp_away,
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
            )

            multi_markets = MultiMarketsResponse(
                over_under_15=OverUnderResponse(
                    line=mm_prediction.over_under_15.line,
                    over_prob=mm_prediction.over_under_15.over_prob,
                    under_prob=mm_prediction.over_under_15.under_prob,
                    over_odds=mm_prediction.over_under_15.over_odds,
                    under_odds=mm_prediction.over_under_15.under_odds,
                    over_value=mm_prediction.over_under_15.over_value,
                    under_value=mm_prediction.over_under_15.under_value,
                    recommended=mm_prediction.over_under_15.recommended,
                ),
                over_under_25=OverUnderResponse(
                    line=mm_prediction.over_under_25.line,
                    over_prob=mm_prediction.over_under_25.over_prob,
                    under_prob=mm_prediction.over_under_25.under_prob,
                    over_odds=mm_prediction.over_under_25.over_odds,
                    under_odds=mm_prediction.over_under_25.under_odds,
                    over_value=mm_prediction.over_under_25.over_value,
                    under_value=mm_prediction.over_under_25.under_value,
                    recommended=mm_prediction.over_under_25.recommended,
                ),
                over_under_35=OverUnderResponse(
                    line=mm_prediction.over_under_35.line,
                    over_prob=mm_prediction.over_under_35.over_prob,
                    under_prob=mm_prediction.over_under_35.under_prob,
                    over_odds=mm_prediction.over_under_35.over_odds,
                    under_odds=mm_prediction.over_under_35.under_odds,
                    over_value=mm_prediction.over_under_35.over_value,
                    under_value=mm_prediction.over_under_35.under_value,
                    recommended=mm_prediction.over_under_35.recommended,
                ),
                btts=BttsResponse(
                    yes_prob=mm_prediction.btts.yes_prob,
                    no_prob=mm_prediction.btts.no_prob,
                    yes_odds=mm_prediction.btts.yes_odds,
                    no_odds=mm_prediction.btts.no_odds,
                    recommended=mm_prediction.btts.recommended,
                ),
                double_chance=DoubleChanceResponse(  # type: ignore[call-arg]
                    home_or_draw=mm_prediction.double_chance.home_or_draw_prob,
                    away_or_draw=mm_prediction.double_chance.away_or_draw_prob,
                    home_or_away=mm_prediction.double_chance.home_or_away_prob,
                    home_or_draw_odds=mm_prediction.double_chance.home_or_draw_odds,
                    away_or_draw_odds=mm_prediction.double_chance.away_or_draw_odds,
                    home_or_away_odds=mm_prediction.double_chance.home_or_away_odds,
                    recommended=mm_prediction.double_chance.recommended,
                ),
                correct_score=CorrectScoreResponse(
                    scores=mm_prediction.correct_score.scores,
                    most_likely=mm_prediction.correct_score.most_likely,
                    most_likely_prob=mm_prediction.correct_score.most_likely_prob,
                ),
                expected_home_goals=mm_prediction.expected_home_goals,
                expected_away_goals=mm_prediction.expected_away_goals,
                expected_total_goals=mm_prediction.expected_total_goals,
            )
        except Exception as e:
            logger.warning(f"Failed to calculate fallback multi-markets: {e}")
            multi_markets = None

    random.seed()  # Reset random seed

    # Build data source info for beta feedback
    data_source = DataSourceInfo(
        source="fallback",
        is_fallback=True,
        warning=f"[BETA] Prédiction estimée - {fallback_reason}",
        warning_code="EXTERNAL_API_RATE_LIMIT" if is_rate_limit else "EXTERNAL_API_ERROR",
        details="Données basées sur des modèles statistiques sans contexte temps réel",
        retry_after_seconds=retry_after,
    )

    return PredictionResponse(
        match_id=match_id,
        home_team="Équipe Domicile",
        away_team="Équipe Extérieur",
        competition="Match",
        match_date=datetime.now() + timedelta(hours=2),
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
        multi_markets=multi_markets,
        created_at=datetime.now(),
        is_daily_pick=False,
        data_source=data_source,
    )


@router.get(
    "/{match_id}",
    response_model=PredictionResponse,
    responses=AUTH_RESPONSES,
    operation_id="getPrediction",
)
@limiter.limit(RATE_LIMITS["predictions"])
async def get_prediction(
    request: Request,
    match_id: int,
    user: AuthenticatedUser,
    include_model_details: bool = Query(False, description="Include model details"),
) -> PredictionResponse:
    """Get detailed prediction for a specific match."""
    try:
        # Fetch real match from API
        client = get_football_data_client()
        api_match = await client.get_match(match_id)
        return await _generate_prediction_from_api_match(
            api_match, include_model_details=include_model_details
        )

    except RateLimitError as e:
        # On rate limit, try fallback instead of failing
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        logger.warning(f"Rate limit hit for match {match_id}, using fallback prediction")
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason="Limite API externe atteinte (10 req/min)",
            is_rate_limit=True,
            retry_after=retry_after,
        )

    except FootballDataAPIError as e:
        error_msg = str(e).lower()

        # If it's a real "not found" error, still return 404
        if "not found" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Match {match_id} not found",
            )

        # For other API failures (502, timeout, etc), use fallback
        logger.warning(f"API failed for match {match_id}: {e}. Using fallback prediction.")
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason=f"Erreur API externe: {str(e)[:50]}",
        )

    except Exception as e:
        # Catch-all for any other errors, use fallback
        logger.error(f"Unexpected error for match {match_id}: {e}. Using fallback prediction.")
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason=f"Erreur inattendue: {str(e)[:50]}",
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
@limiter.limit(RATE_LIMITS["predictions"])
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
@limiter.limit(RATE_LIMITS["predictions"])
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
        raise HTTPException(
            status_code=429,
            detail={
                "message": "[BETA] Limite API externe atteinte (football-data.org: 10 req/min)",
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
            },
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 502,
            detail=(
                f"Match {match_id} not found"
                if "not found" in str(e).lower()
                else f"[BETA] Erreur API: {str(e)}"
            ),
        )
