"""LLM-derived adjustments for match predictions.

Processes LLM analysis to compute probability adjustments and confidence scores
based on injuries, form, sentiment, and other contextual factors.
"""

import logging
from typing import Optional

from src.llm.client import get_llm_client
from src.llm.prompts import (
    SYSTEM_JSON_EXTRACTOR,
    INJURY_ANALYSIS_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT,
)
from src.llm.prompts_advanced import (
    get_injury_impact_analysis_prompt,
    get_form_analysis_prompt,
)
from src.prediction_engine.ensemble import LLMAdjustments

logger = logging.getLogger(__name__)


async def analyze_injury_impact(
    team_name: str,
    news_text: str,
    team_strength: str = "medium",
) -> dict:
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

        # Validate required fields
        if "impact_score" not in result or "confidence" not in result:
            logger.warning(f"Missing key fields in injury analysis for {team_name}")
            return {
                "player_name": result.get("player_name", "unknown"),
                "impact_score": 0.0,
                "confidence": 0.0,
                "reasoning": "Incomplete analysis",
            }

        return result

    except Exception as e:
        logger.error(f"Error analyzing injury for {team_name}: {str(e)}")
        return {
            "player_name": "unknown",
            "impact_score": 0.0,
            "confidence": 0.0,
            "reasoning": "Analysis failed",
        }


async def analyze_sentiment(
    team_name: str,
    content: str,
    source_type: str = "news",
) -> dict:
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

        # Validate sentiment score range
        if "sentiment_score" in result:
            score = result["sentiment_score"]
            if not isinstance(score, (int, float)):
                result["sentiment_score"] = 0.0
            else:
                result["sentiment_score"] = max(-1.0, min(1.0, float(score)))

        if "confidence" not in result:
            result["confidence"] = 0.0

        return result

    except Exception as e:
        logger.error(f"Error analyzing sentiment for {team_name}: {str(e)}")
        return {
            "sentiment_score": 0.0,
            "confidence": 0.0,
            "reasoning": "Analysis failed",
        }


async def analyze_form(
    team_name: str,
    recent_results: list[str],
    media_sentiment: str = "neutral",
    tactical_changes: str = "",
) -> dict:
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

        # Validate sentiment adjustment range
        if "sentiment_adjustment" in result:
            adjustment = result["sentiment_adjustment"]
            if isinstance(adjustment, (int, float)):
                result["sentiment_adjustment"] = max(-0.15, min(0.15, float(adjustment)))

        if "confidence" not in result:
            result["confidence"] = 0.5

        return result

    except Exception as e:
        logger.error(f"Error analyzing form for {team_name}: {str(e)}")
        return {
            "sentiment_adjustment": 0.0,
            "confidence": 0.0,
            "reasoning": "Analysis failed",
        }


async def calculate_llm_adjustments(
    home_team: str,
    away_team: str,
    home_injuries: Optional[list[dict]] = None,
    away_injuries: Optional[list[dict]] = None,
    home_sentiment: Optional[dict] = None,
    away_sentiment: Optional[dict] = None,
    home_form: Optional[dict] = None,
    away_form: Optional[dict] = None,
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

    logger.info(f"Final adjustments - Home: {adjustments.injury_impact_home:.3f}, "
                f"Away: {adjustments.injury_impact_away:.3f}, "
                f"Confidence: {adjustments.overall_confidence:.3f}")

    return adjustments


def _calculate_injury_impact(injuries: list[dict], team_name: str) -> dict:
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
        inj.get("impact_score", 0) * inj.get("confidence", 0.5)
        for inj in injuries
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


def _calculate_sentiment_adjustment(sentiment: dict, team_name: str) -> dict:
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


def _calculate_form_adjustment(form: dict, team_name: str) -> dict:
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
