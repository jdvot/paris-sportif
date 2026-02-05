"""Client for football-data.org API.

Free tier: 10 requests/minute
Documentation: https://www.football-data.org/documentation/api

INCLUDES CACHING to avoid rate limits.
Uses Redis for distributed caching when available, with in-memory fallback.
Also includes outgoing request throttling to prevent exceeding rate limits.
"""

import asyncio
import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import FootballDataAPIError, RateLimitError

logger = logging.getLogger(__name__)


# ============== OUTGOING RATE LIMITER ==============
class AsyncRateLimiter:
    """
    Async rate limiter using token bucket algorithm.
    Limits outgoing API requests to avoid hitting football-data.org rate limits.

    Free tier allows 10 requests/minute, so we limit to 8/minute for safety margin.
    """

    def __init__(self, requests_per_minute: int = 8):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0
        self._rate_limit_until: float = 0  # Timestamp when rate limit resets

    async def acquire(self) -> None:
        """Wait until we can make a request without exceeding rate limit."""
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # If we're in a rate limit period, wait for it to reset
            if self._rate_limit_until > now:
                wait_time = self._rate_limit_until - now
                logger.info(f"Rate limit active, waiting {wait_time:.1f}s for reset")
                await asyncio.sleep(wait_time)
                now = asyncio.get_event_loop().time()

            # Ensure minimum interval between requests
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"Throttling request, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    def set_rate_limit(self, reset_seconds: int) -> None:
        """Set rate limit lockout period based on API response."""
        now = asyncio.get_event_loop().time()
        self._rate_limit_until = now + reset_seconds
        logger.warning(f"Rate limit set for {reset_seconds}s (until {self._rate_limit_until})")


# Global rate limiter instance
_rate_limiter = AsyncRateLimiter(requests_per_minute=8)


# ============== CACHE SYSTEM ==============
class SimpleCache:
    """Simple in-memory cache with TTL (fallback when Redis unavailable)."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def _make_key(self, endpoint: str, params: dict[str, Any] | None) -> str:
        """Create a unique cache key."""
        param_str = json.dumps(params or {}, sort_keys=True)
        key = f"{endpoint}:{param_str}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any | None:
        """Get cached value if not expired."""
        key = self._make_key(endpoint, params)
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                logger.debug(f"Memory Cache HIT for {endpoint}")
                return value
            else:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Memory Cache EXPIRED for {endpoint}")
        return None

    def set(
        self, endpoint: str, params: dict[str, Any] | None, value: Any, ttl_seconds: int
    ) -> None:
        """Cache a value with TTL."""
        key = self._make_key(endpoint, params)
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[key] = (value, expires_at)
        logger.debug(f"Memory Cache SET for {endpoint} (TTL: {ttl_seconds}s)")

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Memory Cache CLEARED")


class RedisCache:
    """Redis-based cache for distributed caching across instances."""

    def __init__(self) -> None:
        self._fallback = SimpleCache()
        self._redis_available: bool | None = None

    def _make_key(self, endpoint: str, params: dict[str, Any] | None) -> str:
        """Create a unique cache key with namespace."""
        param_str = json.dumps(params or {}, sort_keys=True, default=str)
        key = f"{endpoint}:{param_str}"
        key_hash = hashlib.md5(key.encode()).hexdigest()[:16]
        return f"football_api:{key_hash}"

    async def _check_redis(self) -> bool:
        """Check if Redis is available."""
        if self._redis_available is not None:
            return self._redis_available
        try:
            from src.core.cache import health_check

            self._redis_available = await health_check()
            if self._redis_available:
                logger.info("Redis cache available - using distributed caching")
            else:
                logger.warning("Redis unavailable - falling back to in-memory cache")
        except Exception as e:
            logger.warning(f"Redis check failed: {e} - using in-memory cache")
            self._redis_available = False
        return self._redis_available

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any | None:
        """Get cached value from Redis or fallback."""
        if await self._check_redis():
            try:
                from src.core.cache import cache_get

                key = self._make_key(endpoint, params)
                cached = await cache_get(key)
                if cached:
                    logger.debug(f"Redis Cache HIT for {endpoint}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis GET failed: {e}")
        # Fallback to in-memory
        return self._fallback.get(endpoint, params)

    async def set(
        self, endpoint: str, params: dict[str, Any] | None, value: Any, ttl_seconds: int
    ) -> None:
        """Cache a value in Redis or fallback."""
        if await self._check_redis():
            try:
                from src.core.cache import cache_set

                key = self._make_key(endpoint, params)
                await cache_set(key, json.dumps(value, default=str), ttl_seconds)
                logger.debug(f"Redis Cache SET for {endpoint} (TTL: {ttl_seconds}s)")
                return
            except Exception as e:
                logger.warning(f"Redis SET failed: {e}")
        # Fallback to in-memory
        self._fallback.set(endpoint, params, value, ttl_seconds)

    def clear(self) -> None:
        """Clear fallback cache (Redis entries will expire naturally)."""
        self._fallback.clear()


# Global cache instance - uses Redis when available
_cache = RedisCache()
_sync_cache = SimpleCache()  # For sync operations only

# Cache TTLs (in seconds)
CACHE_TTL_MATCHES = 300  # 5 minutes for matches
CACHE_TTL_STANDINGS = 600  # 10 minutes for standings
CACHE_TTL_H2H = 1800  # 30 minutes for head-to-head
CACHE_TTL_TEAM = 900  # 15 minutes for team info
CACHE_TTL_TEAM_MATCHES = 300  # 5 minutes for team recent matches


class TeamData(BaseModel):
    """Team data from API."""

    id: int
    name: str
    shortName: str | None = None
    tla: str | None = None
    crest: str | None = None


class CompetitionData(BaseModel):
    """Competition data from API."""

    id: int
    name: str
    code: str
    emblem: str | None = None


class ScoreData(BaseModel):
    """Score data from API."""

    home: int | None = None
    away: int | None = None


class FullScoreData(BaseModel):
    """Full score data from API including all periods."""

    fullTime: ScoreData | None = None
    halfTime: ScoreData | None = None
    duration: str | None = None  # "REGULAR", "EXTRA_TIME", "PENALTY_SHOOTOUT"
    winner: str | None = None  # "HOME_TEAM", "AWAY_TEAM", "DRAW"


class MatchData(BaseModel):
    """Match data from API."""

    id: int
    competition: CompetitionData
    homeTeam: TeamData
    awayTeam: TeamData
    utcDate: str
    status: str
    matchday: int | None = None
    score: FullScoreData | None = None


class StandingTeam(BaseModel):
    """Team in standings."""

    position: int
    team: TeamData
    playedGames: int
    won: int
    draw: int
    lost: int
    points: int
    goalsFor: int
    goalsAgainst: int
    goalDifference: int


# Import centralized competition names
# Note: EL (Europa League) and ECL (Conference League) require paid tier
from src.core.constants import COMPETITION_NAMES as COMPETITIONS


class FootballDataClient:
    """Client for football-data.org API."""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.football_data_api_key
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}
        # Debug logging
        if self.api_key:
            key = self.api_key
            masked_key = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
            logger.info(f"FootballDataClient initialized with API key: {masked_key}")
        else:
            logger.warning("FootballDataClient initialized WITHOUT API key!")

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(RateLimitError),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make API request with rate limiting and retry logic."""
        url = f"{self.BASE_URL}{endpoint}"

        # Wait for rate limiter before making request
        await _rate_limiter.acquire()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                timeout=30.0,
            )

            if response.status_code == 429:
                # Parse rate limit reset time from headers
                reset_seconds = 60  # Default to 60 seconds
                if "x-requestcounter-reset" in response.headers:
                    try:
                        reset_seconds = int(response.headers["x-requestcounter-reset"])
                    except (ValueError, TypeError):
                        pass
                elif "Retry-After" in response.headers:
                    try:
                        reset_seconds = int(response.headers["Retry-After"])
                    except (ValueError, TypeError):
                        pass

                # Set the rate limiter to wait for reset
                _rate_limiter.set_rate_limit(reset_seconds + 2)  # Add 2s buffer

                logger.warning(
                    f"Rate limit exceeded! Reset in {reset_seconds}s. "
                    f"Headers: x-requests-available-minute={response.headers.get('x-requests-available-minute')}"
                )
                raise RateLimitError(
                    "Rate limit exceeded for football-data.org",
                    details={
                        "retry_after": reset_seconds,
                        "requests_available": response.headers.get("x-requests-available-minute"),
                    },
                )

            if response.status_code != 200:
                logger.error(f"API error {response.status_code} for {url}: {response.text[:500]}")
                raise FootballDataAPIError(
                    f"API error: {response.status_code}",
                    details={"response": response.text},
                )

            result: dict[str, Any] = response.json()
            return result

    async def get_competitions(self) -> list[dict[str, Any]]:
        """Get list of available competitions."""
        data = await self._request("GET", "/competitions")
        return data.get("competitions", [])  # type: ignore[no-any-return]

    async def get_competition(self, code: str) -> dict[str, Any]:
        """Get competition details."""
        result: dict[str, Any] = await self._request("GET", f"/competitions/{code}")
        return result

    async def get_matches(
        self,
        competition: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: Literal["SCHEDULED", "LIVE", "FINISHED"] | None = None,
        matchday: int | None = None,
    ) -> list[MatchData]:
        """
        Get matches with optional filters. USES CACHE.

        Args:
            competition: Competition code (PL, PD, BL1, SA, FL1, CL, EL)
            date_from: Start date
            date_to: End date
            status: Match status filter
            matchday: Matchday number
        """
        params: dict[str, Any] = {}

        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            # football-data.org API uses exclusive dateTo, so add 1 day
            # to include matches on the end date
            adjusted_date_to = date_to + timedelta(days=1)
            params["dateTo"] = adjusted_date_to.isoformat()
        if status:
            params["status"] = status
        if matchday:
            params["matchday"] = matchday

        if competition:
            endpoint = f"/competitions/{competition}/matches"
        else:
            # Get matches across all competitions
            endpoint = "/matches"
            if not competition:
                # Filter to our supported competitions
                params["competitions"] = ",".join(COMPETITIONS.keys())

        # Check cache first (async Redis with fallback)
        cached = await _cache.get(endpoint, params)
        if cached is not None:
            return [MatchData(**m) for m in cached]

        # Fetch from API
        data = await self._request("GET", endpoint, params)
        matches = data.get("matches", [])

        # Cache the raw data
        await _cache.set(endpoint, params, matches, CACHE_TTL_MATCHES)

        return [MatchData(**m) for m in matches]

    async def get_match(self, match_id: int) -> MatchData:
        """Get single match details. USES CACHE."""
        endpoint = f"/matches/{match_id}"

        # Check cache first
        cached = await _cache.get(endpoint, None)
        if cached is not None:
            logger.debug(f"Cache HIT for match {match_id}")
            return MatchData(**cached)

        # Fetch from API
        data = await self._request("GET", endpoint)

        # Cache the result
        await _cache.set(endpoint, None, data, CACHE_TTL_MATCHES)
        return MatchData(**data)

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """Get team details. USES CACHE."""
        endpoint = f"/teams/{team_id}"

        # Check cache first
        cached = await _cache.get(endpoint, None)
        if cached is not None:
            logger.debug(f"Cache HIT for team {team_id}")
            return cached

        # Fetch from API
        result: dict[str, Any] = await self._request("GET", endpoint)

        # Cache the result
        await _cache.set(endpoint, None, result, CACHE_TTL_TEAM)
        return result

    async def get_team_matches(
        self,
        team_id: int,
        status: Literal["SCHEDULED", "LIVE", "FINISHED"] | None = None,
        limit: int = 10,
    ) -> list[MatchData]:
        """Get matches for a specific team. USES CACHE."""
        endpoint = f"/teams/{team_id}/matches"
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status

        # Check cache first
        cached = await _cache.get(endpoint, params)
        if cached is not None:
            logger.debug(f"Cache HIT for team {team_id} matches")
            return [MatchData(**m) for m in cached]

        # Fetch from API
        data = await self._request("GET", endpoint, params)
        matches = data.get("matches", [])

        # Cache the result
        await _cache.set(endpoint, params, matches, CACHE_TTL_TEAM_MATCHES)

        return [MatchData(**m) for m in matches]

    async def get_standings(self, competition: str) -> list[StandingTeam]:
        """Get current standings for a competition. USES CACHE."""
        endpoint = f"/competitions/{competition}/standings"

        # Check cache first (async Redis with fallback)
        cached = await _cache.get(endpoint, None)
        if cached is not None:
            standings = []
            for standing_group in cached:
                if standing_group.get("type") == "TOTAL":
                    for team_standing in standing_group.get("table", []):
                        standings.append(StandingTeam(**team_standing))
                    break
            return standings

        # Fetch from API
        data = await self._request("GET", endpoint)

        # Cache the raw standings data
        await _cache.set(endpoint, None, data.get("standings", []), CACHE_TTL_STANDINGS)

        standings = []
        for standing_group in data.get("standings", []):
            if standing_group.get("type") == "TOTAL":
                for team_standing in standing_group.get("table", []):
                    standings.append(StandingTeam(**team_standing))
                break

        return standings

    async def get_head_to_head(
        self,
        match_id: int,
        limit: int = 10,
    ) -> list[MatchData]:
        """Get head-to-head history for teams in a match. USES CACHE."""
        endpoint = f"/matches/{match_id}/head2head"
        params: dict[str, Any] = {"limit": limit}

        # Check cache first
        cached = await _cache.get(endpoint, params)
        if cached is not None:
            logger.debug(f"Cache HIT for H2H match {match_id}")
            return [MatchData(**m) for m in cached]

        # Fetch from API
        data = await self._request("GET", endpoint, params)
        matches = data.get("matches", [])

        # Cache the result
        await _cache.set(endpoint, params, matches, CACHE_TTL_H2H)

        return [MatchData(**m) for m in matches]

    async def get_upcoming_matches(
        self,
        days: int = 2,
        competition: str | None = None,
    ) -> list[MatchData]:
        """Get upcoming matches for the next N days."""
        from datetime import timedelta

        today = date.today()
        date_to = today + timedelta(days=days)

        return await self.get_matches(
            competition=competition,
            date_from=today,
            date_to=date_to,
            status="SCHEDULED",
        )


def get_football_data_client() -> FootballDataClient:
    """
    Get FootballDataClient instance with current settings.

    Creates a fresh instance each call to ensure the API key is always
    loaded from current environment variables. This solves the issue where
    a module-level singleton would be initialized before environment
    variables are properly loaded during application startup.

    Returns:
        FootballDataClient: New client instance with current API key
    """
    return FootballDataClient()
