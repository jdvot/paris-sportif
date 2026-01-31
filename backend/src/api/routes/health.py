"""Health check endpoints."""

from fastapi import APIRouter

from src.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy", "version": settings.app_version}


@router.get("/health/ready")
async def readiness_check() -> dict[str, str | bool]:
    """Readiness check including dependencies."""
    # TODO: Add database and Redis connection checks
    return {
        "status": "ready",
        "database": True,
        "redis": True,
        "football_api": bool(settings.football_data_api_key),
        "llm_api": bool(settings.anthropic_api_key),
    }
