"""RAG (Retrieval Augmented Generation) endpoints for match context enrichment.

Premium endpoints - require premium or admin role.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.auth import PREMIUM_RESPONSES, PremiumUser
from src.data.data_enrichment import get_data_enrichment
from src.prediction_engine.rag_enrichment import get_rag_enrichment

logger = logging.getLogger(__name__)

router = APIRouter()


class WeatherInfo(BaseModel):
    """Weather information for match day."""

    available: bool = False
    temperature: float | None = None
    feels_like: float | None = None
    humidity: int | None = None
    description: str | None = None
    wind_speed: float | None = None
    rain_probability: float | None = None
    impact: str | None = None


class TeamContext(BaseModel):
    """Team context information."""

    team_name: str
    recent_news: list[str] = []
    injuries: list[str] = []
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0)
    sentiment_label: str = "neutral"


class MatchContext(BaseModel):
    """Full match context from RAG enrichment."""

    home_team: str
    away_team: str
    competition: str
    match_date: datetime

    # Team contexts
    home_context: TeamContext
    away_context: TeamContext

    # Match factors
    is_derby: bool = False
    match_importance: str = "normal"  # low, normal, high, critical

    # Weather
    weather: WeatherInfo | None = None

    # Combined analysis
    combined_analysis: str | None = None

    # Metadata
    enriched_at: datetime
    sources_used: list[str] = []


class RAGStatusResponse(BaseModel):
    """RAG system status."""

    enabled: bool
    groq_configured: bool
    last_enrichment: datetime | None = None
    total_enrichments: int = 0


@router.get("/status", response_model=RAGStatusResponse, responses=PREMIUM_RESPONSES)
async def get_rag_status(user: PremiumUser) -> RAGStatusResponse:
    """Get RAG system status."""
    try:
        rag = get_rag_enrichment()
        return RAGStatusResponse(
            enabled=True,
            groq_configured=rag.groq_client is not None,
            last_enrichment=None,  # TODO: track this
            total_enrichments=0,
        )
    except Exception as e:
        logger.error(f"RAG status error: {e}")
        return RAGStatusResponse(
            enabled=False,
            groq_configured=False,
        )


@router.get("/enrich", response_model=MatchContext, responses=PREMIUM_RESPONSES)
async def enrich_match(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code (PL, SA, etc.)"),
    match_date: str | None = Query(None, description="Match date in YYYY-MM-DD format"),
) -> MatchContext:
    """
    Enrich a match with contextual information using RAG.

    This endpoint fetches news, injuries, sentiment analysis,
    and other contextual data for a match.
    """
    try:
        rag = get_rag_enrichment()

        # Parse match date
        if match_date:
            parsed_date = datetime.strptime(match_date, "%Y-%m-%d")
        else:
            parsed_date = datetime.now()

        # Get enrichment
        enrichment = await rag.enrich_match_prediction(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=parsed_date,
        )

        # Extract nested contexts
        home_ctx = enrichment.get("home_context", {})
        away_ctx = enrichment.get("away_context", {})
        match_ctx = enrichment.get("match_context", {})

        # Convert sentiment to float score (handle both string and float inputs)
        sentiment_map = {"positive": 0.8, "negative": 0.2, "neutral": 0.5}

        def parse_sentiment(value: Any) -> tuple[float, str]:
            """Parse sentiment value, handling both string and numeric types."""
            if isinstance(value, (int, float)):
                # Already numeric, clamp to valid range
                score = max(-1.0, min(1.0, float(value)))
                label = "positive" if score > 0.3 else ("negative" if score < -0.3 else "neutral")
                return score, label
            elif isinstance(value, str):
                label = value.lower()
                score = sentiment_map.get(label, 0.5)
                return score, label
            return 0.5, "neutral"

        home_sentiment_raw = home_ctx.get("sentiment", "neutral")
        home_sentiment_score, home_sentiment_str = parse_sentiment(home_sentiment_raw)
        away_sentiment_raw = away_ctx.get("sentiment", "neutral")
        away_sentiment_score, away_sentiment_str = parse_sentiment(away_sentiment_raw)

        # Extract news titles and injury descriptions from dict lists
        def extract_titles(items: list[Any], key: str = "title") -> list[str]:
            """Extract string values from a list of dicts or strings."""
            result = []
            for item in items:
                if isinstance(item, dict):
                    val = item.get(key) or item.get("type") or str(item)
                    if val:
                        result.append(str(val)[:200])  # Truncate to avoid huge strings
                elif isinstance(item, str):
                    result.append(item[:200])
            return result

        home_news = extract_titles(home_ctx.get("news", []), "title")
        away_news = extract_titles(away_ctx.get("news", []), "title")
        home_injuries = extract_titles(home_ctx.get("injuries", []), "type")
        away_injuries = extract_titles(away_ctx.get("injuries", []), "type")

        # Fetch weather data
        weather_info = None
        try:
            data_enrichment = get_data_enrichment()
            weather_data = await data_enrichment.weather_client.get_match_weather(
                home_team, parsed_date
            )
            if weather_data.get("available"):
                weather_info = WeatherInfo(
                    available=True,
                    temperature=weather_data.get("temperature"),
                    feels_like=weather_data.get("feels_like"),
                    humidity=weather_data.get("humidity"),
                    description=weather_data.get("description"),
                    wind_speed=weather_data.get("wind_speed"),
                    rain_probability=weather_data.get("rain_probability"),
                    impact=weather_data.get("impact"),
                )
        except Exception as e:
            logger.warning(f"Weather fetch failed: {e}")

        # Build response
        return MatchContext(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=parsed_date,
            home_context=TeamContext(
                team_name=home_team,
                recent_news=home_news,
                injuries=home_injuries,
                sentiment_score=home_sentiment_score,
                sentiment_label=home_sentiment_str,
            ),
            away_context=TeamContext(
                team_name=away_team,
                recent_news=away_news,
                injuries=away_injuries,
                sentiment_score=away_sentiment_score,
                sentiment_label=away_sentiment_str,
            ),
            is_derby=match_ctx.get("is_derby", False),
            match_importance=match_ctx.get("importance", "normal"),
            weather=weather_info,
            combined_analysis=None,  # Not generated in base enrichment
            enriched_at=datetime.now(),
            sources_used=["groq_llm", "public_data", "open_meteo"],
        )

    except Exception as e:
        logger.error(f"RAG enrichment error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich match: {str(e)}",
        )


def _get_sentiment_label(score: float) -> str:
    """
    Convert sentiment score to label.

    Note: This function is kept for backward compatibility but is no longer
    used in the main enrich endpoint, which now receives sentiment as a string
    from the RAG enrichment service.
    """
    if score >= 0.6:
        return "positive"
    elif score <= 0.4:
        return "negative"
    return "neutral"


@router.post("/analyze")
async def analyze_match_context(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code"),
    additional_context: str | None = Query(None, description="Additional context to include"),
) -> dict[str, Any]:
    """
    Generate a detailed analysis of match context using LLM.

    This is a more intensive analysis than the basic enrichment.
    """
    try:
        rag = get_rag_enrichment()

        # First, get the enrichment data
        enrichment = await rag.enrich_match_prediction(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=datetime.now(),
        )

        # Create a base prediction structure
        base_prediction = {
            "home_win": 0.40,
            "draw": 0.30,
            "away_win": 0.30,
            "explanation": additional_context or "",
        }

        # Generate analysis with correct signature
        analysis = await rag.generate_enriched_analysis(
            home_team=home_team,
            away_team=away_team,
            base_prediction=base_prediction,
            enrichment=enrichment,
        )

        return {
            "home_team": home_team,
            "away_team": away_team,
            "competition": competition,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"RAG analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analysis: {str(e)}",
        )
