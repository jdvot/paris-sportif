"""RAG (Retrieval Augmented Generation) module for enriching predictions.

This module fetches contextual information from various sources to improve
prediction accuracy:
- Recent news about teams
- Injury/suspension information
- Form analysis from multiple sources
- Head-to-head context
"""

import asyncio
import logging
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import defusedxml.ElementTree as ET
import httpx

from src.core.config import settings
from src.llm.client import GroqClient, get_llm_client

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Limits for news/injury fetching
MAX_NEWS_ITEMS = 5
MAX_HEADLINES_TO_PARSE = 10
MAX_INJURIES_TO_KEEP = 5
MIN_INJURY_CONFIDENCE = 0.5

# LLM token limits
MAX_TOKENS_KEY_INFO = 200
MAX_TOKENS_SENTIMENT = 10
MAX_TOKENS_ANALYSIS = 350


# =============================================================================
# Injury Parsing - Improved patterns to reduce false positives
# =============================================================================


@dataclass
class InjuryInfo:
    """Structured injury information extracted from news."""

    player_name: str | None
    injury_type: str | None
    severity: str  # minor, moderate, serious, unknown
    duration: str | None  # "2-3 weeks", "season", etc.
    headline: str
    confidence: float  # 0.0 to 1.0


class InjuryParser:
    """Parse injury information from news headlines with high precision."""

    # Body parts that indicate injury
    BODY_PARTS = [
        "hamstring",
        "ischio",
        "cuisse",
        "knee",
        "genou",
        "acl",
        "mcl",
        "lcl",
        "ankle",
        "cheville",
        "groin",
        "adducteur",
        "aine",
        "calf",
        "mollet",
        "back",
        "dos",
        "lombaire",
        "shoulder",
        "épaule",
        "hip",
        "hanche",
        "thigh",
        "quadriceps",
        "foot",
        "pied",
        "metatarsal",
        "achilles",
        "tendon",
        "muscle",
        "musculaire",
        "ligament",
    ]

    # Injury action words
    INJURY_ACTIONS = [
        "injured",
        "blessé",
        "blessure",
        "injury",
        "sidelined",
        "sidelines",
        "ruled out",
        "absent",
        "miss",
        "misses",
        "manquera",
        "forfait",
        "surgery",
        "opération",
        "opéré",
        "scan",
        "tests",
        "examen",
        "strain",
        "sprain",
        "tear",
        "rupture",
        "fracture",
        "broken",
        "cassé",
        "doubtful",
        "doubt",
        "incertain",
        "fitness concern",
        "fitness doubt",
        "fitness",
        "limped off",
        "carried off",
        "sorti sur blessure",
        "blow",
        "setback",
        "coup dur",
        "out for",
        "absent pour",
        "return from injury",
        "retour de blessure",
        "knock",
        "minor knock",
        "slight",
        "long-term",
        "long term",
        "concern",
        "problem",
        "issue",
    ]

    # Suspension keywords
    SUSPENSION_KEYWORDS = [
        "suspended",
        "suspendu",
        "suspension",
        "red card",
        "carton rouge",
        "ban",
        "banned",
        "interdit",
        "yellow card accumulation",
        "cumul de cartons",
    ]

    # Duration patterns
    DURATION_PATTERNS = [
        (r"(\d+)\s*(?:to|-)\s*(\d+)\s*weeks?", lambda m: f"{m.group(1)}-{m.group(2)} weeks"),
        (r"(\d+)\s*weeks?", lambda m: f"{m.group(1)} weeks"),
        (r"(\d+)\s*(?:to|-)\s*(\d+)\s*months?", lambda m: f"{m.group(1)}-{m.group(2)} months"),
        (r"(\d+)\s*months?", lambda m: f"{m.group(1)} months"),
        (r"(\d+)\s*(?:to|-)\s*(\d+)\s*jours?", lambda m: f"{m.group(1)}-{m.group(2)} days"),
        (r"(\d+)\s*(?:to|-)\s*(\d+)\s*semaines?", lambda m: f"{m.group(1)}-{m.group(2)} weeks"),
        (r"rest of (?:the )?season", lambda m: "rest of season"),
        (r"fin de saison", lambda m: "rest of season"),
        (r"long[ -]term", lambda m: "long-term"),
        (r"longue durée", lambda m: "long-term"),
    ]

    # FALSE POSITIVE patterns - headlines to EXCLUDE
    FALSE_POSITIVE_PATTERNS = [
        r"out of contract",  # Transfer news
        r"contract (?:runs )?out",  # Contract expiration
        r"speaking out",  # Interviews
        r"lash(?:es)? out",  # Criticism
        r"drops? out of (?:transfer|race|running)",  # Transfer news
        r"rules? out (?:transfer|move|deal|signing)",  # Transfer news
        r"time out",  # Break
        r"knock(?:ed)? out of",  # Competition elimination (any context)
        r"priced out",  # Too expensive
        r"out of favour",  # Not playing
        r"frozen out",  # Not playing
        r"loan move",  # Transfer
        r"transfer target",  # Transfer
        r"interest in",  # Transfer speculation
        r"set to sign",  # Transfer
        r"closes in on",  # Transfer
        r"agrees (?:terms|deal)",  # Transfer
        r"(?:could|may|might) leave",  # Transfer speculation
        r"exit",  # Transfer
        r"departure",  # Transfer
    ]

    @classmethod
    def parse_headline(cls, headline: str, team_name: str) -> InjuryInfo | None:
        """
        Parse a headline for injury information.

        Returns None if not injury-related or if it's a false positive.
        """
        headline_lower = headline.lower()

        # Check for false positives FIRST
        for pattern in cls.FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, headline_lower):
                logger.debug(f"Excluded false positive: {headline[:60]}...")
                return None

        # Check if headline contains injury indicators
        has_body_part = any(bp in headline_lower for bp in cls.BODY_PARTS)
        has_injury_action = any(ia in headline_lower for ia in cls.INJURY_ACTIONS)
        has_suspension = any(sk in headline_lower for sk in cls.SUSPENSION_KEYWORDS)

        # Need at least one injury indicator
        if not (has_body_part or has_injury_action or has_suspension):
            return None

        # Calculate confidence based on indicators
        confidence = 0.4
        if has_body_part:
            confidence += 0.3
        if has_injury_action:
            confidence += 0.2
        if has_suspension:
            confidence += 0.2

        # Extract player name (simple heuristic)
        player_name = cls._extract_player_name(headline, team_name)
        if player_name:
            confidence += 0.1

        # Extract injury type
        injury_type = cls._extract_injury_type(headline_lower)

        # Extract duration
        duration = cls._extract_duration(headline_lower)

        # Determine severity
        severity = cls._estimate_severity(headline_lower, duration)

        return InjuryInfo(
            player_name=player_name,
            injury_type=injury_type,
            severity=severity,
            duration=duration,
            headline=headline[:150],
            confidence=min(confidence, 1.0),
        )

    @classmethod
    def _extract_player_name(cls, headline: str, team_name: str) -> str | None:
        """Extract player name from headline using patterns."""
        # Pattern: "Player Name injured/ruled out/etc"
        # Look for capitalized words before injury keywords
        patterns = [
            # "Mohamed Salah ruled out"
            r"([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+){1,2})\s+(?:ruled out|injured|sidelined|doubtful|set to miss)",
            # "injury blow for Mohamed Salah"
            r"(?:injury|blow|setback)\s+(?:for|to)\s+([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+){1,2})",
            # "Mohamed Salah's injury"
            r"([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+)?)'s\s+(?:injury|fitness|hamstring|knee)",
            # French: "Blessure de Mohamed Salah"
            r"[Bb]lessure\s+(?:de|pour)\s+([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+){1,2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, headline)
            if match:
                name = match.group(1)
                # Exclude team name from being detected as player
                if team_name.lower() not in name.lower():
                    return name

        return None

    @classmethod
    def _extract_injury_type(cls, headline_lower: str) -> str | None:
        """Extract the type of injury."""
        # Check body parts
        for bp in cls.BODY_PARTS:
            if bp in headline_lower:
                return bp

        # Check for suspension
        for sk in cls.SUSPENSION_KEYWORDS:
            if sk in headline_lower:
                return "suspension"

        return None

    @classmethod
    def _extract_duration(cls, headline_lower: str) -> str | None:
        """Extract injury duration from headline."""
        for pattern, formatter in cls.DURATION_PATTERNS:
            match = re.search(pattern, headline_lower)
            if match:
                return formatter(match)
        return None

    @classmethod
    def _estimate_severity(cls, headline_lower: str, duration: str | None) -> str:
        """Estimate injury severity."""
        # Minor keywords - check first (more specific)
        minor_keywords = ["minor", "slight", "small", "little"]
        if any(kw in headline_lower for kw in minor_keywords):
            return "minor"

        # Keywords for serious injuries
        serious_keywords = [
            "surgery",
            "opération",
            "acl",
            "season",
            "long-term",
            "long term",
            "rupture",
        ]
        if any(kw in headline_lower for kw in serious_keywords):
            return "serious"

        # Keywords for moderate injuries
        moderate_keywords = ["weeks", "semaines", "month", "mois", "ruled out", "sidelined"]
        if any(kw in headline_lower for kw in moderate_keywords):
            return "moderate"

        # Duration-based estimation
        if duration:
            if "month" in duration or "season" in duration or "long" in duration:
                return "serious"
            if "week" in duration:
                return "moderate"

        # Minor keywords (less specific)
        minor_secondary = ["doubt", "concern", "knock", "fitness"]
        if any(kw in headline_lower for kw in minor_secondary):
            return "minor"

        return "unknown"


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
        # Use centralized LLM client with retry logic and error handling
        self.llm_client: GroqClient | None = None
        if settings.groq_api_key:
            self.llm_client = get_llm_client()
            logger.info("RAG enrichment initialized with LLM client")

        # Initialize semantic search (optional, graceful degradation)
        self.semantic_search = None
        try:
            from src.vector.search import SemanticSearch

            self.semantic_search = SemanticSearch()
            logger.info("RAG enrichment initialized with semantic search")
        except Exception as e:
            logger.warning(f"Semantic search not available: {e}")

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
            semantic_task = self._fetch_semantic_context(team_name)

            news, injuries, form_data, semantic_context = await asyncio.gather(
                news_task, injuries_task, form_task, semantic_task, return_exceptions=True
            )

            # Handle results with proper exception logging
            if isinstance(news, Exception):
                logger.warning(f"Failed to fetch news for {team_name}: {news}")
            else:
                context["news"] = news

            if isinstance(injuries, Exception):
                logger.warning(f"Failed to fetch injuries for {team_name}: {injuries}")
            else:
                context["injuries"] = injuries

            if isinstance(form_data, Exception):
                logger.warning(f"Failed to fetch form for {team_name}: {form_data}")
            else:
                context["recent_form"] = form_data.get("results", [])
                context["form_notes"] = form_data.get("summary", "")

            # Merge semantic search results (enhanced context)
            if isinstance(semantic_context, Exception):
                logger.warning(f"Semantic search failed for {team_name}: {semantic_context}")
            elif semantic_context:
                context["semantic_news"] = semantic_context.get("news", [])
                context["semantic_injuries"] = semantic_context.get("injuries", [])
                # Merge unique news titles from semantic search
                existing_titles = {n.get("title", "").lower() for n in context["news"]}
                for sem_news in semantic_context.get("news", []):
                    if sem_news.get("title", "").lower() not in existing_titles:
                        context["news"].append(
                            {
                                "title": sem_news.get("title"),
                                "date": sem_news.get("published_at"),
                                "url": sem_news.get("url"),
                                "source": f"Semantic ({sem_news.get('source', 'cache')})",
                                "score": sem_news.get("score"),
                            }
                        )

            # Analyze sentiment if we have news
            if context["news"] and self.llm_client:
                context["sentiment"] = await self._analyze_sentiment(team_name, context["news"])

            # Generate key info from all sources
            has_content = context["news"] or context["injuries"] or context["recent_form"]
            if self.llm_client and has_content:
                context["key_info"] = await self._extract_key_info(team_name, context)

        except Exception as e:
            logger.error(f"Error getting team context for {team_name}: {e}")

        return context

    async def _fetch_team_news(
        self, team_name: str, limit: int = MAX_NEWS_ITEMS
    ) -> list[dict[str, Any]]:
        """Fetch recent news about a team from Google News RSS."""
        news: list[dict[str, Any]] = []

        try:
            # Use Google News RSS (free, no API key required)
            search_term = quote(team_name)
            rss_url = f"https://news.google.com/rss/search?q={search_term}+football&hl=fr&gl=FR&ceid=FR:fr"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(rss_url)

                if response.status_code == 200:
                    # Parse RSS XML using defusedxml (XXE protection)
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

    async def _fetch_semantic_context(self, team_name: str) -> dict[str, Any] | None:
        """Fetch context using semantic search (Qdrant).

        This provides additional context by searching indexed news articles
        using vector similarity instead of keyword matching.

        Returns:
            Dict with news and injuries from semantic search, or None if unavailable
        """
        if not self.semantic_search:
            return None

        try:
            # Get team context from semantic search
            context = self.semantic_search.news_indexer.get_team_context(
                team_name=team_name,
                context_query="injury news form performance",
                limit=3,
            )

            return {
                "news": context.get("general", []) + context.get("form", []),
                "injuries": context.get("injuries", []),
                "transfers": context.get("transfers", []),
                "total_found": context.get("total_articles", 0),
            }
        except Exception as e:
            logger.warning(f"Semantic search error for {team_name}: {e}")
            return None

    async def _fetch_team_injuries(self, team_name: str) -> list[dict[str, Any]]:
        """
        Fetch injury/suspension information for a team from Google News.

        Uses improved InjuryParser to reduce false positives and extract
        structured information (player name, injury type, severity, duration).
        """
        injuries: list[dict[str, Any]] = []

        try:
            # Search for injury-related news in both English and French
            encoded_team = quote(team_name)
            search_queries = [
                f"{encoded_team}+injury+injured",
                f"{encoded_team}+blessure+blessé",
                f"{encoded_team}+ruled+out",
                f"{encoded_team}+suspendu+suspended",
            ]

            all_headlines: list[tuple[str, str | None]] = []

            async with httpx.AsyncClient(timeout=10.0) as client:
                for query in search_queries:
                    rss_url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"

                    try:
                        response = await client.get(rss_url)

                        if response.status_code == 200:
                            # Parse RSS XML using defusedxml (XXE protection)
                            root = ET.fromstring(response.text)
                            items = root.findall(".//item")[:5]

                            for item in items:
                                title_elem = item.find("title")
                                pub_date_elem = item.find("pubDate")
                                if title_elem is not None and title_elem.text:
                                    pub_date = (
                                        pub_date_elem.text if pub_date_elem is not None else None
                                    )
                                    all_headlines.append((title_elem.text, pub_date))

                    except Exception as e:
                        logger.debug(f"Error fetching query '{query}': {e}")
                        continue

            # Deduplicate headlines
            seen_headlines: set[str] = set()
            unique_headlines: list[tuple[str, str | None]] = []
            for headline, pub_date in all_headlines:
                normalized = headline.lower()[:50]
                if normalized not in seen_headlines:
                    seen_headlines.add(normalized)
                    unique_headlines.append((headline, pub_date))

            # Parse each headline with the improved parser
            for headline, pub_date in unique_headlines[:MAX_HEADLINES_TO_PARSE]:
                injury_info = InjuryParser.parse_headline(headline, team_name)

                if injury_info and injury_info.confidence >= MIN_INJURY_CONFIDENCE:
                    injury_dict: dict[str, Any] = {
                        "player": injury_info.player_name or "Unknown player",
                        "type": injury_info.injury_type or "injury",
                        "severity": injury_info.severity,
                        "duration": injury_info.duration,
                        "headline": injury_info.headline,
                        "source": "Google News",
                        "confidence": injury_info.confidence,
                        "pub_date": pub_date,
                    }
                    injuries.append(injury_dict)

            # Sort by confidence and limit
            injuries.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            injuries = injuries[:MAX_INJURIES_TO_KEEP]

            logger.info(
                f"Fetched {len(injuries)} validated injury items for {team_name} "
                f"(from {len(unique_headlines)} headlines)"
            )

        except Exception as e:
            logger.error(f"Error fetching injuries for {team_name}: {e}")

        return injuries

    async def _fetch_team_form(self, team_name: str) -> dict[str, Any]:
        """Fetch recent form/results for a team."""
        results_list: list[dict[str, str]] = []
        form_data: dict[str, Any] = {"results": results_list, "summary": ""}

        try:
            # Search for recent match results via Google News
            search_term = quote(f"{team_name} résultat score match")
            rss_url = f"https://news.google.com/rss/search?q={search_term}&hl=fr&gl=FR&ceid=FR:fr"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(rss_url)

                if response.status_code == 200:
                    # Parse RSS XML using defusedxml (XXE protection)
                    root = ET.fromstring(response.text)

                    items = root.findall(".//item")[:MAX_NEWS_ITEMS]
                    for item in items:
                        title_elem = item.find("title")
                        if title_elem is not None and title_elem.text:
                            title = title_elem.text
                            # Look for score patterns (e.g., "2-1", "0-0")
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
        """Extract key insights from all context data using centralized LLM client."""
        if not self.llm_client:
            return []

        try:
            # Build context summary
            news_titles = [
                n.get("title", "")[:100] for n in context.get("news", [])[:MAX_NEWS_ITEMS]
            ]
            injuries = [
                f"{i.get('player', 'Joueur inconnu')}: {i.get('type', 'blessure')}"
                for i in context.get("injuries", [])[:3]
            ]
            form = context.get("form_notes", "")

            if not news_titles and not injuries:
                return []

            prompt = f"""Tu es un analyste football expert. Extrais les 3 informations les plus importantes pour prédire le prochain match de {team_name}.

DONNÉES:
- Actualités: {news_titles}
- Blessures/Absences: {injuries if injuries else "Aucune signalée"}
- Forme récente: {form if form else "Non disponible"}

INSTRUCTIONS:
- Retourne exactement 3 points clés
- Maximum 20 mots par point
- Focus: blessures majeures, forme, moral, contexte tactique
- Format: une ligne par point, sans numérotation ni puces

Réponds en français:"""

            # Use centralized async client with retry logic
            content = await self.llm_client.complete(
                prompt=prompt,
                max_tokens=MAX_TOKENS_KEY_INFO,
                temperature=0.2,
            )

            result = content.strip() if content else ""
            # Parse lines
            lines = [line.strip().lstrip("•-123.").strip() for line in result.split("\n")]
            key_info = [line for line in lines if line and len(line) > 5]
            return key_info[:3]

        except Exception as e:
            logger.error(f"Error extracting key info for {team_name}: {e}")
            return []

    async def _analyze_sentiment(self, team_name: str, news: list[dict[str, Any]]) -> str:
        """Analyze sentiment from news articles using centralized LLM client."""
        if not self.llm_client or not news:
            return "neutral"

        try:
            news_text = "\n".join([f"- {n.get('title', '')}" for n in news[:5]])

            prompt = f"""Analyse le sentiment général des actualités concernant {team_name}.

TITRES RÉCENTS:
{news_text}

INSTRUCTION: Réponds par UN SEUL mot parmi: positive, negative, neutral
- positive = bonnes nouvelles, victoires, confiance
- negative = défaites, blessures, crises
- neutral = actualités mixtes ou sans impact

Réponse:"""

            content = await self.llm_client.complete(
                prompt=prompt,
                max_tokens=MAX_TOKENS_SENTIMENT,
                temperature=0.1,
            )

            sentiment = content.strip().lower().split()[0] if content else "neutral"
            if sentiment in ["positive", "negative", "neutral"]:
                return sentiment

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {team_name}: {e}")

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

            # Handle results with proper exception logging
            if isinstance(home_ctx, BaseException):
                logger.warning(f"Failed to get context for {home_team}: {home_ctx}")
            else:
                enrichment["home_context"] = home_ctx

            if isinstance(away_ctx, BaseException):
                logger.warning(f"Failed to get context for {away_team}: {away_ctx}")
            else:
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
        if not self.llm_client:
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

            no_context_msg = "Aucune information contextuelle disponible"
            context_str = (
                "\n".join(f"• {part}" for part in context_parts)
                if context_parts
                else no_context_msg
            )

            home_prob = base_prediction.get("home_win", 0)
            draw_prob = base_prediction.get("draw", 0)
            away_prob = base_prediction.get("away_win", 0)
            confidence = base_prediction.get("confidence", 0.5)

            prompt = f"""Tu es un analyste football professionnel. Génère une analyse experte pour ce match.

═══════════════════════════════════════════════════
MATCH: {home_team} (domicile) vs {away_team} (extérieur)
COMPÉTITION: {match_ctx.get("competition", "Championnat")}
═══════════════════════════════════════════════════

PROBABILITÉS (modèle ML):
• Victoire {home_team}: {home_prob:.0%}
• Match nul: {draw_prob:.0%}
• Victoire {away_team}: {away_prob:.0%}
• Confiance du modèle: {confidence:.0%}

CONTEXTE ACTUEL:
{context_str}

═══════════════════════════════════════════════════

INSTRUCTIONS:
1. Analyse les probabilités vs le contexte actuel
2. Identifie les facteurs qui pourraient influencer le résultat
3. Donne ton avis d'expert en 2-3 phrases percutantes
4. Mentionne le pick recommandé avec la raison principale

Réponds en français, style professionnel:"""

            content = await self.llm_client.complete(
                prompt=prompt,
                max_tokens=MAX_TOKENS_ANALYSIS,
                temperature=0.4,
            )

            return content.strip() if content else ""

        except Exception as e:
            logger.error(f"Error generating enriched analysis for {home_team} vs {away_team}: {e}")
            return str(base_prediction.get("explanation", ""))


# Thread-safe singleton instance
_rag_enrichment: RAGEnrichment | None = None
_rag_lock = threading.Lock()


def get_rag_enrichment() -> RAGEnrichment:
    """Get RAG enrichment singleton (thread-safe)."""
    global _rag_enrichment
    if _rag_enrichment is None:
        with _rag_lock:
            # Double-check locking pattern
            if _rag_enrichment is None:
                _rag_enrichment = RAGEnrichment()
    return _rag_enrichment
