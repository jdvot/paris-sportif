"""RAG (Retrieval Augmented Generation) module for enriching predictions.

This module fetches contextual information from various sources to improve
prediction accuracy:
- Recent news about teams
- Injury/suspension information (structured from football-data.org squad + news)
- Form analysis from multiple sources
- Head-to-head context
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx
from groq import Groq
from pydantic import BaseModel, Field

from src.core.config import settings
from src.data.sources.football_data import SquadPlayer, get_football_data_client

logger = logging.getLogger(__name__)


class StructuredInjury(BaseModel):
    """Structured injury data for a player."""

    player_name: str = Field(description="Player full name")
    position: str | None = Field(default=None, description="Player position")
    injury_type: str = Field(default="unknown", description="Type of injury")
    status: str = Field(default="doubtful", description="doubtful|out|suspended|uncertain")
    expected_return: str | None = Field(default=None, description="Expected return date/timeframe")
    source: str = Field(default="news", description="Data source (api|news)")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this info")


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

    def __init__(self) -> None:
        self.groq_client: Groq | None = None
        if settings.groq_api_key:
            self.groq_client = Groq(api_key=settings.groq_api_key)

    async def get_team_context(self, team_name: str) -> dict[str, Any]:
        """
        Get contextual information about a team.

        Returns:
            dict with keys: news, injuries, form_notes, sentiment
        """
        context: dict[str, Any] = {
            "team": team_name,
            "news": [],
            "injuries": [],
            "form_notes": "",
            "sentiment": "neutral",
            "key_info": [],
            "recent_form": [],
        }

        try:
            # Run multiple fetches in parallel
            news_task = self._fetch_team_news(team_name)
            injuries_task = self._fetch_team_injuries(team_name)
            form_task = self._fetch_team_form(team_name)

            news, injuries, form_data = await asyncio.gather(
                news_task, injuries_task, form_task, return_exceptions=True
            )

            if not isinstance(news, Exception):
                context["news"] = news
            if not isinstance(injuries, Exception):
                context["injuries"] = injuries
            if not isinstance(form_data, Exception):
                context["recent_form"] = form_data.get("results", [])
                context["form_notes"] = form_data.get("summary", "")

            # Analyze sentiment if we have news
            if context["news"] and self.groq_client:
                context["sentiment"] = await self._analyze_sentiment(team_name, context["news"])

            # Generate key info from all sources
            has_content = context["news"] or context["injuries"] or context["recent_form"]
            if self.groq_client and has_content:
                context["key_info"] = await self._extract_key_info(team_name, context)

        except Exception as e:
            logger.error(f"Error getting team context for {team_name}: {e}")

        return context

    async def _fetch_team_news(self, team_name: str, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch recent news about a team from Google News RSS."""
        news: list[dict[str, Any]] = []

        try:
            # Use Google News RSS (free, no API key required)
            search_term = team_name.replace(" ", "+")
            rss_url = f"https://news.google.com/rss/search?q={search_term}+football&hl=fr&gl=FR&ceid=FR:fr"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(rss_url)

                if response.status_code == 200:
                    # Parse RSS XML
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(response.text)

                    items = root.findall(".//item")[:limit]
                    for item in items:
                        title_elem = item.find("title")
                        pub_date_elem = item.find("pubDate")
                        link_elem = item.find("link")

                        if title_elem is not None:
                            news.append(
                                {
                                    "title": title_elem.text,
                                    "date": (
                                        pub_date_elem.text if pub_date_elem is not None else None
                                    ),
                                    "url": link_elem.text if link_elem is not None else None,
                                    "source": "Google News",
                                }
                            )

                    logger.info(f"Fetched {len(news)} news items for {team_name}")

        except Exception as e:
            logger.error(f"Error fetching news for {team_name}: {e}")

        return news

    async def _fetch_team_injuries(self, team_name: str) -> list[dict[str, Any]]:
        """
        Fetch injury/suspension information using structured data from football-data.org.

        Strategy:
        1. Get squad from football-data.org API (structured player names)
        2. Search news for injury mentions matching squad players
        3. Return structured injury data with player names and positions
        """
        injuries: list[dict[str, Any]] = []

        try:
            # Step 1: Get squad from football-data.org
            client = get_football_data_client()
            squad = await client.get_squad_for_team_name(team_name)
            player_names = {p.name.lower(): p for p in squad}

            logger.debug(f"Got squad for {team_name}: {len(squad)} players")

            # Step 2: Search news for injury mentions
            search_term = f"{team_name.replace(' ', '+')}+blessure+injury+absent"
            rss_url = f"https://news.google.com/rss/search?q={search_term}&hl=fr&gl=FR&ceid=FR:fr"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(rss_url)

                if response.status_code == 200:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(response.text)
                    items = root.findall(".//item")[:5]

                    # Keywords to identify injury news (avoid false positives)
                    injury_keywords = ["bless", "injur", "absent", "forfait", "suspen"]
                    exclude_keywords = ["contract", "contrat", "transfer", "prolonge"]

                    for item in items:
                        title_elem = item.find("title")
                        if title_elem is None or not title_elem.text:
                            continue

                        title = title_elem.text
                        title_lower = title.lower()

                        # Skip if contains exclusion keywords (false positives)
                        if any(kw in title_lower for kw in exclude_keywords):
                            continue

                        # Check for injury keywords
                        if not any(kw in title_lower for kw in injury_keywords):
                            continue

                        # Try to match player name from squad
                        matched_player: SquadPlayer | None = None
                        for player_name_lower, player in player_names.items():
                            # Check if player's last name is in title
                            last_name = player_name_lower.split()[-1]
                            if len(last_name) > 3 and last_name in title_lower:
                                matched_player = player
                                break

                        # Determine injury status from keywords
                        status = "uncertain"
                        if "absent" in title_lower or "forfait" in title_lower:
                            status = "out"
                        elif "suspen" in title_lower:
                            status = "suspended"
                        elif "doubt" in title_lower or "incertain" in title_lower:
                            status = "doubtful"

                        injury_data = StructuredInjury(
                            player_name=matched_player.name if matched_player else "Unknown",
                            position=matched_player.position if matched_player else None,
                            injury_type=title[:80],
                            status=status,
                            source="news" if not matched_player else "api+news",
                            confidence=0.8 if matched_player else 0.4,
                        )

                        injuries.append(injury_data.model_dump())

                    logger.info(f"Fetched {len(injuries)} structured injury items for {team_name}")

        except Exception as e:
            logger.error(f"Error fetching injuries for {team_name}: {e}")

        return injuries

    async def _fetch_team_form(self, team_name: str) -> dict[str, Any]:
        """Fetch recent form/results for a team."""
        results_list: list[dict[str, str]] = []
        form_data: dict[str, Any] = {"results": results_list, "summary": ""}

        try:
            # Search for recent match results via Google News
            search_term = f"{team_name.replace(' ', '+')}+résultat+score+match"
            rss_url = f"https://news.google.com/rss/search?q={search_term}&hl=fr&gl=FR&ceid=FR:fr"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(rss_url)

                if response.status_code == 200:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(response.text)

                    items = root.findall(".//item")[:5]
                    for item in items:
                        title_elem = item.find("title")
                        if title_elem is not None and title_elem.text:
                            title = title_elem.text
                            # Look for score patterns (e.g., "2-1", "0-0")
                            import re

                            score_match = re.search(r"\b(\d+)\s*[-:]\s*(\d+)\b", title)
                            if score_match:
                                form_data["results"].append(
                                    {
                                        "headline": title[:100],
                                        "score": f"{score_match.group(1)}-{score_match.group(2)}",
                                    }
                                )

                    # Generate summary
                    if form_data["results"]:
                        form_data["summary"] = f"{len(form_data['results'])} recent results found"

                    result_count = len(form_data["results"])
                    logger.info(f"Fetched form for {team_name}: {result_count} results")

        except Exception as e:
            logger.error(f"Error fetching form for {team_name}: {e}")

        return form_data

    async def _extract_key_info(self, team_name: str, context: dict[str, Any]) -> list[str]:
        """Extract key insights from all context data using LLM."""
        if not self.groq_client:
            return []

        try:
            # Build context summary
            news_titles = [n.get("title", "")[:80] for n in context.get("news", [])[:3]]
            injuries = [i.get("type", "")[:60] for i in context.get("injuries", [])[:2]]
            form = context.get("form_notes", "")

            if not news_titles and not injuries:
                return []

            prompt = f"""Extract 2-3 key facts about {team_name} from this info.
Be concise (max 15 words per fact). Focus on: injuries, transfers, form.

Recent news: {news_titles}
Injury reports: {injuries}
Form: {form}

Reply with bullet points only, in French:"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content
            result = content.strip() if content else ""
            # Parse bullet points
            lines = [line.strip().lstrip("•-").strip() for line in result.split("\n")]
            key_info = [line for line in lines if line]
            return key_info[:3]

        except Exception as e:
            logger.error(f"Error extracting key info: {e}")
            return []

    async def _analyze_sentiment(self, team_name: str, news: list[dict[str, Any]]) -> str:
        """Analyze sentiment from news articles using Groq."""
        if not self.groq_client or not news:
            return "neutral"

        try:
            news_text = "\n".join([n.get("title", "") for n in news[:5]])

            prompt = f"""Analyze the sentiment of these headlines about {team_name}.
Headlines:
{news_text}

Reply with exactly one word: positive, negative, or neutral"""
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content
            sentiment = content.strip().lower() if content else "neutral"
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

            results = await asyncio.gather(home_task, away_task, return_exceptions=True)
            home_ctx: dict[str, Any] | BaseException = results[0]
            away_ctx: dict[str, Any] | BaseException = results[1]

            if not isinstance(home_ctx, BaseException):
                enrichment["home_context"] = home_ctx
            if not isinstance(away_ctx, BaseException):
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
            if (team1 in home_team and team2 in away_team) or (
                team2 in home_team and team1 in away_team
            ):
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
        base_prediction: dict[str, Any],
        enrichment: dict[str, Any],
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
            return str(base_prediction.get("explanation", ""))

        try:
            # Build context from enrichment
            context_parts = []

            home_ctx = enrichment.get("home_context", {})
            away_ctx = enrichment.get("away_context", {})
            match_ctx = enrichment.get("match_context", {})

            # Add key info from both teams
            if home_ctx.get("key_info"):
                context_parts.append(f"Infos clés {home_team}: {'; '.join(home_ctx['key_info'])}")

            if away_ctx.get("key_info"):
                context_parts.append(f"Infos clés {away_team}: {'; '.join(away_ctx['key_info'])}")

            # Add sentiment analysis
            home_sentiment = home_ctx.get("sentiment", "neutral")
            away_sentiment = away_ctx.get("sentiment", "neutral")
            if home_sentiment != "neutral" or away_sentiment != "neutral":
                sentiment_str = f"{home_team}={home_sentiment}, {away_team}={away_sentiment}"
                context_parts.append(f"Sentiment: {sentiment_str}")

            # Add recent form notes
            if home_ctx.get("form_notes"):
                context_parts.append(f"Forme {home_team}: {home_ctx['form_notes']}")
            if away_ctx.get("form_notes"):
                context_parts.append(f"Forme {away_team}: {away_ctx['form_notes']}")

            if home_ctx.get("injuries"):
                inj_list = [i.get("type", "")[:50] for i in home_ctx["injuries"][:2]]
                context_parts.append(f"Blessures {home_team}: {', '.join(inj_list)}")

            if away_ctx.get("injuries"):
                inj_list = [i.get("type", "")[:50] for i in away_ctx["injuries"][:2]]
                context_parts.append(f"Blessures {away_team}: {', '.join(inj_list)}")

            if match_ctx.get("is_derby"):
                context_parts.append("Match: Derby local (rivalité historique)")

            if match_ctx.get("importance") == "high":
                context_parts.append("Importance: Match crucial pour le classement")

            no_context_msg = "Pas d'informations contextuelles"
            context_str = "\n".join(context_parts) if context_parts else no_context_msg

            prompt = f"""Analyse ce match de football et génère une prédiction enrichie.

Match: {home_team} vs {away_team}
Compétition: {match_ctx.get("competition", "League")}

Prédiction de base:
- Victoire {home_team}: {base_prediction.get("home_win", 0):.1%}
- Match nul: {base_prediction.get("draw", 0):.1%}
- Victoire {away_team}: {base_prediction.get("away_win", 0):.1%}

Contexte supplémentaire:
{context_str}

Génère une analyse de 2-3 phrases en français qui prend en compte ces informations contextuelles."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content
            return content.strip() if content else ""

        except Exception as e:
            logger.error(f"Error generating enriched analysis: {e}")
            return str(base_prediction.get("explanation", ""))


# Singleton instance
_rag_enrichment: RAGEnrichment | None = None


def get_rag_enrichment() -> RAGEnrichment:
    """Get RAG enrichment singleton."""
    global _rag_enrichment
    if _rag_enrichment is None:
        _rag_enrichment = RAGEnrichment()
    return _rag_enrichment
