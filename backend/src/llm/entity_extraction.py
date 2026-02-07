"""LLM-based entity extraction for news articles (NER).

Extracts teams, players, and competitions from football news articles
using Groq LLM with regex fallback. Supports bilingual FR/EN content.

Architecture:
- batch_extract(): 8B model, batches of 5 articles (for ingestion pipeline)
- deep_extract(): 70B model, single article (for RAG enrichment)
- _regex_fallback(): InjuryParser + keyword detection (when LLM unavailable)

Cache:
- ner:batch:{md5} → 6h TTL
- ner:deep:{md5}  → 12h TTL
"""

import hashlib
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel

from src.core.cache import cache_get, cache_set
from src.llm.client import GroqClient, get_llm_client

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class ExtractedTeam(BaseModel):
    """A team entity extracted from text."""

    name: str
    canonical_name: str | None = None
    role: Literal["subject", "opponent", "mentioned"] = "mentioned"
    confidence: float = 0.5


class ExtractedPlayer(BaseModel):
    """A player entity extracted from text."""

    name: str
    team: str | None = None
    context: Literal["injury", "transfer", "performance", "suspension", "return", "general"] = (
        "general"
    )
    confidence: float = 0.5


class ExtractedCompetition(BaseModel):
    """A competition entity extracted from text."""

    name: str
    canonical_code: str | None = None
    confidence: float = 0.5


class ArticleEntities(BaseModel):
    """All entities extracted from a single article."""

    teams: list[ExtractedTeam] = []
    players: list[ExtractedPlayer] = []
    competitions: list[ExtractedCompetition] = []
    article_type: Literal["injury", "transfer", "form", "preview", "general"] = "general"
    language: Literal["en", "fr"] = "en"


# =============================================================================
# Prompts
# =============================================================================

ENTITY_EXTRACTION_BATCH_PROMPT = (
    "You are a football NER (Named Entity Recognition) system.\n"
    "Extract entities from the following football news articles.\n\n"
    "For each article, extract:\n"
    "- teams: name, role (subject/opponent/mentioned), confidence\n"
    "- players: name, team (if known), context "
    "(injury/transfer/performance/suspension/return/general), "
    "confidence (0-1)\n"
    "- competitions: name, canonical_code "
    "(PL/PD/BL1/SA/FL1/CL/EL or null), confidence (0-1)\n"
    "- article_type: injury/transfer/form/preview/general\n"
    "- language: en/fr\n\n"
    "Known competition codes: PL (Premier League), PD (La Liga), "
    "BL1 (Bundesliga), SA (Serie A), FL1 (Ligue 1), "
    "CL (Champions League), EL (Europa League)\n\n"
    "Common aliases:\n"
    "- UCL/C1/Ligue des Champions -> CL\n"
    "- Prem/EPL -> PL\n"
    "- Liga/LaLiga -> PD\n"
    "- Calcio -> SA\n"
    "- L1 -> FL1\n\n"
    'Respond with a JSON object: {{"articles": [...]}}\n'
    "Each ArticleEntities has: teams, players, competitions, "
    "article_type, language.\n\n"
    "ARTICLES:\n{articles_text}"
)

ENTITY_EXTRACTION_DEEP_PROMPT = (
    "You are an expert football NER system performing "
    "deep entity extraction.\n"
    "Extract ALL entities from this article with high precision.\n\n"
    "Known teams in context: {known_teams}\n\n"
    "For teams: extract name, try to match to a canonical name "
    "from the known teams list, assign role "
    "(subject=main team, opponent=their opponent, "
    "mentioned=just referenced).\n"
    "For players: extract full name, associate with team if "
    "possible, classify context "
    "(injury/transfer/performance/suspension/return/general).\n"
    "For competitions: extract name, map to canonical code "
    "(PL/PD/BL1/SA/FL1/CL/EL).\n\n"
    "Common competition aliases:\n"
    "- UCL/C1/Ligue des Champions/Champions League -> CL\n"
    "- Prem/EPL/Premier League -> PL\n"
    "- Liga/LaLiga/La Liga -> PD\n"
    "- Calcio/Serie A -> SA\n"
    "- L1/Ligue 1 -> FL1\n"
    "- Europa League/C3 -> EL\n\n"
    'Respond with JSON: {{"teams": [...], "players": [...], '
    '"competitions": [...], "article_type": "...", '
    '"language": "..."}}\n\n'
    "TITLE: {title}\nCONTENT: {content}"
)


# =============================================================================
# Competition alias mapping (for regex fallback)
# =============================================================================

COMPETITION_ALIASES: dict[str, str] = {
    # Premier League
    "premier league": "PL",
    "prem": "PL",
    "epl": "PL",
    "pl": "PL",
    # La Liga
    "la liga": "PD",
    "laliga": "PD",
    "liga": "PD",
    # Bundesliga
    "bundesliga": "BL1",
    # Serie A
    "serie a": "SA",
    "calcio": "SA",
    # Ligue 1
    "ligue 1": "FL1",
    "l1": "FL1",
    # Champions League
    "champions league": "CL",
    "ligue des champions": "CL",
    "ucl": "CL",
    "c1": "CL",
    # Europa League
    "europa league": "EL",
    "c3": "EL",
}


# =============================================================================
# Service
# =============================================================================


class EntityExtractionService:
    """LLM-based entity extraction service with regex fallback.

    Uses Groq LLM for extraction:
    - 8B model for batch extraction (news ingestion)
    - 70B model for deep extraction (RAG enrichment)
    - Regex fallback when LLM is unavailable
    """

    BATCH_SIZE = 5
    CACHE_TTL_BATCH = 21600  # 6 hours
    CACHE_TTL_DEEP = 43200  # 12 hours
    CACHE_TTL_FALLBACK = 3600  # 1 hour

    def __init__(self) -> None:
        self.llm_client: GroqClient | None = None
        try:
            self.llm_client = get_llm_client()
        except Exception as e:
            logger.warning(f"LLM client not available for NER: {e}")

    async def batch_extract(
        self,
        articles: list[dict[str, str]],
    ) -> list[ArticleEntities]:
        """Extract entities from multiple articles using 8B model.

        Args:
            articles: List of dicts with 'title' and optionally 'content' keys.

        Returns:
            List of ArticleEntities, one per article (same order).
        """
        if not articles:
            return []

        results: list[ArticleEntities] = []

        # Process in batches of BATCH_SIZE
        for i in range(0, len(articles), self.BATCH_SIZE):
            batch = articles[i : i + self.BATCH_SIZE]
            batch_results = await self._extract_batch(batch)
            results.extend(batch_results)

        return results

    async def _extract_batch(
        self,
        batch: list[dict[str, str]],
    ) -> list[ArticleEntities]:
        """Extract entities from a single batch of articles."""
        # Check cache for each article
        cached_results: dict[int, ArticleEntities] = {}
        uncached_indices: list[int] = []

        for idx, article in enumerate(batch):
            cache_key = self._cache_key("batch", article)
            cached = await cache_get(cache_key)
            if cached:
                try:
                    cached_results[idx] = ArticleEntities.model_validate_json(cached)
                    continue
                except Exception:
                    pass
            uncached_indices.append(idx)

        # All cached
        if not uncached_indices:
            return [cached_results[i] for i in range(len(batch))]

        # Build LLM request for uncached articles
        uncached_articles = [batch[i] for i in uncached_indices]
        llm_results = await self._llm_batch_extract(uncached_articles)

        # Cache new results
        for idx_offset, result in enumerate(llm_results):
            original_idx = uncached_indices[idx_offset]
            cached_results[original_idx] = result
            cache_key = self._cache_key("batch", batch[original_idx])
            ttl = self.CACHE_TTL_BATCH if self.llm_client else self.CACHE_TTL_FALLBACK
            await cache_set(cache_key, result.model_dump_json(), ttl)

        return [cached_results[i] for i in range(len(batch))]

    async def _llm_batch_extract(
        self,
        articles: list[dict[str, str]],
    ) -> list[ArticleEntities]:
        """Call LLM for batch extraction, fallback to regex on failure."""
        if not self.llm_client:
            return [
                self._regex_fallback(a.get("title", ""), a.get("content", "")) for a in articles
            ]

        try:
            # Format articles for prompt
            articles_text = ""
            for idx, article in enumerate(articles):
                title = article.get("title", "")
                content = article.get("content", "")[:200]
                articles_text += f"\n--- Article {idx + 1} ---\nTitle: {title}\n"
                if content:
                    articles_text += f"Content: {content}\n"

            prompt = ENTITY_EXTRACTION_BATCH_PROMPT.format(articles_text=articles_text)

            response = await self.llm_client.analyze_json(
                prompt=prompt,
                model=GroqClient.MODEL_SMALL,
                temperature=0.1,
            )

            return self._parse_batch_response(response, len(articles))

        except Exception as e:
            logger.warning(f"LLM batch NER failed, using regex fallback: {e}")
            return [
                self._regex_fallback(a.get("title", ""), a.get("content", "")) for a in articles
            ]

    def _parse_batch_response(
        self,
        response: dict[str, Any],
        expected_count: int,
    ) -> list[ArticleEntities]:
        """Parse and validate LLM batch response."""
        results: list[ArticleEntities] = []
        raw_articles = response.get("articles", [])

        for i in range(expected_count):
            if i < len(raw_articles):
                try:
                    results.append(ArticleEntities.model_validate(raw_articles[i]))
                except Exception as e:
                    logger.debug(f"Failed to parse article {i} NER response: {e}")
                    results.append(ArticleEntities())
            else:
                results.append(ArticleEntities())

        return results

    async def deep_extract(
        self,
        title: str,
        content: str,
        known_teams: list[str] | None = None,
    ) -> ArticleEntities:
        """Deep entity extraction using 70B model for a single article.

        Args:
            title: Article title.
            content: Article content.
            known_teams: List of known team names for context.

        Returns:
            ArticleEntities with high-precision extraction.
        """
        # Check cache
        cache_key = self._cache_key("deep", {"title": title, "content": content[:200]})
        cached = await cache_get(cache_key)
        if cached:
            try:
                return ArticleEntities.model_validate_json(cached)
            except Exception:
                pass

        result = await self._llm_deep_extract(title, content, known_teams or [])

        # Cache result
        ttl = self.CACHE_TTL_DEEP if self.llm_client else self.CACHE_TTL_FALLBACK
        await cache_set(cache_key, result.model_dump_json(), ttl)

        return result

    async def _llm_deep_extract(
        self,
        title: str,
        content: str,
        known_teams: list[str],
    ) -> ArticleEntities:
        """Call 70B LLM for deep extraction, fallback to regex."""
        if not self.llm_client:
            return self._regex_fallback(title, content)

        try:
            prompt = ENTITY_EXTRACTION_DEEP_PROMPT.format(
                known_teams=", ".join(known_teams) if known_teams else "none",
                title=title,
                content=content[:500] if content else "(no content)",
            )

            response = await self.llm_client.analyze_json(
                prompt=prompt,
                model=GroqClient.MODEL_LARGE,
                temperature=0.1,
            )

            return ArticleEntities.model_validate(response)

        except Exception as e:
            logger.warning(f"LLM deep NER failed, using regex fallback: {e}")
            return self._regex_fallback(title, content)

    def _regex_fallback(self, title: str, content: str) -> ArticleEntities:
        """Regex-based entity extraction fallback.

        Uses existing InjuryParser patterns + keyword detection.
        """
        text = f"{title} {content}".lower()
        full_text = f"{title} {content}"

        # Detect article type
        article_type = self._detect_article_type(text)

        # Detect language
        language = self._detect_language(text)

        # Extract players via capitalization patterns
        players = self._extract_players_regex(full_text, article_type)

        # Extract competitions
        competitions = self._extract_competitions_regex(text)

        # Extract teams (basic: look for known patterns)
        teams = self._extract_teams_regex(full_text)

        return ArticleEntities(
            teams=teams,
            players=players,
            competitions=competitions,
            article_type=article_type,
            language=language,
        )

    def _detect_article_type(
        self,
        text_lower: str,
    ) -> Literal["injury", "transfer", "form", "preview", "general"]:
        """Detect article type from lowercase text."""
        injury_kw = [
            "injury",
            "injured",
            "blessure",
            "blessé",
            "ruled out",
            "sidelined",
            "surgery",
            "opération",
            "forfait",
            "suspendu",
            "suspended",
            "hamstring",
            "knee",
            "ankle",
            "acl",
        ]
        if any(kw in text_lower for kw in injury_kw):
            return "injury"

        transfer_kw = [
            "transfer",
            "signing",
            "mercato",
            "transfert",
            "deal",
            "bid",
            "target",
            "linked",
            "loan",
            "prêt",
        ]
        if any(kw in text_lower for kw in transfer_kw):
            return "transfer"

        form_kw = [
            "win",
            "victory",
            "defeat",
            "loss",
            "draw",
            "victoire",
            "défaite",
            "streak",
            "unbeaten",
            "form",
        ]
        if any(kw in text_lower for kw in form_kw):
            return "form"

        preview_kw = [
            "preview",
            "avant-match",
            "pronostic",
            "prediction",
            "clash",
            "showdown",
        ]
        if any(kw in text_lower for kw in preview_kw):
            return "preview"

        return "general"

    def _detect_language(self, text_lower: str) -> Literal["en", "fr"]:
        """Simple language detection based on keywords."""
        fr_indicators = [
            "le ",
            "la ",
            "les ",
            "du ",
            "des ",
            "un ",
            "une ",
            "est ",
            "sont ",
            "dans ",
            "pour ",
            "avec ",
            "sur ",
            "blessure",
            "transfert",
            "victoire",
            "défaite",
            "match nul",
        ]
        en_indicators = [
            "the ",
            "is ",
            "are ",
            "in ",
            "for ",
            "with ",
            "injury",
            "transfer",
            "victory",
            "defeat",
            "draw",
        ]

        fr_count = sum(1 for kw in fr_indicators if kw in text_lower)
        en_count = sum(1 for kw in en_indicators if kw in text_lower)

        return "fr" if fr_count > en_count else "en"

    def _extract_players_regex(
        self,
        text: str,
        article_type: str,
    ) -> list[ExtractedPlayer]:
        """Extract player names using capitalization patterns."""
        players: list[ExtractedPlayer] = []
        seen_names: set[str] = set()

        # Pattern: Two or three capitalized words (player name pattern)
        pattern = r"\b([A-Z][a-zéèêëàâäôöùûüïîç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüïîç]+){1,2})\b"
        matches = re.findall(pattern, text)

        # Filter out common non-player words
        exclude = {
            "Premier League",
            "Champions League",
            "Europa League",
            "Serie A",
            "La Liga",
            "Ligue 1",
            "Bundesliga",
            "Manchester City",
            "Manchester United",
            "Real Madrid",
            "Atletico Madrid",
            "Aston Villa",
            "Crystal Palace",
            "West Ham",
            "Nottingham Forest",
            "Borussia Dortmund",
            "Bayer Leverkusen",
            "Eintracht Frankfurt",
            "Bayern Munich",
            "Union Berlin",
            "Real Betis",
            "Real Sociedad",
            "Athletic Club",
            "Paris Saint",
            "Google News",
            "Red Card",
            "Yellow Card",
        }

        # Map article_type to player context
        context_map: dict[
            str, Literal["injury", "transfer", "performance", "suspension", "return", "general"]
        ] = {
            "injury": "injury",
            "transfer": "transfer",
            "form": "performance",
        }
        player_context = context_map.get(article_type, "general")

        # Also exclude any match with a known team/competition name
        team_names_lower = {t.lower() for t in self._known_team_names()}
        comp_words = {
            "league",
            "champions",
            "europa",
            "premier",
            "ligue",
            "bundesliga",
            "serie",
            "copa",
            "coupe",
            "cup",
        }

        for name in matches:
            if name in exclude or name in seen_names:
                continue
            name_lower = name.lower()
            # Skip if name contains a known team name
            if any(tn in name_lower for tn in team_names_lower if len(tn) > 3):
                continue
            # Skip if any word is a competition keyword
            name_words = {w.lower() for w in name.split()}
            if name_words & comp_words:
                continue
            # Must be 2+ words and reasonable length
            if len(name.split()) >= 2 and 5 < len(name) < 40:
                seen_names.add(name)
                players.append(
                    ExtractedPlayer(
                        name=name,
                        context=player_context,
                        confidence=0.4,
                    )
                )

        return players[:5]  # Limit to 5 players

    def _extract_competitions_regex(
        self,
        text_lower: str,
    ) -> list[ExtractedCompetition]:
        """Extract competition references from text."""
        competitions: list[ExtractedCompetition] = []
        seen_codes: set[str] = set()

        for alias, code in COMPETITION_ALIASES.items():
            if alias in text_lower and code not in seen_codes:
                seen_codes.add(code)
                competitions.append(
                    ExtractedCompetition(
                        name=alias,
                        canonical_code=code,
                        confidence=0.7,
                    )
                )

        return competitions

    @staticmethod
    def _known_team_names() -> list[str]:
        """Return list of known team names for matching."""
        return [
            "Arsenal",
            "Chelsea",
            "Manchester United",
            "Manchester City",
            "Liverpool",
            "Tottenham",
            "Newcastle",
            "Aston Villa",
            "Brighton",
            "West Ham",
            "Fulham",
            "Crystal Palace",
            "Brentford",
            "Everton",
            "Nottingham Forest",
            "Bournemouth",
            "Wolves",
            "Leicester",
            "Real Madrid",
            "Barcelona",
            "Atletico Madrid",
            "Sevilla",
            "Valencia",
            "Villarreal",
            "Juventus",
            "AC Milan",
            "Inter",
            "Napoli",
            "AS Roma",
            "Lazio",
            "Fiorentina",
            "Atalanta",
            "Bayern Munich",
            "Borussia Dortmund",
            "RB Leipzig",
            "Bayer Leverkusen",
            "PSG",
            "Paris Saint-Germain",
            "Marseille",
            "Lyon",
            "Monaco",
            "Lille",
            "Nice",
            "Lens",
            "Rennes",
        ]

    def _extract_teams_regex(self, text: str) -> list[ExtractedTeam]:
        """Extract team names from text using known team names."""
        teams: list[ExtractedTeam] = []
        seen_names: set[str] = set()

        for team_name in self._known_team_names():
            if team_name.lower() in text.lower() and team_name not in seen_names:
                seen_names.add(team_name)
                teams.append(
                    ExtractedTeam(
                        name=team_name,
                        canonical_name=team_name,
                        role="mentioned",
                        confidence=0.8,
                    )
                )

        # First team found is likely the subject
        if teams:
            teams[0].role = "subject"
            if len(teams) > 1:
                teams[1].role = "opponent"

        return teams

    @staticmethod
    def _cache_key(prefix: str, article: dict[str, str]) -> str:
        """Generate Redis cache key for an article."""
        title = article.get("title", "")
        content = article.get("content", "")[:200]
        raw = f"{title}|{content}"
        md5 = hashlib.md5(raw.encode()).hexdigest()
        return f"ner:{prefix}:{md5}"


# =============================================================================
# Singleton
# =============================================================================

_ner_service: EntityExtractionService | None = None


def get_entity_extraction_service() -> EntityExtractionService:
    """Get or create the NER service singleton."""
    global _ner_service
    if _ner_service is None:
        _ner_service = EntityExtractionService()
    return _ner_service
