"""Health check endpoints."""

import time
from typing import Any

from fastapi import APIRouter

from src.core.cache import health_check as redis_health_check
from src.core.config import settings
from src.core.rate_limit import STORAGE_URI

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy", "version": settings.app_version}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check including dependencies.

    Returns "ready" if all critical services are up, "degraded" if
    non-critical services (like Redis) are unavailable.
    """
    # Measure Redis health with latency
    redis_start = time.monotonic()
    redis_ok = await redis_health_check()
    redis_latency_ms = round((time.monotonic() - redis_start) * 1000, 1)

    redis_status: dict[str, Any] = {
        "connected": redis_ok,
        "latency_ms": redis_latency_ms if redis_ok else None,
        "backend": "redis" if STORAGE_URI != "memory://" else "memory",
    }

    # Overall status: degraded if Redis is down in production
    if not redis_ok and settings.is_production:
        overall_status = "degraded"
    else:
        overall_status = "ready"

    return {
        "status": overall_status,
        "database": True,
        "redis": redis_status,
        "football_api": bool(settings.football_data_api_key),
        "llm_api": bool(settings.groq_api_key),
    }
