"""Vector search module using Qdrant and sentence-transformers.

This module provides semantic search capabilities for:
- News articles (injuries, transfers, team news)
- Historical match patterns
- LLM analysis caching
"""

from src.vector.embeddings import get_embedding_model, embed_text, embed_texts
from src.vector.qdrant_store import get_qdrant_client, QdrantStore
from src.vector.news_indexer import NewsIndexer, NewsArticle
from src.vector.search import SemanticSearch, enrich_with_semantic_search
from src.vector.news_ingestion import NewsIngestionService, get_ingestion_service

__all__ = [
    "get_embedding_model",
    "embed_text",
    "embed_texts",
    "get_qdrant_client",
    "QdrantStore",
    "NewsIndexer",
    "NewsArticle",
    "SemanticSearch",
    "enrich_with_semantic_search",
    "NewsIngestionService",
    "get_ingestion_service",
]
