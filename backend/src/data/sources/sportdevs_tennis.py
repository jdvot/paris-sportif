"""Client for Tennis Live Data API via RapidAPI.

Free tier available on RapidAPI (sportcontentapi).
API: https://rapidapi.com/sportcontentapi/api/tennis-live-data
Host: tennis-live-data.p.rapidapi.com

Known endpoints:
  GET /rankings/ATP          → ATP rankings
  GET /rankings/WTA          → WTA rankings
  GET /matches-results/{date} → Match results for a date (YYYY-MM-DD)
  GET /matches/{date}        → Upcoming matches for a date (YYYY-MM-DD)
  GET /tournaments/{tour}    → Tournaments for a tour (ATP/WTA)
"""

import asyncio
import logging
import time
from typing import Any

from src.core.config import settings
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

BASE_URL = "https://tennis-live-data.p.rapidapi.com"
API_HOST = "tennis-live-data.p.rapidapi.com"

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour
_MAX_CACHE_ENTRIES = 200

# Rate limiting
_last_request_time: float = 0
_MIN_INTERVAL = 2.0  # seconds


async def _throttle() -> None:
    """Ensure minimum interval between API requests."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        await asyncio.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _get_cache(key: str) -> Any | None:
    """Get value from cache if not expired."""
    if key in _cache:
        ts, value = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: Any) -> None:
    """Set value in cache with TTL."""
    if len(_cache) >= _MAX_CACHE_ENTRIES:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]
    _cache[key] = (time.time(), value)


async def _request(endpoint: str) -> dict[str, Any]:
    """Make an authenticated request to Tennis Live Data API.

    Returns the full JSON response dict (typically has "meta" and "results" keys).
    """
    if not settings.sportdevs_api_key:
        logger.warning("SPORTDEVS_API_KEY not configured, skipping Tennis request")
        return {}

    cache_key = f"tennis:{endpoint}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    await _throttle()

    client = get_http_client()
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "x-rapidapi-key": settings.sportdevs_api_key,
        "x-rapidapi-host": API_HOST,
    }

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        _set_cache(cache_key, data)
        return data

    except Exception as e:
        logger.error(f"Tennis API request failed: {endpoint} - {e}")
        return {}


async def get_matches(date_str: str) -> list[dict[str, Any]]:
    """Get tennis matches for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of match dicts from Tennis Live Data API.
    """
    data = await _request(f"/matches-results/{date_str}")
    results: list[dict[str, Any]] = data.get("results", [])
    logger.info(f"Tennis API: {len(results)} matches for {date_str}")
    return results


async def get_upcoming_matches(date_str: str) -> list[dict[str, Any]]:
    """Get upcoming tennis matches for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of upcoming match dicts.
    """
    data = await _request(f"/matches/{date_str}")
    results: list[dict[str, Any]] = data.get("results", [])
    logger.info(f"Tennis API: {len(results)} upcoming matches for {date_str}")
    return results


async def get_rankings(tour: str = "ATP") -> list[dict[str, Any]]:
    """Get tennis rankings for a tour.

    Args:
        tour: Tour name ("ATP" or "WTA")

    Returns:
        List of player ranking dicts with keys like first_name, last_name, ranking, etc.
    """
    data = await _request(f"/rankings/{tour}")
    results_data = data.get("results", {})
    rankings: list[dict[str, Any]] = results_data.get("rankings", [])
    logger.info(f"Tennis API: {len(rankings)} {tour} rankings")
    return rankings


async def get_tournaments(tour: str = "ATP") -> list[dict[str, Any]]:
    """Get tennis tournaments for a tour.

    Args:
        tour: Tour name ("ATP" or "WTA")

    Returns:
        List of tournament dicts.
    """
    data = await _request(f"/tournaments/{tour}")
    results: list[dict[str, Any]] = data.get("results", [])
    logger.info(f"Tennis API: {len(results)} {tour} tournaments")
    return results
