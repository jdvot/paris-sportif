"""News ingestion service for semantic search.

Fetches news from various sources and indexes them in Qdrant
for the RAG pipeline.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.vector.news_indexer import NewsArticle, NewsIndexer

logger = logging.getLogger(__name__)


class NewsIngestionService:
    """Fetch and index news from various sources."""

    # Team name mappings for football-data.org API
    TEAM_IDS = {
        # Premier League
        "Arsenal": 57,
        "Chelsea": 61,
        "Manchester United": 66,
        "Manchester City": 65,
        "Liverpool": 64,
        "Tottenham": 73,
        "Newcastle": 67,
        "Aston Villa": 58,
        "Brighton": 397,
        "West Ham": 563,
        "Fulham": 63,
        "Crystal Palace": 354,
        "Brentford": 402,
        "Everton": 62,
        "Nottingham Forest": 351,
        "Bournemouth": 1044,
        "Wolves": 76,
        "Leicester": 338,
        # La Liga
        "Real Madrid": 86,
        "Barcelona": 81,
        "Atletico Madrid": 78,
        "Sevilla": 559,
        "Real Betis": 90,
        "Valencia": 95,
        "Villarreal": 94,
        "Athletic Club": 77,
        "Real Sociedad": 92,
        # Serie A
        "Juventus": 109,
        "AC Milan": 98,
        "Inter": 108,
        "Napoli": 113,
        "AS Roma": 100,
        "Lazio": 110,
        "Fiorentina": 99,
        "Atalanta": 102,
        # Bundesliga
        "Bayern Munich": 5,
        "Borussia Dortmund": 4,
        "RB Leipzig": 721,
        "Bayer Leverkusen": 3,
        "Eintracht Frankfurt": 19,
        "Union Berlin": 28,
        "Freiburg": 17,
        "Wolfsburg": 11,
        # Ligue 1
        "PSG": 524,
        "Paris Saint-Germain": 524,
        "Marseille": 516,
        "Lyon": 523,
        "Monaco": 548,
        "Lille": 521,
        "Nice": 522,
        "Lens": 546,
        "Rennes": 529,
    }

    # Competition codes
    COMPETITIONS = {
        "PL": "Premier League",
        "PD": "La Liga",
        "BL1": "Bundesliga",
        "SA": "Serie A",
        "FL1": "Ligue 1",
        "CL": "Champions League",
    }

    def __init__(self):
        self.indexer = NewsIndexer()

    async def fetch_team_news_from_api(
        self,
        team_name: str,
        max_articles: int = 10,
    ) -> list[NewsArticle]:
        """Fetch news for a team from public APIs.

        Uses NewsAPI (if configured) or simulated news for development.
        """
        articles = []

        # Try to fetch from NewsAPI (if API key is available)
        # For now, we'll generate simulated news for development
        articles.extend(
            self._generate_simulated_news(team_name, max_articles)
        )

        return articles

    def _generate_simulated_news(
        self,
        team_name: str,
        count: int = 5,
    ) -> list[NewsArticle]:
        """Generate simulated news articles for development.

        In production, this would be replaced with real API calls.
        """
        now = datetime.utcnow()
        templates = [
            {
                "title": f"{team_name} prepare for crucial upcoming fixture",
                "content": f"The {team_name} squad has been training hard this week in preparation for their upcoming fixture. Manager expressed confidence in the team's form.",
                "type": "general",
            },
            {
                "title": f"Key player ruled out for {team_name}",
                "content": f"{team_name} will be without their key midfielder for the upcoming match due to a muscle injury sustained in training. Recovery expected in 2-3 weeks.",
                "type": "injury",
            },
            {
                "title": f"{team_name} on impressive winning streak",
                "content": f"{team_name} have extended their unbeaten run to 5 matches, showcasing excellent form in recent weeks. The team's defensive record has been particularly impressive.",
                "type": "form",
            },
            {
                "title": f"{team_name} linked with January transfer move",
                "content": f"Transfer rumors suggest {team_name} are monitoring several targets ahead of the January window. Sources indicate a bid may be made for a young striker.",
                "type": "transfer",
            },
            {
                "title": f"Match preview: What to expect from {team_name}",
                "content": f"Analysts preview the upcoming clash featuring {team_name}. Key battles in midfield expected to determine the outcome.",
                "type": "preview",
            },
        ]

        articles = []
        for i, template in enumerate(templates[:count]):
            articles.append(
                NewsArticle(
                    title=template["title"],
                    content=template["content"],
                    source="simulated",
                    published_at=now - timedelta(days=i),
                    team_name=team_name,
                    team_id=self.TEAM_IDS.get(team_name),
                    article_type=template["type"],
                )
            )

        return articles

    async def ingest_team_news(
        self,
        team_name: str,
        max_articles: int = 10,
    ) -> dict[str, Any]:
        """Fetch and index news for a specific team."""
        logger.info(f"Ingesting news for {team_name}")

        articles = await self.fetch_team_news_from_api(team_name, max_articles)
        indexed = self.indexer.index_articles(articles)

        return {
            "team": team_name,
            "fetched": len(articles),
            "indexed": indexed,
        }

    async def ingest_competition_news(
        self,
        competition: str,
        max_per_team: int = 5,
    ) -> dict[str, Any]:
        """Ingest news for all teams in a competition."""
        logger.info(f"Ingesting news for competition: {competition}")

        # Get teams for competition
        teams = self._get_competition_teams(competition)
        results = []

        for team in teams:
            try:
                result = await self.ingest_team_news(team, max_per_team)
                results.append(result)
            except Exception as e:
                logger.error(f"Error ingesting news for {team}: {e}")
                results.append({
                    "team": team,
                    "error": str(e),
                })

        total_indexed = sum(r.get("indexed", 0) for r in results)

        return {
            "competition": competition,
            "teams_processed": len(results),
            "total_indexed": total_indexed,
            "details": results,
        }

    def _get_competition_teams(self, competition: str) -> list[str]:
        """Get list of team names for a competition."""
        teams_by_comp = {
            "PL": [
                "Arsenal", "Chelsea", "Manchester United", "Manchester City",
                "Liverpool", "Tottenham", "Newcastle", "Aston Villa",
                "Brighton", "West Ham", "Fulham", "Crystal Palace",
                "Brentford", "Everton", "Nottingham Forest", "Bournemouth",
                "Wolves", "Leicester",
            ],
            "PD": [
                "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
                "Real Betis", "Valencia", "Villarreal", "Athletic Club",
                "Real Sociedad",
            ],
            "SA": [
                "Juventus", "AC Milan", "Inter", "Napoli",
                "AS Roma", "Lazio", "Fiorentina", "Atalanta",
            ],
            "BL1": [
                "Bayern Munich", "Borussia Dortmund", "RB Leipzig",
                "Bayer Leverkusen", "Eintracht Frankfurt", "Union Berlin",
                "Freiburg", "Wolfsburg",
            ],
            "FL1": [
                "PSG", "Marseille", "Lyon", "Monaco",
                "Lille", "Nice", "Lens", "Rennes",
            ],
        }
        return teams_by_comp.get(competition, [])

    async def ingest_all_competitions(
        self,
        max_per_team: int = 3,
    ) -> dict[str, Any]:
        """Ingest news for all supported competitions."""
        logger.info("Ingesting news for all competitions")

        results = []
        for comp_code in ["PL", "PD", "SA", "BL1", "FL1"]:
            try:
                result = await self.ingest_competition_news(comp_code, max_per_team)
                results.append(result)
            except Exception as e:
                logger.error(f"Error ingesting competition {comp_code}: {e}")
                results.append({
                    "competition": comp_code,
                    "error": str(e),
                })

        total_indexed = sum(r.get("total_indexed", 0) for r in results)

        return {
            "competitions_processed": len(results),
            "total_indexed": total_indexed,
            "details": results,
        }

    def index_custom_article(
        self,
        title: str,
        content: str | None = None,
        team_name: str | None = None,
        article_type: str = "general",
        source: str = "manual",
    ) -> bool:
        """Index a custom article manually."""
        article = NewsArticle(
            title=title,
            content=content,
            source=source,
            published_at=datetime.utcnow(),
            team_name=team_name,
            team_id=self.TEAM_IDS.get(team_name) if team_name else None,
            article_type=article_type,
        )
        return self.indexer.index_article(article)

    def get_stats(self) -> dict[str, Any]:
        """Get ingestion statistics."""
        return {
            "indexer_stats": self.indexer.get_stats(),
            "supported_competitions": list(self.COMPETITIONS.keys()),
            "known_teams": len(self.TEAM_IDS),
        }


# Singleton instance
_ingestion_service: NewsIngestionService | None = None


def get_ingestion_service() -> NewsIngestionService:
    """Get or create news ingestion service."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = NewsIngestionService()
    return _ingestion_service
