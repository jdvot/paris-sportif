"""LLM-derived adjustments for predictions."""

from typing import Optional

from src.llm.client import get_llm_client
from src.llm.prompts import (
    SYSTEM_JSON_EXTRACTOR,
    INJURY_ANALYSIS_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT,
)
from src.prediction_engine.ensemble import LLMAdjustments


async def analyze_injury_impact(
    team_name: str,
    news_text: str,
) -> dict:
    """
    Analyze injury news and extract impact.

    Args:
        team_name: Team name
        news_text: Injury news text

    Returns:
        Dict with injury analysis
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
            model=client.MODEL_SMALL,  # Use smaller model for extraction
        )
        return result
    except Exception:
        return {
            "player_name": "unknown",
            "impact_score": 0.0,
            "confidence": 0.0,
        }


async def analyze_sentiment(
    team_name: str,
    content: str,
    source_type: str = "news",
) -> dict:
    """
    Analyze sentiment from news/media.

    Args:
        team_name: Team name
        content: Content to analyze
        source_type: Source type (news, press_conference, social)

    Returns:
        Dict with sentiment analysis
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
        )
        return result
    except Exception:
        return {
            "sentiment_score": 0.0,
            "confidence": 0.0,
        }


async def calculate_llm_adjustments(
    home_team: str,
    away_team: str,
    home_injuries: list[dict] | None = None,
    away_injuries: list[dict] | None = None,
    home_sentiment: dict | None = None,
    away_sentiment: dict | None = None,
) -> LLMAdjustments:
    """
    Calculate LLM adjustments for prediction.

    Combines injury impact and sentiment analysis.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_injuries: List of injury analyses for home team
        away_injuries: List of injury analyses for away team
        home_sentiment: Sentiment analysis for home team
        away_sentiment: Sentiment analysis for away team

    Returns:
        LLMAdjustments to apply to prediction
    """
    adjustments = LLMAdjustments()
    reasoning_parts = []

    # Calculate injury impact
    if home_injuries:
        total_impact = sum(
            inj.get("impact_score", 0) * inj.get("confidence", 0.5)
            for inj in home_injuries
        )
        # Scale to -0.3 to 0.0 range
        adjustments.injury_impact_home = max(-0.3, -total_impact * 0.3)
        if adjustments.injury_impact_home < -0.05:
            key_injuries = [inj.get("player_name", "?") for inj in home_injuries[:2]]
            reasoning_parts.append(
                f"{home_team} affaibli par blessures ({', '.join(key_injuries)})"
            )

    if away_injuries:
        total_impact = sum(
            inj.get("impact_score", 0) * inj.get("confidence", 0.5)
            for inj in away_injuries
        )
        adjustments.injury_impact_away = max(-0.3, -total_impact * 0.3)
        if adjustments.injury_impact_away < -0.05:
            key_injuries = [inj.get("player_name", "?") for inj in away_injuries[:2]]
            reasoning_parts.append(
                f"{away_team} affaibli par blessures ({', '.join(key_injuries)})"
            )

    # Apply sentiment adjustments
    if home_sentiment:
        score = home_sentiment.get("sentiment_score", 0)
        confidence = home_sentiment.get("confidence", 0.5)
        adjustments.sentiment_home = score * confidence * 0.1  # Max ±0.1
        if abs(adjustments.sentiment_home) > 0.03:
            mood = "positif" if adjustments.sentiment_home > 0 else "negatif"
            reasoning_parts.append(f"Moral {mood} pour {home_team}")

    if away_sentiment:
        score = away_sentiment.get("sentiment_score", 0)
        confidence = away_sentiment.get("confidence", 0.5)
        adjustments.sentiment_away = score * confidence * 0.1
        if abs(adjustments.sentiment_away) > 0.03:
            mood = "positif" if adjustments.sentiment_away > 0 else "negatif"
            reasoning_parts.append(f"Moral {mood} pour {away_team}")

    # Set reasoning
    adjustments.reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Pas d'ajustement significatif"

    return adjustments
