"""FastAPI application entry point."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.api.routes import (
    admin,
    bets,
    dashboard,
    debug,
    enrichment,
    health,
    matches,
    ml,
    notifications,
    predictions,
    prompts,
    rag,
    stripe,
    sync,
    users,
)
from src.core.config import settings
from src.core.exceptions import ParisportifError
from src.core.rate_limit import limiter
from src.core.sentry import init_sentry
from src.data.database import save_matches, verify_finished_matches
from src.data.sources.football_data import COMPETITIONS, get_football_data_client

# Initialize Sentry for error monitoring
init_sentry()

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def auto_sync_and_verify():
    """
    Automatic job to sync finished matches and verify predictions.
    Runs every 6 hours to keep stats up to date.
    """
    logger.info("[Scheduler] Starting auto sync and verify job...")

    try:
        client = get_football_data_client()
        today = date.today()
        date_from = today - timedelta(days=7)  # Look back 7 days

        total_synced = 0

        # Sync finished matches for each competition
        for comp_code in COMPETITIONS.keys():
            try:
                matches = await client.get_matches(
                    competition=comp_code,
                    date_from=date_from,
                    date_to=today,
                    status="FINISHED",
                )
                matches_dict = [m.model_dump() for m in matches]
                synced = save_matches(matches_dict)
                total_synced += synced

                # Small delay between API calls to respect rate limits
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"[Scheduler] Error syncing {comp_code}: {e}")
                await asyncio.sleep(10)  # Wait longer on error

        # Verify predictions against actual results
        verified_count = verify_finished_matches()

        logger.info(f"[Scheduler] Auto sync complete: {total_synced} matches synced, {verified_count} predictions verified")

    except Exception as e:
        logger.error(f"[Scheduler] Auto sync failed: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS - only in production
        if settings.app_env == "production":
            hsts_value = "max-age=63072000; includeSubDomains; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global scheduler

    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.app_env}")

    # Debug: Show which API key is loaded (masked for security)
    groq_key = settings.groq_api_key
    env_groq_key = os.environ.get("GROQ_API_KEY", "")

    print(f"DEBUG ENV VARS: GROQ_API_KEY from os.environ = {'SET' if env_groq_key else 'NOT SET'}")
    if env_groq_key:
        print(f"DEBUG ENV: {env_groq_key[:8]}...{env_groq_key[-4:]} (len={len(env_groq_key)})")

    if groq_key:
        masked = f"{groq_key[:8]}...{groq_key[-4:]}" if len(groq_key) > 12 else "***"
        print(f"GROQ_API_KEY from settings: {masked} (length: {len(groq_key)})")
    else:
        print("WARNING: GROQ_API_KEY from settings is NOT set or empty!")

    # Start the scheduler for automatic sync
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_sync_and_verify,
        trigger=IntervalTrigger(hours=6),
        id="auto_sync_verify",
        name="Auto sync matches and verify predictions",
        replace_existing=True,
    )
    scheduler.start()
    print("[Scheduler] Started - auto sync every 6 hours")

    # Run initial sync after 30 seconds (let app fully start first)
    asyncio.create_task(_delayed_initial_sync())

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")
    print("Shutting down...")


async def _delayed_initial_sync():
    """Run initial sync after app startup."""
    await asyncio.sleep(30)  # Wait 30 seconds for app to fully start
    logger.info("[Scheduler] Running initial sync...")
    await auto_sync_and_verify()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de predictions de paris sportifs sur le football europeen",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware - Restricted to specific domains for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://paris-sportif.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Exception handlers
@app.exception_handler(ParisportifError)
async def parisportif_exception_handler(request: Request, exc: ParisportifError) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    matches.router,
    prefix=f"{settings.api_v1_prefix}/matches",
    tags=["Matches"],
)
app.include_router(
    predictions.router,
    prefix=f"{settings.api_v1_prefix}/predictions",
    tags=["Predictions"],
)
app.include_router(
    debug.router,
    prefix=f"{settings.api_v1_prefix}/debug",
    tags=["Debug"],
)
app.include_router(
    ml.router,
    prefix=f"{settings.api_v1_prefix}/ml",
    tags=["Machine Learning"],
)
app.include_router(
    sync.router,
    prefix=f"{settings.api_v1_prefix}/sync",
    tags=["Data Sync"],
)
app.include_router(
    rag.router,
    prefix=f"{settings.api_v1_prefix}/rag",
    tags=["RAG Enrichment"],
)
app.include_router(
    enrichment.router,
    prefix=f"{settings.api_v1_prefix}/enrichment",
    tags=["Data Enrichment"],
)
app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users"],
)
app.include_router(
    admin.router,
    prefix=f"{settings.api_v1_prefix}/admin",
    tags=["Admin"],
)
app.include_router(
    prompts.router,
    prefix=f"{settings.api_v1_prefix}/prompts",
    tags=["Prompt Versioning"],
)
app.include_router(
    notifications.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Notifications"],
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.api_v1_prefix}/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    bets.router,
    prefix=f"{settings.api_v1_prefix}/bets",
    tags=["Bets & Bankroll"],
)
app.include_router(
    stripe.router,
    prefix=f"{settings.api_v1_prefix}/stripe",
    tags=["Payments"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
