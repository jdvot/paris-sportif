"""Client for TennisApi via RapidAPI (by REcodeX).

Free tier: 50 requests/day, 4 req/sec
API: https://rapidapi.com/fluis.lacasse/api/tennisapi1
Host: tennisapi1.p.rapidapi.com

Endpoints used:
  GET /api/tennis/calendar/month/{year}/{month}  → Calendar with events
  GET /api/tennis/tournament/{id}/events/...     → Tournament events
  GET /api/tennis/ranking/{type}/{page}          → ATP/WTA rankings
  GET /api/tennis/event/{id}                     → Event details
  GET /api/tennis/daily-categories/{day}/{month}/{year} → Daily schedule
"""

import asyncio
import logging
import time
from typing import Any

from src.core.config import settings
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

BASE_URL = "https://tennisapi1.p.rapidapi.com"
API_HOST = "tennisapi1.p.rapidapi.com"

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour
_MAX_CACHE_ENTRIES = 200

# Rate limiting: 50 req/day on free tier → 1 req per 3 seconds for safety
_last_request_time: float = 0
_MIN_INTERVAL = 3.0  # seconds


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
    """Make an authenticated request to TennisApi.

    Returns the full JSON response dict.
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


async def get_daily_matches(day: int, month: int, year: int) -> list[dict[str, Any]]:
    """Get daily tennis schedule/categories with events.

    Args:
        day: Day of month (1-31)
        month: Month (1-12)
        year: Year (e.g., 2026)

    Returns:
        List of category dicts containing events.
    """
    data = await _request(f"/api/tennis/daily-categories/{day}/{month}/{year}")
    categories: list[dict[str, Any]] = data.get("categories", [])
    total_events = sum(len(c.get("events", [])) for c in categories)
    logger.info(f"Tennis API: {total_events} events for {year}-{month:02d}-{day:02d}")
    return categories


async def get_rankings(ranking_type: str = "atp", page: int = 1) -> list[dict[str, Any]]:
    """Get tennis rankings.

    Args:
        ranking_type: "atp" or "wta"
        page: Page number (1-indexed)

    Returns:
        List of ranking entry dicts.
    """
    data = await _request(f"/api/tennis/ranking/{ranking_type}/{page}")
    rankings: list[dict[str, Any]] = data.get("rankings", [])
    logger.info(f"Tennis API: {len(rankings)} {ranking_type.upper()} rankings (page {page})")
    return rankings


async def get_event_details(event_id: int) -> dict[str, Any]:
    """Get details for a specific event/match.

    Args:
        event_id: Event ID from the API

    Returns:
        Event detail dict.
    """
    data = await _request(f"/api/tennis/event/{event_id}")
    return data.get("event", {})


async def get_tournaments() -> list[dict[str, Any]]:
    """Get current month's tournaments from the calendar.

    Returns:
        List of tournament/category dicts from the monthly calendar.
    """
    from datetime import date

    today = date.today()
    data = await _request(f"/api/tennis/calendar/month/{today.year}/{today.month}")
    tournaments: list[dict[str, Any]] = data.get("tournaments", data.get("categories", []))
    logger.info(f"Tennis API: {len(tournaments)} tournaments for {today.year}-{today.month:02d}")
    return tournaments
