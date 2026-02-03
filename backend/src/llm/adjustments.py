"""LLM-derived adjustments for match predictions.

Processes LLM analysis to compute probability adjustments and confidence scores
based on injuries, form, sentiment, and other contextual factors.
"""

import logging
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.llm.client import get_llm_client
from src.llm.prompts import (
    INJURY_ANALYSIS_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT,
    SYSTEM_JSON_EXTRACTOR,
)
from src.llm.prompts_advanced import (
    get_form_analysis_prompt,
    get_injury_impact_analysis_prompt,
)
from src.prediction_engine.ensemble import LLMAdjustments

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Validation Models for LLM JSON Responses
# =============================================================================


class InjuryAnalysis(BaseModel):
    """Validated injury analysis from LLM."""

    player_name: str | None = Field(default=None, description="Name of injured player")
    position: str | None = Field(default=None, description="Player position")
    impact_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Impact on team performance (0.0-1.0)",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in analysis (0.0-1.0)"
    )
    is_key_player: bool = Field(default=False, description="Whether player is key")
    expected_return: str | None = Field(
        default=None, description="Expected return timeframe"
    )
    reasoning: str = Field(default="", description="Analysis reasoning")

    @field_validator("impact_score", "confidence", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> float:
        """Coerce string values to float."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return 0.0
        if v is None:
            return 0.0
        return float(v)

    @field_validator("is_key_player", mode="before")
    @classmethod
    def coerce_bool(cls, v: Any) -> bool:
        """Coerce various values to bool."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "yes", "1", "oui")
        return bool(v)


class SentimentAnalysis(BaseModel):
    """Validated sentiment analysis from LLM."""

    sentiment_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Sentiment score (-1.0 to 1.0)",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in analysis (0.0-1.0)"
    )
    morale_indicator: Literal[
        "very_negative", "negative", "neutral", "positive", "very_positive"
    ] = Field(default="neutral", description="Team morale level")
    key_factors: list[str] = Field(
        default_factory=list, description="Key factors affecting sentiment"
    )
    reasoning: str = Field(default="", description="Analysis reasoning")

    @field_validator("sentiment_score", "confidence", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> float:
        """Coerce string values to float."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return 0.0
        if v is None:
            return 0.0
        return float(v)

    @field_validator("morale_indicator", mode="before")
    @classmethod
    def normalize_morale(cls, v: Any) -> str:
        """Normalize morale indicator values."""
        if v is None:
            return "neutral"
        v_str = str(v).lower().strip()
        valid_values = {
            "very_negative",
            "negative",
            "neutral",
            "positive",
            "very_positive",
        }
        if v_str in valid_values:
            return v_str
        # Map common variations
        if "very" in v_str and "neg" in v_str:
            return "very_negative"
        if "very" in v_str and "pos" in v_str:
            return "very_positive"
        if "neg" in v_str or "bad" in v_str:
            return "negative"
        if "pos" in v_str or "good" in v_str:
            return "positive"
        return "neutral"


class FormAssessment(BaseModel):
    """Nested form assessment details."""

    recent_performance: Literal[
        "very_poor",
        "poor",
        "below_average",
        "average",
        "above_average",
        "good",
        "excellent",
    ] = Field(default="average")
    trend: Literal["declining", "stable", "improving"] = Field(default="stable")
    trend_strength: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("recent_performance", mode="before")
    @classmethod
    def normalize_performance(cls, v: Any) -> str:
        """Normalize performance values."""
        if v is None:
            return "average"
        v_str = str(v).lower().strip().replace(" ", "_")
        valid = {
            "very_poor",
            "poor",
            "below_average",
            "average",
            "above_average",
            "good",
            "excellent",
        }
        if v_str in valid:
            return v_str
        # Map common variations
        if "excel" in v_str or "great" in v_str:
            return "excellent"
        if "very" in v_str and "poor" in v_str:
            return "very_poor"
        if "poor" in v_str or "bad" in v_str:
            return "poor"
        if "good" in v_str:
            return "good"
        return "average"

    @field_validator("trend", mode="before")
    @classmethod
    def normalize_trend(cls, v: Any) -> str:
        """Normalize trend values."""
        if v is None:
            return "stable"
        v_str = str(v).lower().strip()
        if "improv" in v_str or "up" in v_str or "rising" in v_str:
            return "improving"
        if "declin" in v_str or "down" in v_str or "fall" in v_str:
            return "declining"
        return "stable"


class FormAnalysis(BaseModel):
    """Validated form analysis from LLM."""

    sentiment_adjustment: float = Field(
        default=0.0,
        ge=-0.15,
        le=0.15,
        description="Form-based adjustment (-0.15 to 0.15)",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in analysis (0.0-1.0)"
    )
    form_assessment: FormAssessment = Field(default_factory=FormAssessment)
    reasoning: str = Field(default="", description="Analysis reasoning")

    @field_validator("sentiment_adjustment", "confidence", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> float:
        """Coerce string values to float."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return 0.0
        if v is None:
            return 0.0
        return float(v)

    @field_validator("form_assessment", mode="before")
    @classmethod
    def ensure_form_assessment(cls, v: Any) -> dict:
        """Ensure form_assessment is a dict."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


def validate_injury_analysis(raw_result: dict) -> InjuryAnalysis:
    """Validate and parse raw LLM injury analysis result."""
    try:
        return InjuryAnalysis.model_validate(raw_result)
    except Exception as e:
        logger.warning(f"Injury analysis validation failed: {e}")
        return InjuryAnalysis(reasoning="Validation failed")


def validate_sentiment_analysis(raw_result: dict) -> SentimentAnalysis:
    """Validate and parse raw LLM sentiment analysis result."""
    try:
        return SentimentAnalysis.model_validate(raw_result)
    except Exception as e:
        logger.warning(f"Sentiment analysis validation failed: {e}")
        return SentimentAnalysis(reasoning="Validation failed")


def validate_form_analysis(raw_result: dict) -> FormAnalysis:
    """Validate and parse raw LLM form analysis result."""
    try:
        return FormAnalysis.model_validate(raw_result)
    except Exception as e:
        logger.warning(f"Form analysis validation failed: {e}")
        return FormAnalysis(reasoning="Validation failed")


async def analyze_injury_impact(
    team_name: str,
    news_text: str,
    team_strength: str = "medium",
) -> dict[str, Any]:
    """
    Analyze injury news and extract detailed impact assessment.

    Provides structured injury information including severity, expected return,
    and impact score for prediction adjustments.

    Args:
        team_name: Team name
        news_text: Injury news text
        team_strength: Team strength (weak/medium/strong)

    Returns:
        Dict with injury analysis including impact_score and confidence
    """
    client = get_llm_client()

    prompt = INJURY_ANALYSIS_PROMPT.format(
        team_name=team_name,
        news_text=news_text,
    )

    try:
        result = await client.analyze_json(
            prompt=prompt,
            system_prompt=SYSTEM_JSON_EXTRACTOR,
            model=client.MODEL_SMALL,
            temperature=0.2,  # Low temperature for consistent extraction
        )

        # Validate with Pydantic model
        validated = validate_injury_analysis(result)
        logger.debug(
            f"Injury analysis for {team_name}: impact={validated.impact_score:.2f}, "
            f"confidence={validated.confidence:.2f}"
        )
        return validated.model_dump()

    except Exception as e:
        logger.error(f"Error analyzing injury for {team_name}: {str(e)}")
        return InjuryAnalysis(reasoning="Analysis failed").model_dump()


async def analyze_sentiment(
    team_name: str,
    content: str,
    source_type: str = "news",
) -> dict[str, Any]:
    """
    Analyze sentiment from news, media, or social content.

    Evaluates team morale, confidence, and forward outlook based on
    media sentiment and public perception.

    Args:
        team_name: Team name
        content: Content to analyze (news, interview, social media, etc.)
        source_type: Source type (news/press_conference/social/interview)

    Returns:
        Dict with sentiment analysis including score and confidence
    """
    client = get_llm_client()

    prompt = SENTIMENT_ANALYSIS_PROMPT.format(
        team_name=team_name,
        content=content,
        source_type=source_type,
    )

    try:
        result = await client.analyze_json(
            prompt=prompt,
            system_prompt=SYSTEM_JSON_EXTRACTOR,
            model=client.MODEL_SMALL,
            temperature=0.2,
        )

        # Validate with Pydantic model
        validated = validate_sentiment_analysis(result)
        logger.debug(
            f"Sentiment analysis for {team_name}: score={validated.sentiment_score:.2f}, "
            f"morale={validated.morale_indicator}, confidence={validated.confidence:.2f}"
        )
        return validated.model_dump()

    except Exception as e:
        logger.error(f"Error analyzing sentiment for {team_name}: {str(e)}")
        return SentimentAnalysis(reasoning="Analysis failed").model_dump()


async def analyze_form(
    team_name: str,
    recent_results: list[str],
    media_sentiment: str = "neutral",
    tactical_changes: str = "",
) -> dict[str, Any]:
    """
    Analyze team form and momentum with chain-of-thought reasoning.

    Evaluates recent performance, confidence levels, and psychological state.

    Args:
        team_name: Team name
        recent_results: List of recent results (e.g., ['W', 'D', 'L', 'W'])
        media_sentiment: Media sentiment (very_negative/negative/neutral/positive/very_positive)
        tactical_changes: Recent tactical modifications

    Returns:
        Dict with form analysis including momentum and sentiment adjustments
    """
    client = get_llm_client()

    prompt = get_form_analysis_prompt(
        team_name=team_name,
        recent_results=recent_results,
        media_sentiment=media_sentiment,
        tactical_changes=tactical_changes,
    )

    try:
        result = await client.analyze_json(
            prompt=prompt,
            system_prompt="You are an expert at analyzing team form and providing JSON assessments.",
            model=client.MODEL_SMALL,
            temperature=0.3,
        )

        # Validate with Pydantic model
        validated = validate_form_analysis(result)
        logger.debug(
            f"Form analysis for {team_name}: adjustment={validated.sentiment_adjustment:.3f}, "
            f"performance={validated.form_assessment.recent_performance}, "
            f"trend={validated.form_assessment.trend}"
        )
        return validated.model_dump()

    except Exception as e:
        logger.error(f"Error analyzing form for {team_name}: {str(e)}")
        return FormAnalysis(reasoning="Analysis failed").model_dump()


async def calculate_llm_adjustments(
    home_team: str,
    away_team: str,
    home_injuries: list[dict[str, Any]] | None = None,
    away_injuries: list[dict[str, Any]] | None = None,
    home_sentiment: dict[str, Any] | None = None,
    away_sentiment: dict[str, Any] | None = None,
    home_form: dict[str, Any] | None = None,
    away_form: dict[str, Any] | None = None,
) -> LLMAdjustments:
    """
    Calculate comprehensive LLM-based adjustments for match prediction.

    Synthesizes injury impact, sentiment analysis, and form evaluation into
    probability adjustments with detailed reasoning.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_injuries: List of injury analyses for home team
        away_injuries: List of injury analyses for away team
        home_sentiment: Sentiment analysis for home team
        away_sentiment: Sentiment analysis for away team
        home_form: Form analysis for home team
        away_form: Form analysis for away team

    Returns:
        LLMAdjustments object with all adjustments and confidence scores
    """
    adjustments = LLMAdjustments()
    reasoning_parts = []

    # Calculate injury impact
    if home_injuries:
        injury_impact = _calculate_injury_impact(home_injuries, home_team)
        adjustments.injury_impact_home = injury_impact["factor"]
        if abs(injury_impact["factor"]) > 0.05:
            reasoning_parts.append(injury_impact["reasoning"])
        logger.info(f"{home_team} injury impact: {injury_impact['factor']:.3f}")

    if away_injuries:
        injury_impact = _calculate_injury_impact(away_injuries, away_team)
        adjustments.injury_impact_away = injury_impact["factor"]
        if abs(injury_impact["factor"]) > 0.05:
            reasoning_parts.append(injury_impact["reasoning"])
        logger.info(f"{away_team} injury impact: {injury_impact['factor']:.3f}")

    # Apply sentiment adjustments
    if home_sentiment:
        sentiment_adjustment = _calculate_sentiment_adjustment(home_sentiment, home_team)
        adjustments.sentiment_home = sentiment_adjustment["factor"]
        if abs(sentiment_adjustment["factor"]) > 0.03:
            reasoning_parts.append(sentiment_adjustment["reasoning"])
        logger.info(f"{home_team} sentiment adjustment: {sentiment_adjustment['factor']:.3f}")

    if away_sentiment:
        sentiment_adjustment = _calculate_sentiment_adjustment(away_sentiment, away_team)
        adjustments.sentiment_away = sentiment_adjustment["factor"]
        if abs(sentiment_adjustment["factor"]) > 0.03:
            reasoning_parts.append(sentiment_adjustment["reasoning"])
        logger.info(f"{away_team} sentiment adjustment: {sentiment_adjustment['factor']:.3f}")

    # Apply form adjustments
    if home_form:
        form_adjustment = _calculate_form_adjustment(home_form, home_team)
        adjustments.form_home = form_adjustment["factor"]
        if abs(form_adjustment["factor"]) > 0.03:
            reasoning_parts.append(form_adjustment["reasoning"])
        logger.info(f"{home_team} form adjustment: {form_adjustment['factor']:.3f}")

    if away_form:
        form_adjustment = _calculate_form_adjustment(away_form, away_team)
        adjustments.form_away = form_adjustment["factor"]
        if abs(form_adjustment["factor"]) > 0.03:
            reasoning_parts.append(form_adjustment["reasoning"])
        logger.info(f"{away_team} form adjustment: {form_adjustment['factor']:.3f}")

    # Set comprehensive reasoning
    if reasoning_parts:
        adjustments.reasoning = "; ".join(reasoning_parts)
    else:
        adjustments.reasoning = "No significant adjustments identified"

    # Calculate overall confidence
    confidences = []
    if home_injuries:
        confidences.extend([inj.get("confidence", 0.5) for inj in home_injuries])
    if away_injuries:
        confidences.extend([inj.get("confidence", 0.5) for inj in away_injuries])
    if home_sentiment:
        confidences.append(home_sentiment.get("confidence", 0.5))
    if away_sentiment:
        confidences.append(away_sentiment.get("confidence", 0.5))
    if home_form:
        confidences.append(home_form.get("confidence", 0.5))
    if away_form:
        confidences.append(away_form.get("confidence", 0.5))

    if confidences:
        adjustments.overall_confidence = sum(confidences) / len(confidences)
    else:
        adjustments.overall_confidence = 0.5

    logger.info(
        f"Final adjustments - Home: {adjustments.injury_impact_home:.3f}, "
        f"Away: {adjustments.injury_impact_away:.3f}, "
        f"Confidence: {adjustments.overall_confidence:.3f}"
    )

    return adjustments


def _calculate_injury_impact(injuries: list[dict[str, Any]], team_name: str) -> dict[str, Any]:
    """
    Calculate cumulative injury impact factor.

    Uses impact scores and confidence levels to determine overall
    competitive disadvantage.

    Args:
        injuries: List of injury analysis dictionaries
        team_name: Team name for logging

    Returns:
        Dict with "factor" (-0.3 to 0.0) and "reasoning"
    """
    if not injuries:
        return {"factor": 0.0, "reasoning": ""}

    # Weight injuries by impact score and confidence
    total_weighted_impact = sum(
        inj.get("impact_score", 0) * inj.get("confidence", 0.5) for inj in injuries
    )

    # Scale to -0.3 to 0.0 range (more conservative than simple multiplication)
    impact_factor = max(-0.3, -total_weighted_impact * 0.2)

    # Build reasoning with key injuries
    key_injuries = []
    for inj in injuries[:3]:  # Top 3 injuries
        player = inj.get("player_name", "unknown")
        impact = inj.get("impact_score", 0)
        if impact > 0.3:
            key_injuries.append(player)

    if key_injuries:
        reasoning = f"{team_name} weakened by absences ({', '.join(key_injuries)})"
    else:
        reasoning = ""

    return {"factor": impact_factor, "reasoning": reasoning}


def _calculate_sentiment_adjustment(sentiment: dict[str, Any], team_name: str) -> dict[str, Any]:
    """
    Calculate sentiment-based probability adjustment.

    Converts sentiment score to probability adjustment with confidence weighting.

    Args:
        sentiment: Sentiment analysis dictionary
        team_name: Team name for logging

    Returns:
        Dict with "factor" (-0.1 to 0.1) and "reasoning"
    """
    score = sentiment.get("sentiment_score", 0)
    confidence = sentiment.get("confidence", 0.5)

    # Apply confidence weight (only use adjustment if confident)
    adjustment_factor = score * confidence * 0.1  # Max ±0.1

    mood_indicator = sentiment.get("morale_indicator", "neutral")
    mood_descriptors = {
        "very_positive": "excellent",
        "positive": "strong",
        "neutral": "neutral",
        "negative": "weak",
        "very_negative": "crisis",
    }
    mood = mood_descriptors.get(mood_indicator, "neutral")

    if abs(adjustment_factor) > 0.02:
        reasoning = f"{team_name} in {mood} morale (sentiment: {score:.2f})"
    else:
        reasoning = ""

    return {"factor": adjustment_factor, "reasoning": reasoning}


def _calculate_form_adjustment(form: dict[str, Any], team_name: str) -> dict[str, Any]:
    """
    Calculate form-based probability adjustment.

    Evaluates recent performance and momentum to adjust probabilities.

    Args:
        form: Form analysis dictionary
        team_name: Team name for logging

    Returns:
        Dict with "factor" (-0.1 to 0.1) and "reasoning"
    """
    sentiment_adjustment = form.get("sentiment_adjustment", 0)
    confidence = form.get("confidence", 0.5)

    # Apply confidence weighting
    adjustment_factor = sentiment_adjustment * confidence  # Range: ±0.15

    performance = form.get("form_assessment", {}).get("recent_performance", "average")
    trend = form.get("form_assessment", {}).get("trend", "stable")

    performance_map = {
        "very_poor": "terrible",
        "poor": "poor",
        "below_average": "below average",
        "average": "average",
        "above_average": "above average",
        "good": "good",
        "excellent": "excellent",
    }
    perf_desc = performance_map.get(performance, "average")

    if abs(adjustment_factor) > 0.02:
        reasoning = f"{team_name} in {perf_desc} form ({trend})"
    else:
        reasoning = ""

    return {"factor": adjustment_factor, "reasoning": reasoning}
