"""RAG (Retrieval Augmented Generation) endpoints for match context enrichment."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from src.prediction_engine.rag_enrichment import get_rag_enrichment

logger = logging.getLogger(__name__)

router = APIRouter()


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

    # Combined analysis
    combined_analysis: Optional[str] = None

    # Metadata
    enriched_at: datetime
    sources_used: list[str] = []


class RAGStatusResponse(BaseModel):
    """RAG system status."""
    enabled: bool
    groq_configured: bool
    last_enrichment: Optional[datetime] = None
    total_enrichments: int = 0


@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status() -> RAGStatusResponse:
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


@router.get("/enrich", response_model=MatchContext)
async def enrich_match(
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code (PL, SA, etc.)"),
    match_date: Optional[str] = Query(None, description="Match date in YYYY-MM-DD format"),
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

        # Build response
        return MatchContext(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=parsed_date,
            home_context=TeamContext(
                team_name=home_team,
                recent_news=enrichment.get("home_news", []),
                injuries=enrichment.get("home_injuries", []),
                sentiment_score=enrichment.get("home_sentiment", 0.0),
                sentiment_label=_get_sentiment_label(enrichment.get("home_sentiment", 0.0)),
            ),
            away_context=TeamContext(
                team_name=away_team,
                recent_news=enrichment.get("away_news", []),
                injuries=enrichment.get("away_injuries", []),
                sentiment_score=enrichment.get("away_sentiment", 0.0),
                sentiment_label=_get_sentiment_label(enrichment.get("away_sentiment", 0.0)),
            ),
            is_derby=enrichment.get("is_derby", False),
            match_importance=enrichment.get("importance", "normal"),
            combined_analysis=enrichment.get("analysis"),
            enriched_at=datetime.now(),
            sources_used=["groq_llm", "public_data"],
        )

    except Exception as e:
        logger.error(f"RAG enrichment error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich match: {str(e)}",
        )


def _get_sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score >= 0.3:
        return "positive"
    elif score <= -0.3:
        return "negative"
    return "neutral"


@router.post("/analyze")
async def analyze_match_context(
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code"),
    additional_context: Optional[str] = Query(None, description="Additional context to include"),
) -> dict:
    """
    Generate a detailed analysis of match context using LLM.

    This is a more intensive analysis than the basic enrichment.
    """
    try:
        rag = get_rag_enrichment()

        # Generate analysis
        analysis = await rag.generate_enriched_analysis(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            additional_context=additional_context or "",
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
