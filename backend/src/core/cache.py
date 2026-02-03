"""Redis cache utility for API response caching.

Provides decorators and utilities for caching expensive API calls.
Uses redis-py with async support for non-blocking operations.
"""

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Type variables for generic function types
T = TypeVar("T")
P = ParamSpec("P")

# Connection pool for efficient Redis connections
_pool: ConnectionPool[Any] | None = None


def get_redis_pool() -> ConnectionPool[Any]:
    """Get or create the Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
    return _pool


async def get_redis_client() -> aioredis.Redis[Any]:
    """Get an async Redis client from the connection pool."""
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def cache_get(key: str) -> str | None:
    """Get a value from cache.

    Args:
        key: The cache key.

    Returns:
        The cached value as a string, or None if not found.
    """
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
        else:
            logger.debug(f"Cache MISS: {key}")
        return str(value) if value else None
    except aioredis.RedisError as e:
        logger.warning(f"Redis GET error for key {key}: {e}")
        return None


async def cache_set(key: str, value: str, ttl: int) -> bool:
    """Set a value in cache with TTL.

    Args:
        key: The cache key.
        value: The value to cache (as string).
        ttl: Time-to-live in seconds.

    Returns:
        True if successful, False otherwise.
    """
    try:
        client = await get_redis_client()
        await client.setex(key, ttl, value)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except aioredis.RedisError as e:
        logger.warning(f"Redis SET error for key {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from cache.

    Args:
        key: The cache key to delete.

    Returns:
        True if successful, False otherwise.
    """
    try:
        client = await get_redis_client()
        await client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except aioredis.RedisError as e:
        logger.warning(f"Redis DELETE error for key {key}: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern.

    Args:
        pattern: The pattern to match (e.g., "predictions:*").

    Returns:
        Number of keys deleted.
    """
    try:
        client = await get_redis_client()
        keys: list[str] = []
        async for key in client.scan_iter(match=pattern):
            keys.append(str(key))
        if keys:
            deleted = await client.delete(*keys)
            logger.info(f"Cache DELETE pattern {pattern}: {deleted} keys removed")
            return int(deleted) if deleted else 0
        return 0
    except aioredis.RedisError as e:
        logger.warning(f"Redis DELETE pattern error for {pattern}: {e}")
        return 0


def generate_cache_key(*args: Any, prefix: str = "cache") -> str:
    """Generate a consistent cache key from arguments.

    Args:
        *args: Arguments to include in the key.
        prefix: Key prefix for namespacing.

    Returns:
        A hashed cache key string.
    """
    # Serialize arguments to JSON for consistent hashing
    key_data = json.dumps(args, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
    return f"{prefix}:{key_hash}"


def cached(
    ttl: int, prefix: str = "cache"
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[Any]]]:
    """Decorator to cache async function results in Redis.

    Args:
        ttl: Time-to-live in seconds.
        prefix: Cache key prefix.

    Usage:
        @cached(ttl=300, prefix="matches")
        async def get_matches(competition: str) -> list[Match]:
            ...
    """

    def decorator(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Generate cache key from function name and arguments
            cache_key = generate_cache_key(
                func.__name__, args, kwargs, prefix=prefix
            )

            # Try to get from cache
            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache for {cache_key}")

            # Call the function
            result = await func(*args, **kwargs)

            # Cache the result
            try:
                await cache_set(cache_key, json.dumps(result, default=str), ttl)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize result for caching: {e}")

            return result

        return wrapper

    return decorator


def cached_response(
    ttl: int, prefix: str = "api"
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[Any]]]:
    """Decorator to cache Pydantic response models.

    Similar to @cached but handles Pydantic models properly.

    Args:
        ttl: Time-to-live in seconds.
        prefix: Cache key prefix.

    Usage:
        @cached_response(ttl=1800, prefix="predictions")
        async def get_prediction(match_id: int) -> PredictionResponse:
            ...
    """

    def decorator(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Generate cache key from function name and arguments
            # Skip 'self' or 'user' arguments that shouldn't affect caching
            cache_args: list[Any] = []

            for arg in args:
                # Skip user/auth objects (typically first arg after self)
                if hasattr(arg, "user_id") or hasattr(arg, "email"):
                    continue
                cache_args.append(arg)

            cache_kwargs: dict[str, Any] = {}
            for key, value in dict(kwargs).items():
                if key in ("user", "current_user"):
                    continue
                cache_kwargs[key] = value

            cache_key = generate_cache_key(
                func.__name__, tuple(cache_args), cache_kwargs, prefix=prefix
            )

            # Try to get from cache
            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                try:
                    data = json.loads(cached_value)
                    # Return cached data as-is (will be Pydantic model dict)
                    logger.debug(f"Returning cached response for {cache_key}")
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache for {cache_key}")

            # Call the function
            result = await func(*args, **kwargs)

            # Cache the result (convert Pydantic model to dict if needed)
            try:
                if hasattr(result, "model_dump"):
                    cache_data = result.model_dump(mode="json")
                elif hasattr(result, "dict"):
                    cache_data = result.dict()
                else:
                    cache_data = result

                await cache_set(
                    cache_key, json.dumps(cache_data, default=str), ttl
                )
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize response for caching: {e}")

            return result

        return wrapper

    return decorator


async def invalidate_match_cache(match_id: int | None = None) -> int:
    """Invalidate match-related cache entries.

    Args:
        match_id: Specific match ID to invalidate, or None for all matches.

    Returns:
        Number of cache entries invalidated.
    """
    if match_id:
        pattern = f"matches:*{match_id}*"
    else:
        pattern = "matches:*"

    count = await cache_delete_pattern(pattern)
    pred_pattern = "predictions:*" if not match_id else f"predictions:*{match_id}*"
    count += await cache_delete_pattern(pred_pattern)
    return count


async def invalidate_standings_cache(competition_code: str | None = None) -> int:
    """Invalidate standings cache entries.

    Args:
        competition_code: Specific competition to invalidate, or None for all.

    Returns:
        Number of cache entries invalidated.
    """
    if competition_code:
        pattern = f"standings:{competition_code}:*"
    else:
        pattern = "standings:*"

    return await cache_delete_pattern(pattern)


async def health_check() -> bool:
    """Check if Redis is available and responding.

    Returns:
        True if Redis is healthy, False otherwise.
    """
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except aioredis.RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        return False
