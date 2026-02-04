"""Vector search module using Qdrant and sentence-transformers.

This module provides semantic search capabilities for:
- News articles (injuries, transfers, team news)
- Historical match patterns
- LLM analysis caching
"""

from src.vector.embeddings import embed_text, embed_texts, get_embedding_model
from src.vector.news_indexer import NewsArticle, NewsIndexer
from src.vector.news_ingestion import NewsIngestionService, get_ingestion_service
from src.vector.qdrant_store import QdrantStore, get_qdrant_client
from src.vector.search import SemanticSearch, enrich_with_semantic_search

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
