"""Embedding generation using sentence-transformers.

Uses all-MiniLM-L6-v2 model:
- 384 dimensions
- Fast inference (CPU OK)
- Good multilingual support (FR/EN)
- Free and open source
"""

import logging
from functools import lru_cache
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# Model singleton
_model = None
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_embedding_model():
    """Get or initialize the embedding model (lazy loading)."""
    global _model

    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {MODEL_NAME}")
            _model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Embedding model loaded successfully (dim={EMBEDDING_DIM})")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    return _model


def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        List of floats (384 dimensions)
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * EMBEDDING_DIM

    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)

    # Normalize the embedding
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding.tolist()


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for multiple texts (batch processing).

    Args:
        texts: List of texts to embed
        batch_size: Batch size for processing

    Returns:
        List of embeddings (each 384 dimensions)
    """
    if not texts:
        return []

    # Filter empty texts and track indices
    non_empty_indices = []
    non_empty_texts = []
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_indices.append(i)
            non_empty_texts.append(text)

    # Initialize result with zero vectors
    results = [[0.0] * EMBEDDING_DIM for _ in range(len(texts))]

    if not non_empty_texts:
        return results

    model = get_embedding_model()

    # Batch encode
    embeddings = model.encode(
        non_empty_texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=len(non_empty_texts) > 100,
    )

    # Normalize and assign to results
    for idx, embedding in zip(non_empty_indices, embeddings):
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        results[idx] = embedding.tolist()

    return results


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding
        embedding2: Second embedding

    Returns:
        Similarity score (0 to 1, higher = more similar)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))
