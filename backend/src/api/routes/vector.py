"""Vector store management endpoints.

Admin endpoints for managing Qdrant vector store and news indexing.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.auth import ADMIN_RESPONSES, PREMIUM_RESPONSES, AdminUser, PremiumUser

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class VectorStoreStats(BaseModel):
    """Vector store statistics."""

    collection: str
    total_vectors: int
    embedding_dimension: int = 384
    status: str = "ready"


class IngestionResult(BaseModel):
    """Result of news ingestion."""

    team: str | None = None
    competition: str | None = None
    fetched: int = 0
    indexed: int = 0
    error: str | None = None


class IngestionResponse(BaseModel):
    """Full ingestion response."""

    status: str
    total_indexed: int
    competitions_processed: int | None = None
    teams_processed: int | None = None
    details: list[IngestionResult] = []
    timestamp: str


class SearchResult(BaseModel):
    """Single search result."""

    id: str
    score: float
    title: str
    content: str | None = None
    team_name: str | None = None
    article_type: str | None = None
    published_at: str | None = None
    source: str | None = None


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    results: list[SearchResult]
    total: int
    search_time_ms: float


class CustomArticleRequest(BaseModel):
    """Request to index a custom article."""

    title: str = Field(..., min_length=5, max_length=500)
    content: str | None = Field(None, max_length=5000)
    team_name: str | None = None
    article_type: str = "general"


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get("/stats", response_model=VectorStoreStats, responses=ADMIN_RESPONSES)
async def get_vector_stats(user: AdminUser) -> VectorStoreStats:
    """
    Get vector store statistics.

    Returns information about the Qdrant collection including total vectors.
    Admin role required.
    """
    try:
        from src.vector.search import SemanticSearch

        search = SemanticSearch()  # type: ignore[no-untyped-call]
        stats = search.get_stats()

        return VectorStoreStats(
            collection=stats.get("news_index", {}).get("collection", "news"),
            total_vectors=stats.get("news_index", {}).get("total_vectors", 0),
            status=stats.get("status", "ready"),
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Vector search module not available. Check Qdrant configuration.",
        )
    except Exception as e:
        logger.error(f"Error getting vector stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/team", response_model=IngestionResponse, responses=ADMIN_RESPONSES)
async def ingest_team_news(
    user: AdminUser,
    team_name: str = Query(..., description="Team name to ingest news for"),
    max_articles: int = Query(10, ge=1, le=50, description="Max articles to fetch"),
) -> IngestionResponse:
    """
    Ingest news for a specific team.

    Fetches news articles and indexes them in the vector store.
    Admin role required.
    """
    try:
        from src.vector.news_ingestion import get_ingestion_service

        service = get_ingestion_service()
        result = await service.ingest_team_news(team_name, max_articles)

        return IngestionResponse(
            status="success",
            total_indexed=result.get("indexed", 0),
            teams_processed=1,
            details=[
                IngestionResult(
                    team=result.get("team"),
                    fetched=result.get("fetched", 0),
                    indexed=result.get("indexed", 0),
                )
            ],
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error ingesting team news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/competition", response_model=IngestionResponse, responses=ADMIN_RESPONSES)
async def ingest_competition_news(
    user: AdminUser,
    competition: str = Query(..., description="Competition code (PL, PD, SA, BL1, FL1)"),
    max_per_team: int = Query(5, ge=1, le=20, description="Max articles per team"),
) -> IngestionResponse:
    """
    Ingest news for all teams in a competition.

    Admin role required.
    """
    try:
        from src.vector.news_ingestion import get_ingestion_service

        service = get_ingestion_service()
        result = await service.ingest_competition_news(competition, max_per_team)

        details = []
        for detail in result.get("details", []):
            details.append(
                IngestionResult(
                    team=detail.get("team"),
                    fetched=detail.get("fetched", 0),
                    indexed=detail.get("indexed", 0),
                    error=detail.get("error"),
                )
            )

        return IngestionResponse(
            status="success",
            total_indexed=result.get("total_indexed", 0),
            competitions_processed=1,
            teams_processed=result.get("teams_processed", 0),
            details=details,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error ingesting competition news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/all", response_model=IngestionResponse, responses=ADMIN_RESPONSES)
async def ingest_all_news(
    user: AdminUser,
    max_per_team: int = Query(3, ge=1, le=10, description="Max articles per team"),
) -> IngestionResponse:
    """
    Ingest news for all supported competitions.

    This can take several minutes to complete.
    Admin role required.
    """
    try:
        from src.vector.news_ingestion import get_ingestion_service

        service = get_ingestion_service()
        result = await service.ingest_all_competitions(max_per_team)

        return IngestionResponse(
            status="success",
            total_indexed=result.get("total_indexed", 0),
            competitions_processed=result.get("competitions_processed", 0),
            details=[],  # Too many details, skip for summary
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error ingesting all news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/article", responses=ADMIN_RESPONSES)
async def index_custom_article(
    user: AdminUser,
    article: CustomArticleRequest,
) -> dict[str, Any]:
    """
    Index a custom article manually.

    Useful for adding breaking news or important updates.
    Admin role required.
    """
    try:
        from src.vector.news_ingestion import get_ingestion_service

        service = get_ingestion_service()
        success = service.index_custom_article(
            title=article.title,
            content=article.content,
            team_name=article.team_name,
            article_type=article.article_type,
        )

        return {
            "status": "success" if success else "failed",
            "indexed": success,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error indexing custom article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Premium Endpoints (Search)
# ============================================================================


@router.get("/search", response_model=SearchResponse, responses=PREMIUM_RESPONSES)
async def search_news(
    user: PremiumUser,
    query: str = Query(..., min_length=3, description="Search query"),
    team_name: str | None = Query(None, description="Filter by team name"),
    article_type: str | None = Query(None, description="Filter by type (injury, transfer, form)"),
    limit: int = Query(5, ge=1, le=20, description="Max results"),
) -> SearchResponse:
    """
    Search news articles using semantic search.

    Premium feature - uses vector embeddings for semantic matching.
    """
    import time

    start_time = time.time()

    try:
        from src.vector.news_indexer import NewsIndexer

        indexer = NewsIndexer()  # type: ignore[no-untyped-call]
        results = indexer.search_news(
            query=query,
            team_name=team_name,
            article_type=article_type,
            limit=limit,
            min_score=0.4,
        )

        search_results = [
            SearchResult(
                id=r.get("id", ""),
                score=r.get("score", 0.0),
                title=r.get("title", ""),
                content=r.get("content"),
                team_name=r.get("team_name"),
                article_type=r.get("article_type"),
                published_at=r.get("published_at"),
                source=r.get("source"),
            )
            for r in results
        ]

        elapsed_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=search_results,
            total=len(search_results),
            search_time_ms=round(elapsed_ms, 2),
        )
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-context", responses=PREMIUM_RESPONSES)
async def get_team_context(
    user: PremiumUser,
    team_name: str = Query(..., description="Team name"),
    limit: int = Query(5, ge=1, le=10, description="Max articles per category"),
) -> dict[str, Any]:
    """
    Get comprehensive context for a team.

    Returns categorized news (injuries, transfers, form, etc.).
    Premium feature.
    """
    try:
        from src.vector.news_indexer import NewsIndexer

        indexer = NewsIndexer()  # type: ignore[no-untyped-call]
        context = indexer.get_team_context(team_name, limit=limit)

        return {
            "team_name": team_name,
            "context": context,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting team context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match-context", responses=PREMIUM_RESPONSES)
async def get_match_context(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str | None = Query(None, description="Competition name"),
) -> dict[str, Any]:
    """
    Get semantic context for a match.

    Retrieves relevant news for both teams using vector search.
    Premium feature.
    """
    try:
        from src.vector.search import enrich_with_semantic_search

        context = enrich_with_semantic_search(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
        )

        return {
            "home_team": home_team,
            "away_team": away_team,
            "competition": competition,
            "context": context,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting match context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
