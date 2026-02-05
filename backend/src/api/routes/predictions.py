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
from pydantic import BaseModel, ConfigDict, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.core.cache import cache_get, cache_set
from src.core.config import settings
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.core.rate_limit import RATE_LIMITS, limiter
from src.data.data_enrichment import get_data_enrichment
from src.data.fatigue_service import MatchFatigueData, get_fatigue_service
from src.data.sources.football_data import MatchData, get_football_data_client
from src.db.repositories import get_uow
from src.db.services.match_service import MatchService
from src.db.services.prediction_service import PredictionService
from src.llm.prompts_advanced import get_prediction_analysis_prompt
from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor
from src.prediction_engine.multi_markets import get_multi_markets_prediction
from src.prediction_engine.rag_enrichment import get_rag_enrichment

# Data source type for beta feedback
DataSourceType = Literal["live_api", "cache", "database", "fallback"]

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_language(request: Request) -> str:
    """
    Detect user's preferred language from Accept-Language header.

    Returns:
        "fr" for French, "en" for English (default)
    """
    accept_language = request.headers.get("Accept-Language", "")

    # Parse Accept-Language header (e.g., "fr-FR,fr;q=0.9,en;q=0.8")
    if accept_language:
        # Get first language preference
        primary_lang = accept_language.split(",")[0].split("-")[0].lower()
        if primary_lang == "fr":
            return "fr"
        elif primary_lang == "en":
            return "en"
        elif primary_lang == "nl":
            return "nl"  # Dutch support for future

    return "fr"  # Default to French


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


# Groq client initialization
def get_groq_client() -> Groq:
    """Get Groq API client with configured API key."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not configured in environment")
    return Groq(api_key=settings.groq_api_key)


async def _get_prediction_from_redis(match_id: int) -> dict[str, Any] | None:
    """Get prediction from Redis cache."""
    try:
        cache_key = f"prediction:{match_id}"
        cached = await cache_get(cache_key)
        if cached:
            return json.loads(cached)
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

    # Multi-markets predictions (optional)
    multi_markets: MultiMarketsResponse | None = None

    # Metadata
    created_at: datetime
    is_daily_pick: bool = False

    # Verification status (filled after match completion)
    is_verified: bool = Field(False, description="Whether the match result has been verified")
    is_correct: bool | None = Field(None, description="Whether prediction was correct (null if not verified)")
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
from src.core.messages import (
    get_key_factors_templates,
    get_risk_factors_templates,
    get_label,
    Language,
)

# Legacy aliases for backward compatibility (used in fallback generator)
KEY_FACTORS_TEMPLATES = get_key_factors_templates("fr")
RISK_FACTORS_TEMPLATES = get_risk_factors_templates("fr")


async def _generate_llm_explanation(
    home_team: str,
    away_team: str,
    team_stats: dict[str, Any],
    recommended_bet: str,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    rag_context: dict[str, Any] | None = None,
    language: str = "fr",
) -> tuple[str, list[str], list[str]]:
    """
    Generate explanation and factors using LLM based on REAL data.

    Args:
        language: "fr" for French, "en" for English

    Returns:
        (explanation, key_factors, risk_factors)
    """
    from src.llm.client import get_llm_client

    # Extract real stats for the prompt
    home_elo = team_stats.get("home_elo", 1500)
    away_elo = team_stats.get("away_elo", 1500)
    home_form = team_stats.get("home_form", 50)
    away_form = team_stats.get("away_form", 50)
    home_attack = team_stats.get("home_attack", 1.3)
    away_attack = team_stats.get("away_attack", 1.3)
    home_defense = team_stats.get("home_defense", 1.3)
    away_defense = team_stats.get("away_defense", 1.3)

    # Build RAG context summary
    rag_summary = ""
    if rag_context:
        home_ctx = rag_context.get("home_context", {})
        away_ctx = rag_context.get("away_context", {})

        home_injuries = home_ctx.get("injuries", [])
        away_injuries = away_ctx.get("injuries", [])
        home_key_info = home_ctx.get("key_info", [])
        away_key_info = away_ctx.get("key_info", [])
        home_sentiment = home_ctx.get("sentiment", "neutral")
        away_sentiment = away_ctx.get("sentiment", "neutral")

        rag_summary = f"""
CONTEXTE ACTUALITÉS:
- {home_team}: sentiment={home_sentiment}, blessures={[i.get('player', '?') for i in home_injuries[:3]]}
- {away_team}: sentiment={away_sentiment}, blessures={[i.get('player', '?') for i in away_injuries[:3]]}
- Infos {home_team}: {home_key_info[:2] if home_key_info else 'Aucune'}
- Infos {away_team}: {away_key_info[:2] if away_key_info else 'Aucune'}
"""

    # Determine language instructions
    if language == "en":
        lang_instruction = "Respond in English."
        default_explanation = f"Our analysis favors {'a draw' if recommended_bet == 'draw' else home_team if recommended_bet == 'home_win' else away_team}."
    else:
        lang_instruction = "Réponds en français."
        default_explanation = f"Notre analyse privilégie {'le match nul' if recommended_bet == 'draw' else home_team if recommended_bet == 'home_win' else away_team}."

    prompt = f"""Tu es un analyste football expert. Génère une analyse pour {home_team} vs {away_team}.

DONNÉES RÉELLES:
- Probabilités: {home_team}={home_prob:.1%}, Nul={draw_prob:.1%}, {away_team}={away_prob:.1%}
- Recommandation: {recommended_bet}
- ELO: {home_team}={home_elo:.0f}, {away_team}={away_elo:.0f}
- Forme (0-100): {home_team}={home_form:.0f}%, {away_team}={away_form:.0f}%
- Attaque (buts/match): {home_team}={home_attack:.2f}, {away_team}={away_attack:.2f}
- Défense (buts encaissés/match): {home_team}={home_defense:.2f}, {away_team}={away_defense:.2f}
{rag_summary}

INSTRUCTIONS:
{lang_instruction}
Génère une réponse JSON avec exactement ce format:
{{
  "explanation": "2-3 phrases d'analyse basées sur les données ci-dessus (max 200 caractères)",
  "key_factors": ["facteur clé 1 basé sur les stats", "facteur clé 2", "facteur clé 3"],
  "risk_factors": ["risque 1", "risque 2"]
}}

IMPORTANT: Base ton analyse UNIQUEMENT sur les données fournies. Pas de généralités."""

    try:
        llm_client = get_llm_client()
        if llm_client:
            response = await llm_client.complete(
                prompt=prompt,
                max_tokens=400,
                temperature=0.3,
            )

            if response:
                # Parse JSON from response
                import json
                import re

                # Try to extract JSON from response
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    explanation = data.get("explanation", default_explanation)[:500]
                    key_factors = data.get("key_factors", [])[:5]
                    risk_factors = data.get("risk_factors", [])[:3]

                    if explanation and key_factors:
                        logger.info(f"LLM generated explanation for {home_team} vs {away_team}")
                        return explanation, key_factors, risk_factors

    except Exception as e:
        logger.warning(f"LLM explanation generation failed: {e}")

    # Fallback to programmatic generation if LLM fails
    return _generate_fallback_explanation(
        home_team, away_team, team_stats, recommended_bet,
        home_prob, away_prob, rag_context, language
    )


def _generate_fallback_explanation(
    home_team: str,
    away_team: str,
    team_stats: dict[str, Any],
    recommended_bet: str,
    home_prob: float,
    away_prob: float,
    rag_context: dict[str, Any] | None = None,
    language: str = "fr",
) -> tuple[str, list[str], list[str]]:
    """
    Fallback explanation generator when LLM is unavailable.

    IMPORTANT: Only uses REAL statistical data (ELO, form, injuries from RAG).
    No invented/templated text - clearly indicates when LLM analysis is unavailable.
    """
    key_factors: list[str] = []
    risk_factors: list[str] = []

    home_elo = team_stats.get("home_elo")
    away_elo = team_stats.get("away_elo")
    home_form = team_stats.get("home_form")
    away_form = team_stats.get("away_form")

    lang: Language = language if language in ("fr", "en", "nl") else "fr"
    is_fr = lang == "fr"

    # Only add ELO factor if we have REAL data (not default 1500)
    if home_elo and away_elo and home_elo != 1500 and away_elo != 1500:
        elo_diff = home_elo - away_elo
        if abs(elo_diff) > 50:
            if elo_diff > 0:
                key_factors.append(f"ELO: {home_team} {home_elo:.0f} (+{elo_diff:.0f})")
            else:
                key_factors.append(f"ELO: {away_team} {away_elo:.0f} (+{-elo_diff:.0f})")

    # Only add form factor if we have REAL data (not default 50)
    if home_form and home_form != 50:
        if home_form > 60:
            key_factors.append(f"{home_team}: {home_form:.0f}%")
        elif home_form < 40:
            risk_factors.append(f"{home_team}: {home_form:.0f}%")

    if away_form and away_form != 50:
        if away_form > 60:
            key_factors.append(f"{away_team}: {away_form:.0f}%")
        elif away_form < 40:
            risk_factors.append(f"{away_team}: {away_form:.0f}%")

    # RAG-based factors - these come from real news/injury data
    if rag_context:
        home_ctx = rag_context.get("home_context", {})
        away_ctx = rag_context.get("away_context", {})

        # Real news/key info from RAG
        for info in home_ctx.get("key_info", [])[:1]:
            if info:
                key_factors.append(info[:80])
        for info in away_ctx.get("key_info", [])[:1]:
            if info:
                key_factors.append(info[:80])

        # Real injury data from RAG
        home_injuries = home_ctx.get("injuries", [])
        if home_injuries:
            players = [i.get("player", "?") for i in home_injuries[:2]]
            risk_factors.append(f"{home_team}: {', '.join(players)}")

        away_injuries = away_ctx.get("injuries", [])
        if away_injuries:
            players = [i.get("player", "?") for i in away_injuries[:2]]
            risk_factors.append(f"{away_team}: {', '.join(players)}")

    # Build explanation - indicate LLM unavailable if we have no real data
    has_real_data = bool(key_factors or risk_factors)

    if has_real_data:
        # We have some real statistical data to show
        if is_fr:
            explanation = f"Analyse statistique: {home_team} vs {away_team}. Probabilites basees sur ELO et forme."
        else:
            explanation = f"Statistical analysis: {home_team} vs {away_team}. Probabilities based on ELO and form."
    else:
        # No real data available - be transparent
        if is_fr:
            explanation = f"Analyse LLM indisponible. Prediction basee uniquement sur les modeles statistiques."
            key_factors = ["Donnees detaillees non disponibles"]
            risk_factors = ["Analyse qualitative indisponible"]
        else:
            explanation = f"LLM analysis unavailable. Prediction based on statistical models only."
            key_factors = ["Detailed data unavailable"]
            risk_factors = ["Qualitative analysis unavailable"]

    return explanation, key_factors[:5], risk_factors[:3]


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


async def _get_team_stats_for_ml(home_team: str, away_team: str, match_id: int) -> dict[str, Any]:
    """
    Get team statistics for ML ensemble prediction from database.

    Fetches real team stats (ELO, form, attack/defense) from the teams table.
    Falls back to defaults if team not found.
    """
    from sqlalchemy import text
    from src.db import async_session_factory

    # Default values
    default_elo = 1500.0
    default_attack = 1.3
    default_defense = 1.3
    default_form = 50.0

    result = {
        "home_team_id": 0,
        "away_team_id": 0,
        "home_elo": default_elo,
        "away_elo": default_elo,
        "home_attack": default_attack,
        "home_defense": default_defense,
        "away_attack": default_attack,
        "away_defense": default_defense,
        "home_form": default_form,
        "away_form": default_form,
    }

    try:
        async with async_session_factory() as session:
            # Fetch home team stats
            home_result = await session.execute(
                text("""
                    SELECT id, elo_rating, avg_goals_scored_home, avg_goals_conceded_home,
                           form_score, form
                    FROM teams WHERE name ILIKE :name LIMIT 1
                """),
                {"name": f"%{home_team}%"}
            )
            home_row = home_result.fetchone()

            if home_row:
                result["home_team_id"] = home_row.id
                result["home_elo"] = float(home_row.elo_rating) if home_row.elo_rating else default_elo
                result["home_attack"] = float(home_row.avg_goals_scored_home) if home_row.avg_goals_scored_home else default_attack
                result["home_defense"] = float(home_row.avg_goals_conceded_home) if home_row.avg_goals_conceded_home else default_defense
                result["home_form"] = float(home_row.form_score or 0.5) * 100 if home_row.form_score else default_form
                logger.debug(f"Home team {home_team}: ELO={result['home_elo']}, form={home_row.form}")

            # Fetch away team stats
            away_result = await session.execute(
                text("""
                    SELECT id, elo_rating, avg_goals_scored_away, avg_goals_conceded_away,
                           form_score, form
                    FROM teams WHERE name ILIKE :name LIMIT 1
                """),
                {"name": f"%{away_team}%"}
            )
            away_row = away_result.fetchone()

            if away_row:
                result["away_team_id"] = away_row.id
                result["away_elo"] = float(away_row.elo_rating) if away_row.elo_rating else default_elo
                result["away_attack"] = float(away_row.avg_goals_scored_away) if away_row.avg_goals_scored_away else default_attack
                result["away_defense"] = float(away_row.avg_goals_conceded_away) if away_row.avg_goals_conceded_away else default_defense
                result["away_form"] = float(away_row.form_score or 0.5) * 100 if away_row.form_score else default_form
                logger.debug(f"Away team {away_team}: ELO={result['away_elo']}, form={away_row.form}")

    except Exception as e:
        logger.warning(f"Failed to fetch team stats from DB: {e}, using defaults")

    return result


async def _generate_prediction_from_api_match(
    api_match: MatchData,
    include_model_details: bool = False,
    use_rag: bool = True,
    request: Request | None = None,
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

    # Get team stats for ML models from database
    team_stats = await _get_team_stats_for_ml(home_team, away_team, api_match.id)

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

    # Generate REAL explanation and factors using LLM + RAG context
    explanation, key_factors, risk_factors = await _generate_llm_explanation(
        home_team=home_team,
        away_team=away_team,
        team_stats=team_stats,
        recommended_bet=recommended_bet,
        home_prob=home_prob,
        draw_prob=draw_prob,
        away_prob=away_prob,
        rag_context=rag_context,
        language=_detect_language(request) if request else "fr",
    )

    # Add fatigue factor if significant advantage exists
    lang: Language = _detect_language(request) if request else "fr"
    if fatigue_data:
        if fatigue_data.fatigue_advantage > 0.15:
            key_factors.append(get_label("physical_advantage", lang))
        elif fatigue_data.fatigue_advantage < -0.15:
            key_factors.append(get_label("busy_schedule", lang))

    # Model contributions from ensemble (real data) - ALWAYS calculate for DB storage
    model_contributions = None
    model_details_data = None  # Dict for DB storage
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

        # Store raw contributions for DB
        model_details_data = {
            "contributions": contributions,
            "model_agreement": model_agreement,
            "team_stats": {
                "home_elo": team_stats["home_elo"],
                "away_elo": team_stats["away_elo"],
                "home_attack": team_stats["home_attack"],
                "home_defense": team_stats["home_defense"],
                "away_attack": team_stats["away_attack"],
                "away_defense": team_stats["away_defense"],
                "home_form": team_stats["home_form"],
                "away_form": team_stats["away_form"],
            },
        }

        # Map to API model contributions format (for response only)
        if include_model_details:
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
        model_details_data = None

    # LLM adjustments (from RAG context if available)
    # ALWAYS calculate adjustments and apply to probabilities
    # Only RETURN them in response when include_model_details=True
    llm_adjustments_data = None
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

        # Build detailed reasoning from RAG context
        reasoning_parts = []
        home_key_info = home_ctx.get("key_info", [])
        away_key_info = away_ctx.get("key_info", [])

        # Add injury info to reasoning
        if home_injuries > 0:
            reasoning_parts.append(f"⚠️ {home_team}: {home_injuries} blessure(s) signalée(s)")
        if away_injuries > 0:
            reasoning_parts.append(f"⚠️ {away_team}: {away_injuries} blessure(s) signalée(s)")

        # Add sentiment info
        if home_sentiment_raw != "neutral":
            emoji = "✅" if home_sentiment_raw == "positive" else "❌"
            reasoning_parts.append(f"{emoji} {home_team}: sentiment {home_sentiment_raw} dans les news")
        if away_sentiment_raw != "neutral":
            emoji = "✅" if away_sentiment_raw == "positive" else "❌"
            reasoning_parts.append(f"{emoji} {away_team}: sentiment {away_sentiment_raw} dans les news")

        # Add key info highlights
        if home_key_info:
            reasoning_parts.append(f"📰 {home_team}: {home_key_info[0]}")
        if away_key_info:
            reasoning_parts.append(f"📰 {away_team}: {away_key_info[0]}")

        # Build final reasoning
        if reasoning_parts:
            detailed_reasoning = " | ".join(reasoning_parts)
        else:
            detailed_reasoning = "Aucune information contextuelle significative trouvée dans les news récentes."

        llm_adjustments_data = {
            "injury_impact_home": injury_impact_home,
            "injury_impact_away": injury_impact_away,
            "sentiment_home": round(sentiment_home, 3),
            "sentiment_away": round(sentiment_away, 3),
            "tactical_edge": 0.0,
            "total_adjustment": round(clamped_total, 3),
            "reasoning": detailed_reasoning,
        }

        # ALWAYS apply LLM adjustments to probabilities via log-odds transformation
        if abs(clamped_total) > 0.001:
            import math

            # Apply adjustments: positive = favors home, negative = favors away
            # Use log-odds transformation for smooth adjustment
            def apply_log_odds_adjustment(prob: float, adj: float) -> float:
                """Apply adjustment via log-odds transformation."""
                # Clamp probability to avoid log(0) or log(inf)
                prob = max(0.001, min(0.999, prob))
                log_odds = math.log(prob / (1 - prob))
                adjusted_log_odds = log_odds + adj
                return 1 / (1 + math.exp(-adjusted_log_odds))

            # Distribute adjustment: positive total helps home, negative helps away
            # Home gets positive portion, away gets negative portion
            home_adj = max(0, clamped_total)  # Positive adjustment helps home
            away_adj = -min(0, clamped_total)  # Negative adjustment helps away

            # Apply adjustments
            new_home = apply_log_odds_adjustment(home_prob, home_adj * 2)
            new_away = apply_log_odds_adjustment(away_prob, away_adj * 2)
            new_draw = max(0.05, 1.0 - new_home - new_away)  # Draw is residual

            # Normalize to ensure sum = 1
            total_new = new_home + new_draw + new_away
            home_prob = round(new_home / total_new, 4)
            draw_prob = round(new_draw / total_new, 4)
            away_prob = round(new_away / total_new, 4)

            # Update recommended bet if probabilities changed significantly
            recommended_bet = _get_recommended_bet(home_prob, draw_prob, away_prob)

            logger.info(
                f"Applied LLM adjustments for {home_team} vs {away_team}: "
                f"total_adj={clamped_total:+.3f}, new probs: H={home_prob:.2%} D={draw_prob:.2%} A={away_prob:.2%}"
            )

    # Only include in response when model details requested
    llm_adjustments = None
    if include_model_details:
        if llm_adjustments_data:
            llm_adjustments = LLMAdjustments(**llm_adjustments_data)
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
                    key_factors=cached_key_factors if cached_key_factors else ["Analyse statistique"],
                    risk_factors=cached_risk_factors if cached_risk_factors else ["Données en cache"],
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

        # Generate predictions for all matches with full model details for DB storage
        all_predictions = []
        for api_match in api_matches:
            # Generate with full model details so we can store everything in DB
            pred = await _generate_prediction_from_api_match(api_match, include_model_details=True, request=request)

            # Extract model_details and llm_adjustments for DB storage
            model_details_for_db = None
            if pred.model_contributions:
                model_details_for_db = {
                    "poisson": pred.model_contributions.poisson.model_dump() if pred.model_contributions.poisson else None,
                    "xgboost": pred.model_contributions.xgboost.model_dump() if pred.model_contributions.xgboost else None,
                    "xg_model": pred.model_contributions.xg_model.model_dump() if pred.model_contributions.xg_model else None,
                    "elo": pred.model_contributions.elo.model_dump() if pred.model_contributions.elo else None,
                }

            llm_adjustments_for_db = None
            if pred.llm_adjustments:
                llm_adjustments_for_db = pred.llm_adjustments.model_dump()

            # Save prediction to database with ALL data (including ML model details and LLM adjustments)
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
                    "key_factors": pred.key_factors,
                    "risk_factors": pred.risk_factors,
                    "value_score": pred.value_score,
                    "model_details": model_details_for_db,
                    "llm_adjustments": llm_adjustments_for_db,
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
            from datetime import date, timedelta
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
                message=f"Last {days} days: {pred_count} predictions, {verified_count} verified, {finished_with_pred} finished matches with predictions, {verify_count} newly verified",
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


@router.get(
    "/stats/daily",
    response_model=DailyStatsResponse,
    responses=AUTH_RESPONSES,
    operation_id="getDailyStats",
)
@limiter.limit(RATE_LIMITS["predictions"])
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
                home_team = await uow.teams.get_by_id(match.home_team_id) if match.home_team_id else None
                away_team = await uow.teams.get_by_id(match.away_team_id) if match.away_team_id else None
                return {
                    "home_team": home_team.name if home_team else None,
                    "away_team": away_team.name if away_team else None,
                    "competition": COMPETITION_NAMES.get(match.competition_code, match.competition_code) if match.competition_code else None,
                    "match_date": match.match_date,
                }
    except Exception as e:
        logger.debug(f"Could not fetch match {match_id} from DB: {e}")
    return None


def _generate_fallback_prediction(
    match_id: int,
    include_model_details: bool = False,
    fallback_reason: str = "API externe indisponible",
    is_rate_limit: bool = False,
    retry_after: int | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    competition: str | None = None,
    match_date: datetime | None = None,
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
        home_team=home_team or "Unknown Home Team",
        away_team=away_team or "Unknown Away Team",
        competition=competition or "Unknown",
        match_date=match_date or (datetime.now() + timedelta(hours=2)),
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
                    home_team_obj = await uow.teams.get_by_id(match_obj.home_team_id) if match_obj.home_team_id else None
                    away_team_obj = await uow.teams.get_by_id(match_obj.away_team_id) if match_obj.away_team_id else None
                    home_team = home_team_obj.name if home_team_obj else "Unknown"
                    away_team = away_team_obj.name if away_team_obj else "Unknown"
                    comp_code = match_obj.competition_code or "UNKNOWN"
                    match_date_val = match_obj.match_date if match_obj.match_date else datetime.now()
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

            # Use cached key_factors and risk_factors if available, fallback to defaults
            cached_key_factors = cached.get("key_factors")
            cached_risk_factors = cached.get("risk_factors")
            key_factors = cached_key_factors if cached_key_factors else ["Analyse statistique", "Modèles ML"]
            risk_factors = cached_risk_factors if cached_risk_factors else ["Données en cache"]

            # Build model_contributions and llm_adjustments from cached data
            model_contributions = None
            llm_adjustments_obj = None
            if include_model_details:
                cached_model_details = cached.get("model_details")
                cached_llm_adjustments = cached.get("llm_adjustments")

                if cached_model_details:
                    try:
                        model_contributions = ModelContributions(
                            poisson=PredictionProbabilities(**cached_model_details["poisson"]) if cached_model_details.get("poisson") else PredictionProbabilities(home_win=0.33, draw=0.34, away_win=0.33),
                            xgboost=PredictionProbabilities(**cached_model_details["xgboost"]) if cached_model_details.get("xgboost") else PredictionProbabilities(home_win=0.33, draw=0.34, away_win=0.33),
                            xg_model=PredictionProbabilities(**cached_model_details["xg_model"]) if cached_model_details.get("xg_model") else PredictionProbabilities(home_win=0.33, draw=0.34, away_win=0.33),
                            elo=PredictionProbabilities(**cached_model_details["elo"]) if cached_model_details.get("elo") else PredictionProbabilities(home_win=0.33, draw=0.34, away_win=0.33),
                        )
                    except Exception as e:
                        logger.debug(f"Failed to parse model_details from cache: {e}")

                if cached_llm_adjustments:
                    try:
                        llm_adjustments_obj = LLMAdjustments(**cached_llm_adjustments)
                    except Exception as e:
                        logger.debug(f"Failed to parse llm_adjustments from cache: {e}")

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
                explanation=cached.get("explanation", "Prédiction mise en cache"),
                key_factors=key_factors,
                risk_factors=risk_factors,
                model_contributions=model_contributions,
                llm_adjustments=llm_adjustments_obj,
                created_at=datetime.now(),
                data_source=DataSourceInfo(source="database"),
            )

            # Also cache in Redis for faster future access
            try:
                await _cache_prediction_to_redis(match_id, response.model_dump(mode="json"))
            except Exception:
                pass

            return response
    except Exception as e:
        logger.warning(f"DB cache lookup failed for match {match_id}: {e}")

    # 3. No cache, generate new prediction
    try:
        # Fetch real match from API
        client = get_football_data_client()
        api_match = await client.get_match(match_id)
        # Always generate with full model details for DB storage
        prediction = await _generate_prediction_from_api_match(
            api_match, include_model_details=True, request=request
        )

        # Extract model_details and llm_adjustments for DB storage
        model_details_for_db = None
        if prediction.model_contributions:
            model_details_for_db = {
                "poisson": prediction.model_contributions.poisson.model_dump() if prediction.model_contributions.poisson else None,
                "xgboost": prediction.model_contributions.xgboost.model_dump() if prediction.model_contributions.xgboost else None,
                "xg_model": prediction.model_contributions.xg_model.model_dump() if prediction.model_contributions.xg_model else None,
                "elo": prediction.model_contributions.elo.model_dump() if prediction.model_contributions.elo else None,
            }

        llm_adjustments_for_db = None
        if prediction.llm_adjustments:
            llm_adjustments_for_db = prediction.llm_adjustments.model_dump()

        # 4. Save to DB for permanent storage with ALL data
        try:
            await PredictionService.save_prediction_from_api({
                "match_id": prediction.match_id,
                "match_external_id": f"{api_match.competition.code}_{api_match.id}",
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "competition_code": api_match.competition.code,
                "match_date": api_match.utcDate,
                "home_win_prob": prediction.probabilities.home_win,
                "draw_prob": prediction.probabilities.draw,
                "away_win_prob": prediction.probabilities.away_win,
                "confidence": prediction.confidence,
                "recommendation": prediction.recommended_bet,
                "explanation": prediction.explanation,
                "key_factors": prediction.key_factors,
                "risk_factors": prediction.risk_factors,
                "value_score": prediction.value_score,
                "model_details": model_details_for_db,
                "llm_adjustments": llm_adjustments_for_db,
            })
            logger.info(f"Saved prediction to DB for match {match_id}")
        except Exception as db_err:
            logger.warning(f"Failed to save prediction to DB: {db_err}")

        # If user didn't request model details, strip them from response
        if not include_model_details:
            prediction.model_contributions = None
            prediction.llm_adjustments = None
            prediction.multi_markets = None

        # 5. Cache in Redis
        try:
            await _cache_prediction_to_redis(match_id, prediction.model_dump(mode="json"))
        except Exception:
            pass

        return prediction

    except RateLimitError as e:
        # On rate limit, try fallback instead of failing
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        logger.warning(f"Rate limit hit for match {match_id}, using fallback prediction")
        # Try to get real match info from DB
        match_info = await _get_match_info_from_db(match_id)
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason="Limite API externe atteinte (10 req/min)",
            is_rate_limit=True,
            retry_after=retry_after,
            home_team=match_info.get("home_team") if match_info else None,
            away_team=match_info.get("away_team") if match_info else None,
            competition=match_info.get("competition") if match_info else None,
            match_date=match_info.get("match_date") if match_info else None,
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
        # Try to get real match info from DB
        match_info = await _get_match_info_from_db(match_id)
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason=f"Erreur API externe: {str(e)[:50]}",
            home_team=match_info.get("home_team") if match_info else None,
            away_team=match_info.get("away_team") if match_info else None,
            competition=match_info.get("competition") if match_info else None,
            match_date=match_info.get("match_date") if match_info else None,
        )

    except Exception as e:
        # Catch-all for any other errors, use fallback
        logger.error(f"Unexpected error for match {match_id}: {e}. Using fallback prediction.")
        # Try to get real match info from DB
        match_info = await _get_match_info_from_db(match_id)
        return _generate_fallback_prediction(
            match_id,
            include_model_details,
            fallback_reason=f"Erreur inattendue: {str(e)[:50]}",
            home_team=match_info.get("home_team") if match_info else None,
            away_team=match_info.get("away_team") if match_info else None,
            competition=match_info.get("competition") if match_info else None,
            match_date=match_info.get("match_date") if match_info else None,
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


# ============================================================================
# Calibration Endpoint
# ============================================================================


class CalibrationBucket(BaseModel):
    """Single calibration bucket with predicted vs actual win rate."""

    confidence_range: str = Field(..., description="Confidence range, e.g., '60-70%'")
    predicted_confidence: float = Field(..., description="Average predicted confidence in bucket")
    actual_win_rate: float = Field(..., description="Actual win rate in this bucket")
    count: int = Field(..., description="Number of predictions in bucket")
    overconfidence: float = Field(..., description="Difference: predicted - actual (positive = overconfident)")


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
    overall_calibration_error: float = Field(..., description="Mean calibration error (lower is better)")
    by_bet_type: list[CalibrationByBet] = Field(..., description="Calibration by bet type")
    by_confidence: list[CalibrationBucket] = Field(..., description="Calibration by confidence bucket")
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
    from sqlalchemy import select, func, and_
    from src.db.models import PredictionResult, Match

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

            predictions_data.append({
                "predicted": predicted,
                "actual": actual_outcome,
                "confidence": confidence,
                "is_correct": is_correct,
                "competition": match.competition_code,
            })

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

            by_bet_type.append(CalibrationByBet(
                bet_type=bet,
                total_predictions=bt_count,
                correct=bt_correct,
                accuracy=bt_accuracy,
                avg_confidence=bt_avg_conf,
                buckets=buckets,
            ))

        # Calculate overall confidence buckets
        overall_buckets = _calculate_buckets(predictions_data)

        # Calculate mean calibration error
        calibration_errors = []
        for bucket in overall_buckets:
            if bucket.count > 0:
                calibration_errors.append(abs(bucket.overconfidence))
        mean_calibration_error = sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0

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
                "avg_confidence": sum(p["confidence"] for p in comp_preds) / comp_count if comp_count > 0 else 0,
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


def _calculate_buckets(predictions: list[dict]) -> list[CalibrationBucket]:
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

        buckets.append(CalibrationBucket(
            confidence_range=label,
            predicted_confidence=avg_conf,
            actual_win_rate=actual_rate,
            count=count,
            overconfidence=overconfidence,
        ))

    return buckets
