"""RAG (Retrieval Augmented Generation) module for enriching predictions.

This module fetches contextual information from various sources to improve
prediction accuracy:
- Recent news about teams
- Injury/suspension information
- Form analysis from multiple sources
- Head-to-head context
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any
import httpx
from groq import Groq

from src.core.config import settings

logger = logging.getLogger(__name__)


class RAGEnrichment:
    """Retrieves and processes contextual data for match predictions."""

    # News sources (free/accessible)
    NEWS_SOURCES = {
        "football_italia": "https://football-italia.net",
        "espn": "https://www.espn.com/soccer",
        "goal": "https://www.goal.com",
    }

    # Team name mappings for search
    TEAM_ALIASES = {
        "Manchester City": ["Man City", "City", "MCFC"],
        "Manchester United": ["Man United", "United", "MUFC"],
        "Liverpool": ["LFC", "Reds"],
        "Chelsea": ["CFC", "Blues"],
        "Arsenal": ["Gunners", "AFC"],
        "Real Madrid": ["Madrid", "Los Blancos"],
        "Barcelona": ["Barca", "Blaugrana"],
        "Bayern Munich": ["Bayern", "FCB"],
        "PSG": ["Paris Saint-Germain", "Paris"],
        "Juventus": ["Juve", "Bianconeri"],
        "Inter": ["Inter Milan", "Nerazzurri"],
        "AC Milan": ["Milan", "Rossoneri"],
    }

    def __init__(self):
        self.groq_client = None
        if settings.groq_api_key:
            self.groq_client = Groq(api_key=settings.groq_api_key)

    async def get_team_context(self, team_name: str) -> dict[str, Any]:
        """
        Get contextual information about a team.

        Returns:
            dict with keys: news, injuries, form_notes, sentiment
        """
        context = {
            "team": team_name,
            "news": [],
            "injuries": [],
            "form_notes": "",
            "sentiment": "neutral",
            "key_info": [],
        }

        try:
            # Run multiple fetches in parallel
            news_task = self._fetch_team_news(team_name)
            injuries_task = self._fetch_team_injuries(team_name)

            news, injuries = await asyncio.gather(
                news_task, injuries_task,
                return_exceptions=True
            )

            if not isinstance(news, Exception):
                context["news"] = news
            if not isinstance(injuries, Exception):
                context["injuries"] = injuries

            # Analyze sentiment if we have news
            if context["news"] and self.groq_client:
                context["sentiment"] = await self._analyze_sentiment(team_name, context["news"])

        except Exception as e:
            logger.error(f"Error getting team context for {team_name}: {e}")

        return context

    async def _fetch_team_news(self, team_name: str, limit: int = 5) -> list[dict]:
        """Fetch recent news about a team."""
        news = []

        try:
            # Use a simple approach - could be enhanced with actual news APIs
            # For now, return placeholder indicating no external news API configured
            logger.info(f"News fetch for {team_name} - external API not configured")

            # Could integrate with:
            # - NewsAPI (free tier: 100 req/day)
            # - Google News RSS
            # - Team official Twitter/X feeds

        except Exception as e:
            logger.error(f"Error fetching news for {team_name}: {e}")

        return news

    async def _fetch_team_injuries(self, team_name: str) -> list[dict]:
        """Fetch injury/suspension information for a team."""
        injuries = []

        try:
            # Could integrate with:
            # - Transfermarkt (unofficial scraping)
            # - FotMob API
            # - Team official announcements

            logger.info(f"Injuries fetch for {team_name} - external API not configured")

        except Exception as e:
            logger.error(f"Error fetching injuries for {team_name}: {e}")

        return injuries

    async def _analyze_sentiment(self, team_name: str, news: list[dict]) -> str:
        """Analyze sentiment from news articles using Groq."""
        if not self.groq_client or not news:
            return "neutral"

        try:
            news_text = "\n".join([n.get("title", "") for n in news[:5]])

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze the sentiment of these news headlines about {team_name} football team.
Headlines:
{news_text}

Reply with exactly one word: positive, negative, or neutral"""
                }]
            )

            sentiment = response.choices[0].message.content.strip().lower()
            if sentiment in ["positive", "negative", "neutral"]:
                return sentiment

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")

        return "neutral"

    async def enrich_match_prediction(
        self,
        home_team: str,
        away_team: str,
        competition: str,
        match_date: datetime,
    ) -> dict[str, Any]:
        """
        Enrich a match prediction with contextual data.

        Returns:
            dict with enrichment data for both teams
        """
        enrichment = {
            "home_context": {},
            "away_context": {},
            "match_context": {},
            "enriched_at": datetime.now().isoformat(),
        }

        try:
            # Fetch context for both teams in parallel
            home_task = self.get_team_context(home_team)
            away_task = self.get_team_context(away_team)

            home_ctx, away_ctx = await asyncio.gather(
                home_task, away_task,
                return_exceptions=True
            )

            if not isinstance(home_ctx, Exception):
                enrichment["home_context"] = home_ctx
            if not isinstance(away_ctx, Exception):
                enrichment["away_context"] = away_ctx

            # Add match-specific context
            enrichment["match_context"] = {
                "competition": competition,
                "match_date": match_date.isoformat(),
                "is_derby": self._is_derby(home_team, away_team),
                "importance": self._estimate_match_importance(competition, match_date),
            }

        except Exception as e:
            logger.error(f"Error enriching match {home_team} vs {away_team}: {e}")

        return enrichment

    def _is_derby(self, home_team: str, away_team: str) -> bool:
        """Check if match is a derby (local rivalry)."""
        derbies = [
            ("Manchester City", "Manchester United"),
            ("Liverpool", "Everton"),
            ("Arsenal", "Tottenham"),
            ("Real Madrid", "Atletico Madrid"),
            ("Barcelona", "Espanyol"),
            ("Inter", "AC Milan"),
            ("Juventus", "Torino"),
            ("PSG", "Marseille"),
            ("Bayern Munich", "1860 Munich"),
            ("Borussia Dortmund", "Schalke 04"),
        ]

        for team1, team2 in derbies:
            if (team1 in home_team and team2 in away_team) or \
               (team2 in home_team and team1 in away_team):
                return True

        return False

    def _estimate_match_importance(self, competition: str, match_date: datetime) -> str:
        """Estimate match importance based on competition and timing."""
        # High importance competitions
        if competition in ["Champions League", "CL", "Europa League", "EL"]:
            return "high"

        # Check if late season (April-May typically more important)
        month = match_date.month
        if month in [4, 5]:
            return "high"

        # Early season
        if month in [8, 9]:
            return "low"

        return "medium"

    async def generate_enriched_analysis(
        self,
        home_team: str,
        away_team: str,
        base_prediction: dict,
        enrichment: dict,
    ) -> str:
        """
        Generate an enriched analysis using Groq with RAG context.

        Args:
            home_team: Home team name
            away_team: Away team name
            base_prediction: Base statistical prediction
            enrichment: Contextual enrichment data

        Returns:
            Enhanced analysis text
        """
        if not self.groq_client:
            return base_prediction.get("explanation", "")

        try:
            # Build context from enrichment
            context_parts = []

            home_ctx = enrichment.get("home_context", {})
            away_ctx = enrichment.get("away_context", {})
            match_ctx = enrichment.get("match_context", {})

            if home_ctx.get("injuries"):
                context_parts.append(f"Blessures {home_team}: {', '.join([i.get('player', '') for i in home_ctx['injuries']])}")

            if away_ctx.get("injuries"):
                context_parts.append(f"Blessures {away_team}: {', '.join([i.get('player', '') for i in away_ctx['injuries']])}")

            if match_ctx.get("is_derby"):
                context_parts.append("Match: Derby local (rivalité historique)")

            if match_ctx.get("importance") == "high":
                context_parts.append("Importance: Match crucial pour le classement")

            context_str = "\n".join(context_parts) if context_parts else "Pas d'informations contextuelles supplémentaires"

            prompt = f"""Analyse ce match de football et génère une prédiction enrichie.

Match: {home_team} vs {away_team}
Compétition: {match_ctx.get('competition', 'League')}

Prédiction de base:
- Victoire {home_team}: {base_prediction.get('home_win', 0):.1%}
- Match nul: {base_prediction.get('draw', 0):.1%}
- Victoire {away_team}: {base_prediction.get('away_win', 0):.1%}

Contexte supplémentaire:
{context_str}

Génère une analyse de 2-3 phrases en français qui prend en compte ces informations contextuelles."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating enriched analysis: {e}")
            return base_prediction.get("explanation", "")


# Singleton instance
_rag_enrichment: RAGEnrichment | None = None


def get_rag_enrichment() -> RAGEnrichment:
    """Get RAG enrichment singleton."""
    global _rag_enrichment
    if _rag_enrichment is None:
        _rag_enrichment = RAGEnrichment()
    return _rag_enrichment
