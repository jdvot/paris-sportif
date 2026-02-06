"""Shared httpx client for connection pooling.

Instead of creating a new httpx.AsyncClient per request, use the shared client
to benefit from TCP connection pooling, TLS session reuse, and reduced overhead.

Usage:
    from src.core.http_client import get_http_client

    client = get_http_client()
    response = await client.get("https://example.com")
"""

import logging

import httpx

logger = logging.getLogger(__name__)

# Shared client instance - initialized on first use or at startup
_client: httpx.AsyncClient | None = None


def get_http_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """Get the shared async HTTP client.

    Creates the client lazily on first call. The client is reused across
    all requests for connection pooling benefits.

    Args:
        timeout: Default timeout (only used on first creation)

    Returns:
        Shared httpx.AsyncClient instance
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=30,
            ),
            follow_redirects=True,
        )
        logger.info("Created shared HTTP client with connection pooling")
    return _client


async def close_http_client() -> None:
    """Close the shared HTTP client. Call during app shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
        logger.info("Closed shared HTTP client")
