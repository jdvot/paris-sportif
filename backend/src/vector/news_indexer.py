"""News article indexer for semantic search.

Indexes news articles from various sources into Qdrant
for semantic retrieval in the RAG pipeline.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.vector.embeddings import embed_text, embed_texts
from src.vector.qdrant_store import COLLECTION_NEWS, QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article to be indexed."""

    title: str
    content: str | None = None
    url: str | None = None
    source: str = "unknown"
    published_at: datetime | None = None
    team_name: str | None = None
    team_id: int | None = None
    competition: str | None = None
    article_type: str = "general"  # general, injury, transfer, form, preview
    language: str = "en"


class NewsIndexer:
    """Index news articles for semantic search."""

    def __init__(self):
        self.store = QdrantStore(COLLECTION_NEWS)

    def _generate_id(self, article: NewsArticle) -> str:
        """Generate unique ID for article."""
        # Use URL hash if available, otherwise hash title + team
        if article.url:
            return hashlib.md5(article.url.encode()).hexdigest()

        content = f"{article.title}|{article.team_name}|{article.published_at}"
        return hashlib.md5(content.encode()).hexdigest()

    def _prepare_text(self, article: NewsArticle) -> str:
        """Prepare text for embedding.

        Combines title and content with team context for better retrieval.
        """
        parts = []

        # Add team context
        if article.team_name:
            parts.append(f"Team: {article.team_name}")

        # Add competition context
        if article.competition:
            parts.append(f"Competition: {article.competition}")

        # Add title (most important)
        parts.append(article.title)

        # Add content snippet if available
        if article.content:
            # Limit content to first 500 chars
            content = article.content[:500].strip()
            if content:
                parts.append(content)

        return " | ".join(parts)

    def _classify_article(self, title: str, content: str | None = None) -> str:
        """Classify article type based on content."""
        text = f"{title} {content or ''}".lower()

        # Injury patterns
        injury_patterns = [
            r"injur",
            r"bless",
            r"out for",
            r"sidelined",
            r"ruled out",
            r"hamstring",
            r"knee",
            r"ankle",
            r"muscle",
            r"surgery",
            r"recovery",
            r"return from",
            r"fitness doubt",
        ]
        if any(re.search(p, text) for p in injury_patterns):
            return "injury"

        # Transfer patterns
        transfer_patterns = [
            r"transfer",
            r"sign",
            r"deal",
            r"contract",
            r"loan",
            r"join",
            r"move to",
            r"bid",
            r"offer",
            r"fee",
        ]
        if any(re.search(p, text) for p in transfer_patterns):
            return "transfer"

        # Form/performance patterns
        form_patterns = [
            r"form",
            r"streak",
            r"winning",
            r"losing",
            r"unbeaten",
            r"goals? in",
            r"assists?",
            r"performance",
            r"impressive",
        ]
        if any(re.search(p, text) for p in form_patterns):
            return "form"

        # Match preview patterns
        preview_patterns = [
            r"preview",
            r"prediction",
            r"expect",
            r"key battle",
            r"head.to.head",
            r"h2h",
            r"clash",
            r"showdown",
        ]
        if any(re.search(p, text) for p in preview_patterns):
            return "preview"

        return "general"

    def index_article(self, article: NewsArticle) -> bool:
        """Index a single news article.

        Args:
            article: NewsArticle to index

        Returns:
            True if successful
        """
        try:
            # Generate ID
            article_id = self._generate_id(article)

            # Prepare text and generate embedding
            text = self._prepare_text(article)
            embedding = embed_text(text)

            # Auto-classify if not specified
            if article.article_type == "general":
                article.article_type = self._classify_article(article.title, article.content)

            # Prepare payload
            payload = {
                "title": article.title,
                "content_snippet": (article.content or "")[:200],
                "url": article.url,
                "source": article.source,
                "team_name": article.team_name,
                "team_id": article.team_id,
                "competition": article.competition,
                "article_type": article.article_type,
                "language": article.language,
                "published_at": article.published_at.isoformat() if article.published_at else None,
            }

            # Upsert to Qdrant
            success = self.store.upsert(article_id, embedding, payload)

            if success:
                logger.debug(f"Indexed article: {article.title[:50]}...")

            return success

        except Exception as e:
            logger.error(f"Failed to index article '{article.title[:50]}': {e}")
            return False

    def index_articles(self, articles: list[NewsArticle]) -> int:
        """Index multiple articles (batch processing).

        Args:
            articles: List of NewsArticle to index

        Returns:
            Number of successfully indexed articles
        """
        if not articles:
            return 0

        logger.info(f"Indexing {len(articles)} articles...")

        # Prepare all data
        ids = []
        texts = []
        payloads = []

        for article in articles:
            article_id = self._generate_id(article)
            text = self._prepare_text(article)

            # Auto-classify
            if article.article_type == "general":
                article.article_type = self._classify_article(article.title, article.content)

            ids.append(article_id)
            texts.append(text)
            payloads.append(
                {
                    "title": article.title,
                    "content_snippet": (article.content or "")[:200],
                    "url": article.url,
                    "source": article.source,
                    "team_name": article.team_name,
                    "team_id": article.team_id,
                    "competition": article.competition,
                    "article_type": article.article_type,
                    "language": article.language,
                    "published_at": (
                        article.published_at.isoformat() if article.published_at else None
                    ),
                }
            )

        # Batch embed
        embeddings = embed_texts(texts)

        # Batch upsert
        count = self.store.upsert_batch(ids, embeddings, payloads)

        logger.info(f"Indexed {count}/{len(articles)} articles")
        return count

    def search_news(
        self,
        query: str,
        team_name: str | None = None,
        article_type: str | None = None,
        limit: int = 5,
        min_score: float = 0.5,
        max_age_days: int | None = 7,
    ) -> list[dict[str, Any]]:
        """Search for relevant news articles.

        Args:
            query: Search query (e.g., "key player injury before match")
            team_name: Filter by team name
            article_type: Filter by type (injury, transfer, form, etc.)
            limit: Max results
            min_score: Minimum similarity score
            max_age_days: Only return articles from last N days

        Returns:
            List of matching articles with scores
        """
        # Generate query embedding
        query_embedding = embed_text(query)

        # Build filters
        filters = {}
        if team_name:
            filters["team_name"] = team_name
        if article_type:
            filters["article_type"] = article_type

        # Search
        results = self.store.search(
            query_embedding=query_embedding,
            limit=limit * 2 if max_age_days else limit,  # Over-fetch for date filtering
            score_threshold=min_score,
            filter_conditions=filters if filters else None,
        )

        # Post-filter by date if needed
        if max_age_days:
            cutoff = datetime.utcnow() - timedelta(days=max_age_days)
            filtered_results = []
            for r in results:
                pub_date = r.payload.get("published_at")
                if pub_date:
                    try:
                        pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        if pub_dt.replace(tzinfo=None) >= cutoff:
                            filtered_results.append(r)
                    except ValueError:
                        filtered_results.append(r)  # Keep if date parsing fails
                else:
                    filtered_results.append(r)  # Keep if no date

            results = filtered_results[:limit]
        else:
            results = results[:limit]

        return [
            {
                "id": r.id,
                "score": r.score,
                "title": r.payload.get("title"),
                "content": r.payload.get("content_snippet"),
                "url": r.payload.get("url"),
                "source": r.payload.get("source"),
                "team_name": r.payload.get("team_name"),
                "article_type": r.payload.get("article_type"),
                "published_at": r.payload.get("published_at"),
            }
            for r in results
        ]

    def get_team_context(
        self,
        team_name: str,
        context_query: str = "recent news injuries form",
        limit: int = 5,
    ) -> dict[str, Any]:
        """Get comprehensive context for a team.

        Args:
            team_name: Team name to search for
            context_query: Additional context for search
            limit: Max articles per category

        Returns:
            Dict with categorized news
        """
        query = f"{team_name} {context_query}"
        all_news = self.search_news(
            query=query,
            team_name=team_name,
            limit=limit * 3,
            min_score=0.4,
            max_age_days=14,
        )

        # Categorize results
        context = {
            "team_name": team_name,
            "injuries": [],
            "transfers": [],
            "form": [],
            "general": [],
            "total_articles": len(all_news),
        }

        for article in all_news:
            article_type = article.get("article_type", "general")
            if article_type == "injury" and len(context["injuries"]) < limit:
                context["injuries"].append(article)
            elif article_type == "transfer" and len(context["transfers"]) < limit:
                context["transfers"].append(article)
            elif article_type == "form" and len(context["form"]) < limit:
                context["form"].append(article)
            elif len(context["general"]) < limit:
                context["general"].append(article)

        return context

    def get_stats(self) -> dict[str, Any]:
        """Get indexer statistics."""
        return {
            "collection": COLLECTION_NEWS,
            "total_vectors": self.store.count(),
        }
