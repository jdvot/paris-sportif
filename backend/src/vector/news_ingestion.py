"""News ingestion service for semantic search.

Fetches news from REAL RSS sources and indexes them in Qdrant
for the RAG pipeline.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote

import defusedxml.ElementTree as ET
import httpx

from src.vector.news_indexer import NewsArticle, NewsIndexer

logger = logging.getLogger(__name__)


class NewsIngestionService:
    """Fetch and index news from real RSS sources."""

    # RSS Feed sources by language/region (only verified working feeds)
    RSS_SOURCES = {
        # English sources - Major media
        "bbc_football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "bbc_premier_league": "https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml",
        "bbc_champions_league": "https://feeds.bbci.co.uk/sport/football/champions-league/rss.xml",
        "guardian_football": "https://www.theguardian.com/football/rss",
        "skysports": "https://www.skysports.com/rss/12040",
        "espn_football": "https://www.espn.com/espn/rss/soccer/news",
        "mirror_football": "https://www.mirror.co.uk/sport/football/rss.xml",
        "telegraph_football": "https://www.telegraph.co.uk/football/rss.xml",
        "independent_football": "https://www.independent.co.uk/sport/football/rss",
        # French sources - Major media
        "lequipe_football": "https://dwh.lequipe.fr/api/edito/rss?path=/Football/",
        "lequipe_transfers": "https://dwh.lequipe.fr/api/edito/rss?path=/Football/Transferts-football/",
        "rmcsport_football": "https://rmcsport.bfmtv.com/rss/football/",
        "footmercato": "https://www.footmercato.net/flux-rss",
        "sofoot": "https://www.sofoot.com/rss",
        # French sources - Maxifoot
        "maxifoot_general": "http://rss.maxifoot.com/football-general.xml",
        "maxifoot_transfer": "http://rss.maxifoot.com/football-transfert.xml",
        "maxifoot_ligue1": "http://rss.maxifoot.com/football-ligue1.xml",
        "maxifoot_champions": "http://rss.maxifoot.com/football-ligue-champion.xml",
        # League-specific from Maxifoot (for international coverage in French)
        "maxifoot_angleterre": "http://rss.maxifoot.com/football-angleterre.xml",
        "maxifoot_espagne": "http://rss.maxifoot.com/football-espagne.xml",
        "maxifoot_italie": "http://rss.maxifoot.com/football-italie.xml",
        "maxifoot_allemagne": "http://rss.maxifoot.com/football-allemagne.xml",
        # Club-specific from Maxifoot (French clubs)
        "maxifoot_psg": "http://rss.maxifoot.com/football-psg.xml",
        "maxifoot_om": "http://rss.maxifoot.com/football-om.xml",
        "maxifoot_ol": "http://rss.maxifoot.com/football-ol.xml",
    }

    # Sources that are in French (for language detection)
    FRENCH_SOURCES = {
        "lequipe_football", "lequipe_transfers", "rmcsport_football",
        "footmercato", "sofoot", "maxifoot_general", "maxifoot_transfer",
        "maxifoot_ligue1", "maxifoot_champions", "maxifoot_angleterre",
        "maxifoot_espagne", "maxifoot_italie", "maxifoot_allemagne",
        "maxifoot_psg", "maxifoot_om", "maxifoot_ol",
    }

    # Google News RSS template for team-specific searches
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang}"

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
        """Fetch real news for a team from Google News RSS.

        Uses Google News RSS which is free and requires no API key.
        """
        articles: list[NewsArticle] = []

        try:
            # Fetch from Google News RSS in multiple languages
            search_configs = [
                {"query": f"{team_name} football", "lang": "fr", "country": "FR"},
                {"query": f"{team_name} football", "lang": "en", "country": "GB"},
            ]

            async with httpx.AsyncClient(timeout=15.0) as client:
                for config in search_configs:
                    if len(articles) >= max_articles:
                        break

                    try:
                        encoded_query = quote(config["query"])
                        rss_url = self.GOOGLE_NEWS_RSS.format(
                            query=encoded_query,
                            lang=config["lang"],
                            country=config["country"],
                        )

                        response = await client.get(rss_url)
                        if response.status_code == 200:
                            parsed = self._parse_rss_feed(
                                response.text,
                                source=f"Google News ({config['lang'].upper()})",
                                team_name=team_name,
                            )
                            articles.extend(parsed)

                        # Rate limit
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Error fetching Google News for {team_name} ({config['lang']}): {e}")

            # Deduplicate by title
            seen_titles: set[str] = set()
            unique_articles: list[NewsArticle] = []
            for article in articles:
                title_lower = article.title.lower()[:50]
                if title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    unique_articles.append(article)

            logger.info(f"Fetched {len(unique_articles)} real news articles for {team_name}")
            return unique_articles[:max_articles]

        except Exception as e:
            logger.error(f"Error in fetch_team_news_from_api for {team_name}: {e}")
            return []

    async def fetch_general_football_news(self, max_per_source: int = 5) -> list[NewsArticle]:
        """Fetch general football news from major RSS sources."""
        all_articles: list[NewsArticle] = []

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for source_name, rss_url in self.RSS_SOURCES.items():
                try:
                    response = await client.get(rss_url)
                    if response.status_code == 200:
                        articles = self._parse_rss_feed(
                            response.text,
                            source=source_name,
                            team_name=None,
                        )
                        all_articles.extend(articles[:max_per_source])
                        logger.info(f"Fetched {len(articles[:max_per_source])} articles from {source_name}")

                    # Rate limit
                    await asyncio.sleep(0.5)

                except httpx.TimeoutException:
                    logger.warning(f"Timeout fetching RSS from {source_name}")
                except httpx.ConnectError:
                    logger.warning(f"Connection error for {source_name}")
                except Exception as e:
                    logger.warning(f"Error fetching RSS from {source_name}: {e}")

        logger.info(f"Total general news fetched: {len(all_articles)}")
        return all_articles

    def _parse_rss_feed(
        self,
        xml_content: str,
        source: str,
        team_name: str | None = None,
    ) -> list[NewsArticle]:
        """Parse RSS XML feed and return NewsArticle objects."""
        articles: list[NewsArticle] = []

        try:
            root = ET.fromstring(xml_content)

            # Handle both RSS 2.0 and Atom feeds
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                try:
                    # RSS 2.0 format
                    title_elem = item.find("title")
                    desc_elem = item.find("description")
                    pub_date_elem = item.find("pubDate")
                    link_elem = item.find("link")

                    # Atom format fallback
                    if title_elem is None:
                        title_elem = item.find("{http://www.w3.org/2005/Atom}title")
                    if desc_elem is None:
                        desc_elem = item.find("{http://www.w3.org/2005/Atom}summary")
                    if pub_date_elem is None:
                        pub_date_elem = item.find("{http://www.w3.org/2005/Atom}published")
                    if link_elem is None:
                        link_elem = item.find("{http://www.w3.org/2005/Atom}link")

                    if title_elem is not None and title_elem.text:
                        title = title_elem.text.strip()
                        content = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else None
                        url = None

                        # Get URL (handle Atom link with href attribute)
                        if link_elem is not None:
                            url = link_elem.get("href") or link_elem.text

                        # Parse publication date
                        published_at = datetime.utcnow()
                        if pub_date_elem is not None and pub_date_elem.text:
                            try:
                                # Try multiple date formats
                                for fmt in [
                                    "%a, %d %b %Y %H:%M:%S %z",
                                    "%a, %d %b %Y %H:%M:%S GMT",
                                    "%Y-%m-%dT%H:%M:%S%z",
                                    "%Y-%m-%dT%H:%M:%SZ",
                                ]:
                                    try:
                                        published_at = datetime.strptime(pub_date_elem.text.strip(), fmt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass

                        # Detect article type from content
                        article_type = self._detect_article_type(title, content or "")

                        # Detect language based on source
                        language = "en"  # default
                        if source in self.FRENCH_SOURCES:
                            language = "fr"
                        elif source.startswith("maxifoot") or source.startswith("lequipe") or source.startswith("rmcsport") or source.startswith("footmercato") or source.startswith("sofoot"):
                            language = "fr"
                        elif "(FR)" in source.upper():
                            language = "fr"

                        articles.append(
                            NewsArticle(
                                title=title,
                                content=content[:500] if content else None,
                                source=source,
                                url=url,
                                published_at=published_at,
                                team_name=team_name,
                                team_id=self.TEAM_IDS.get(team_name) if team_name else None,
                                article_type=article_type,
                                language=language,
                            )
                        )

                except Exception as e:
                    logger.debug(f"Error parsing RSS item: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"Error parsing RSS XML from {source}: {e}")

        return articles

    def _detect_article_type(self, title: str, content: str) -> str:
        """Detect the type of article based on keywords."""
        text = f"{title} {content}".lower()

        # Injury keywords
        injury_keywords = ["injury", "injured", "blessure", "blessé", "ruled out", "sidelined", "miss", "doubt"]
        if any(kw in text for kw in injury_keywords):
            return "injury"

        # Transfer keywords
        transfer_keywords = ["transfer", "signing", "sign", "deal", "bid", "target", "linked", "mercato", "transfert"]
        if any(kw in text for kw in transfer_keywords):
            return "transfer"

        # Form/result keywords
        form_keywords = ["win", "victory", "defeat", "loss", "draw", "result", "score", "victoire", "défaite"]
        if any(kw in text for kw in form_keywords):
            return "form"

        # Preview keywords
        preview_keywords = ["preview", "preview", "avant-match", "pronostic", "prediction"]
        if any(kw in text for kw in preview_keywords):
            return "preview"

        return "general"

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
                results.append(
                    {
                        "team": team,
                        "error": str(e),
                    }
                )

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
            ],
            "PD": [
                "Real Madrid",
                "Barcelona",
                "Atletico Madrid",
                "Sevilla",
                "Real Betis",
                "Valencia",
                "Villarreal",
                "Athletic Club",
                "Real Sociedad",
            ],
            "SA": [
                "Juventus",
                "AC Milan",
                "Inter",
                "Napoli",
                "AS Roma",
                "Lazio",
                "Fiorentina",
                "Atalanta",
            ],
            "BL1": [
                "Bayern Munich",
                "Borussia Dortmund",
                "RB Leipzig",
                "Bayer Leverkusen",
                "Eintracht Frankfurt",
                "Union Berlin",
                "Freiburg",
                "Wolfsburg",
            ],
            "FL1": [
                "PSG",
                "Marseille",
                "Lyon",
                "Monaco",
                "Lille",
                "Nice",
                "Lens",
                "Rennes",
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
                results.append(
                    {
                        "competition": comp_code,
                        "error": str(e),
                    }
                )

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
            "rss_sources": list(self.RSS_SOURCES.keys()),
        }

    async def fetch_injury_news(self, team_name: str, max_articles: int = 5) -> list[NewsArticle]:
        """Fetch injury-specific news for a team."""
        articles: list[NewsArticle] = []

        try:
            search_queries = [
                f"{team_name} injury injured",
                f"{team_name} blessure blessé",
                f"{team_name} ruled out doubtful",
            ]

            async with httpx.AsyncClient(timeout=15.0) as client:
                for query in search_queries:
                    if len(articles) >= max_articles:
                        break

                    try:
                        encoded_query = quote(query)
                        rss_url = self.GOOGLE_NEWS_RSS.format(
                            query=encoded_query,
                            lang="fr",
                            country="FR",
                        )

                        response = await client.get(rss_url)
                        if response.status_code == 200:
                            parsed = self._parse_rss_feed(
                                response.text,
                                source="Google News (Injury)",
                                team_name=team_name,
                            )
                            # Only keep injury-related articles
                            injury_articles = [a for a in parsed if a.article_type == "injury"]
                            articles.extend(injury_articles)

                        await asyncio.sleep(0.3)

                    except Exception as e:
                        logger.warning(f"Error fetching injury news for {team_name}: {e}")

            logger.info(f"Fetched {len(articles)} injury news for {team_name}")
            return articles[:max_articles]

        except Exception as e:
            logger.error(f"Error in fetch_injury_news for {team_name}: {e}")
            return []


# Singleton instance
_ingestion_service: NewsIngestionService | None = None


def get_ingestion_service() -> NewsIngestionService:
    """Get or create news ingestion service."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = NewsIngestionService()
    return _ingestion_service
