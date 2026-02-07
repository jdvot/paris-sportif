"""Client for Tennis API (ATP/WTA/ITF) via RapidAPI.

Free tier: 300 requests/day
Documentation: https://rapidapi.com/jjrm365-kIFr3Nx_odV/api/tennis-api-atp-wta-itf
"""

import asyncio
import logging
import time
from typing import Any

from src.core.config import settings
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

BASE_URL = "https://tennis-api-atp-wta-itf.p.rapidapi.com"

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour
_MAX_CACHE_ENTRIES = 200

# Rate limiting: 300 req/day → 1 req per 2 seconds
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


async def _request(endpoint: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Make an authenticated request to SportDevs Tennis API."""
    if not settings.sportdevs_api_key:
        logger.warning("SPORTDEVS_API_KEY not configured, skipping Tennis request")
        return []

    cache_key = f"tennis:{endpoint}:{params}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    await _throttle()

    client = get_http_client()
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "x-rapidapi-key": settings.sportdevs_api_key,
        "x-rapidapi-host": "tennis-api-atp-wta-itf.p.rapidapi.com",
    }

    try:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()

        _set_cache(cache_key, data)
        return data

    except Exception as e:
        logger.error(f"Tennis API request failed: {endpoint} - {e}")
        return []


async def get_matches(date_str: str) -> list[dict[str, Any]]:
    """Get tennis matches for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of match dicts from SportDevs
    """
    result = await _request("/matches", params={"day_after": date_str})
    logger.info(f"Tennis API: {len(result)} matches for {date_str}")
    return result


async def get_players() -> list[dict[str, Any]]:
    """Get tennis players.

    Returns:
        List of player dicts
    """
    result = await _request("/players")
    logger.info(f"Tennis API: {len(result)} players")
    return result


async def get_tournaments() -> list[dict[str, Any]]:
    """Get tennis tournaments.

    Returns:
        List of tournament dicts
    """
    result = await _request("/tournaments")
    logger.info(f"Tennis API: {len(result)} tournaments")
    return result
