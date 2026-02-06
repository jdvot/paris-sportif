"""Qdrant vector store client.

Handles connection to Qdrant Cloud and collection management.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from src.core.config import settings
from src.vector.embeddings import EMBEDDING_DIM

logger = logging.getLogger(__name__)

# Collection names
COLLECTION_NEWS = "news_embeddings"
COLLECTION_MATCHES = "match_embeddings"
COLLECTION_LLM_CACHE = "llm_cache"

# Singleton client
_client: QdrantClient | None = None


@dataclass
class SearchResult:
    """Search result from Qdrant."""

    id: str
    score: float
    payload: dict[str, Any]


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client.

    Raises:
        RuntimeError: If QDRANT_URL is not configured
    """
    global _client

    if _client is None:
        qdrant_url = getattr(settings, "qdrant_url", None)
        qdrant_api_key = getattr(settings, "qdrant_api_key", None)

        if not qdrant_url:
            raise RuntimeError(
                "QDRANT_URL not configured. Qdrant Cloud is required for vector search."
            )

        if "cloud.qdrant.io" in qdrant_url:
            # Qdrant Cloud
            logger.info(f"Connecting to Qdrant Cloud: {qdrant_url}")
            _client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                timeout=30,
            )
        else:
            # Self-hosted Qdrant
            logger.info(f"Connecting to Qdrant: {qdrant_url}")
            _client = QdrantClient(url=qdrant_url, timeout=30)

    return _client


class QdrantStore:
    """High-level interface for Qdrant operations."""

    def __init__(self, collection_name: str = COLLECTION_NEWS):
        self.client = get_qdrant_client()
        self.collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Collection created: {self.collection_name}")

            # Ensure payload indexes exist for filterable fields
            self._ensure_payload_indexes()
        except Exception as e:
            logger.error(f"Failed to ensure collection {self.collection_name}: {e}")

    def _ensure_payload_indexes(self) -> None:
        """Create payload indexes for filterable fields."""
        # Fields that need keyword indexes for filtering
        keyword_fields = ["team_name", "competition", "source", "category", "match_id"]

        for field in keyword_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Created payload index for '{field}' in {self.collection_name}")
            except Exception as e:
                error_str = str(e).lower()
                # Index already exists - this is fine
                if "already exists" in error_str or "already indexed" in error_str:
                    logger.debug(f"Index for '{field}' already exists in {self.collection_name}")
                else:
                    logger.warning(
                        f"Failed to create index for '{field}' in {self.collection_name}: {e}"
                    )

    def upsert(
        self,
        id: str,
        embedding: list[float],
        payload: dict[str, Any],
    ) -> bool:
        """Insert or update a vector.

        Args:
            id: Unique identifier
            embedding: Vector embedding
            payload: Metadata to store

        Returns:
            True if successful
        """
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=id,
                        vector=embedding,
                        payload={
                            **payload,
                            "indexed_at": datetime.utcnow().isoformat(),
                        },
                    )
                ],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert {id}: {e}")
            return False

    def upsert_batch(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """Insert or update multiple vectors.

        Args:
            ids: List of unique identifiers
            embeddings: List of vector embeddings
            payloads: List of metadata dicts
            batch_size: Batch size for upsert

        Returns:
            Number of successfully upserted vectors
        """
        if len(ids) != len(embeddings) or len(ids) != len(payloads):
            raise ValueError("ids, embeddings, and payloads must have same length")

        total_upserted = 0
        indexed_at = datetime.utcnow().isoformat()

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]

            points = [
                PointStruct(
                    id=id_,
                    vector=emb,
                    payload={**payload, "indexed_at": indexed_at},
                )
                for id_, emb, payload in zip(batch_ids, batch_embeddings, batch_payloads)
            ]

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                total_upserted += len(points)
            except Exception as e:
                logger.error(f"Failed to upsert batch starting at {i}: {e}")

        return total_upserted

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        score_threshold: float = 0.5,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_embedding: Query vector
            limit: Maximum results to return
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional filter on payload fields

        Returns:
            List of SearchResult
        """
        try:
            # Build filter if provided
            qdrant_filter = None
            if filter_conditions:
                must_conditions = []
                for key, value in filter_conditions.items():
                    if isinstance(value, list):
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=value),
                            )
                        )
                    else:
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value),
                            )
                        )
                qdrant_filter = models.Filter(must=must_conditions)

            # qdrant-client 1.7+ uses query_points instead of search
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )

            return [
                SearchResult(
                    id=str(r.id),
                    score=r.score,
                    payload=r.payload or {},
                )
                for r in results.points
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete(self, ids: list[str]) -> bool:
        """Delete vectors by ID.

        Args:
            ids: List of IDs to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=ids),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False

    def count(self) -> int:
        """Get total number of vectors in collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0
