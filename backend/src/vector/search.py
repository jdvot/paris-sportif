"""Semantic search API for RAG pipeline.

Provides high-level search functions for the prediction system.
"""

import logging
from datetime import datetime
from typing import Any

from src.vector.news_indexer import NewsIndexer

logger = logging.getLogger(__name__)

# Singleton indexer
_news_indexer: NewsIndexer | None = None


def get_news_indexer() -> NewsIndexer:
    """Get or create news indexer."""
    global _news_indexer
    if _news_indexer is None:
        _news_indexer = NewsIndexer()
    return _news_indexer


class SemanticSearch:
    """High-level semantic search for RAG enrichment."""

    def __init__(self):
        self.news_indexer = get_news_indexer()

    def search_match_context(
        self,
        home_team: str,
        away_team: str,
        competition: str | None = None,
        match_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive context for a match.

        Searches for relevant news about both teams and the matchup.

        Args:
            home_team: Home team name
            away_team: Away team name
            competition: Competition name (optional)
            match_date: Match date (optional, for relevance)

        Returns:
            Dict with context for both teams
        """
        logger.info(f"Searching context for {home_team} vs {away_team}")

        # Get context for both teams
        home_context = self.news_indexer.get_team_context(
            team_name=home_team,
            context_query=f"news injuries form {competition or ''}",
        )

        away_context = self.news_indexer.get_team_context(
            team_name=away_team,
            context_query=f"news injuries form {competition or ''}",
        )

        # Search for head-to-head news
        h2h_query = f"{home_team} vs {away_team} match preview"
        h2h_news = self.news_indexer.search_news(
            query=h2h_query,
            limit=3,
            min_score=0.4,
        )

        return {
            "home_team": home_context,
            "away_team": away_context,
            "head_to_head": h2h_news,
            "searched_at": datetime.utcnow().isoformat(),
        }

    def search_injuries(
        self,
        team_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search specifically for injury news.

        Args:
            team_name: Team to search for
            limit: Max results

        Returns:
            List of injury-related articles
        """
        return self.news_indexer.search_news(
            query=f"{team_name} injury injured ruled out doubt",
            team_name=team_name,
            article_type="injury",
            limit=limit,
            min_score=0.5,
            max_age_days=14,
        )

    def search_form(
        self,
        team_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for team form and performance news.

        Args:
            team_name: Team to search for
            limit: Max results

        Returns:
            List of form-related articles
        """
        return self.news_indexer.search_news(
            query=f"{team_name} form performance winning streak results",
            team_name=team_name,
            article_type="form",
            limit=limit,
            min_score=0.4,
            max_age_days=14,
        )

    def search_similar_query(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Generic semantic search.

        Args:
            query: Natural language query
            limit: Max results

        Returns:
            List of relevant articles
        """
        return self.news_indexer.search_news(
            query=query,
            limit=limit,
            min_score=0.5,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get search system statistics."""
        return {
            "news_index": self.news_indexer.get_stats(),
            "status": "ready",
        }


# Convenience function for RAG enrichment
def enrich_with_semantic_search(
    home_team: str,
    away_team: str,
    competition: str | None = None,
) -> dict[str, Any]:
    """Enrich match prediction with semantic search.

    This is the main entry point for the RAG pipeline.

    Args:
        home_team: Home team name
        away_team: Away team name
        competition: Competition name

    Returns:
        Enriched context for LLM analysis
    """
    search = SemanticSearch()
    return search.search_match_context(
        home_team=home_team,
        away_team=away_team,
        competition=competition,
    )
