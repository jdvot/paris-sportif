"""Health check endpoints."""

from fastapi import APIRouter

from src.core.cache import health_check as redis_health_check
from src.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy", "version": settings.app_version}


@router.get("/health/ready")
async def readiness_check() -> dict[str, str | bool]:
    """Readiness check including dependencies."""
    redis_ok = await redis_health_check()
    return {
        "status": "ready",
        "database": True,
        "redis": redis_ok,
        "football_api": bool(settings.football_data_api_key),
        "llm_api": bool(settings.groq_api_key),
    }
