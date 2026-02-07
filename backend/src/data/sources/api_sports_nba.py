"""Client for API-Sports NBA API.

Free tier: 100 requests/day
Documentation: https://api-sports.io/documentation/nba/v2
"""

import asyncio
import logging
import time
from typing import Any

from src.core.config import settings
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

BASE_URL = "https://v2.nba.api-sports.io"

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour
_MAX_CACHE_ENTRIES = 200

# Rate limiting: 100 req/day → at most 1 req/sec for safety
_last_request_time: float = 0
_MIN_INTERVAL = 1.0  # seconds


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


async def _request(endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Make an authenticated request to API-Sports NBA."""
    if not settings.api_sports_api_key:
        logger.warning("API_SPORTS_API_KEY not configured, skipping NBA request")
        return {"response": []}

    cache_key = f"nba:{endpoint}:{params}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    await _throttle()

    client = get_http_client()
    url = f"{BASE_URL}{endpoint}"
    headers = {"x-apisports-key": settings.api_sports_api_key}

    try:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining:
            logger.debug(f"NBA API rate limit remaining: {remaining}")

        _set_cache(cache_key, data)
        return data

    except Exception as e:
        logger.error(f"NBA API request failed: {endpoint} - {e}")
        return {"response": []}


async def get_games(date_str: str) -> list[dict[str, Any]]:
    """Get NBA games for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of game dicts from API-Sports
    """
    data = await _request("/games", params={"date": date_str})
    result: list[dict[str, Any]] = data.get("response", [])
    logger.info(f"NBA API: {len(result)} games for {date_str}")
    return result


async def get_standings(league: str, season: str) -> list[dict[str, Any]]:
    """Get NBA standings.

    Args:
        league: League ID (e.g., "standard" for NBA)
        season: Season year (e.g., "2025")

    Returns:
        List of standings entries
    """
    data = await _request("/standings", params={"league": league, "season": season})
    result: list[dict[str, Any]] = data.get("response", [])
    logger.info(f"NBA API: {len(result)} standings entries for {league}/{season}")
    return result


async def get_teams(league: str = "standard", season: str = "2025") -> list[dict[str, Any]]:
    """Get NBA teams.

    Args:
        league: League type
        season: Season year

    Returns:
        List of team dicts
    """
    data = await _request("/teams", params={"league": league, "season": season})
    result: list[dict[str, Any]] = data.get("response", [])
    logger.info(f"NBA API: {len(result)} teams")
    return result
