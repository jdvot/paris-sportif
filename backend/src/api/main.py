"""FastAPI application entry point."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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
    basketball,
    bets,
    dashboard,
    debug,
    enrichment,
    favorites,
    health,
    matches,
    ml,
    notifications,
    predictions,
    prompts,
    rag,
    search,
    stripe,
    sync,
    tennis,
    testimonials,
    users,
    vector,
)
from src.api.routes.sync import (
    _calculate_proper_elo_ratings,
    _recalculate_all_team_stats,
    _sync_form_from_standings,
    _update_missing_team_countries,
    _update_team_elo_ratings,
)
from src.core.config import settings
from src.core.exceptions import ParisportifError
from src.core.logging_config import generate_request_id, setup_logging
from src.core.rate_limit import limiter
from src.core.sentry import init_sentry
from src.data.sources.football_data import (  # type: ignore[attr-defined]
    COMPETITIONS,
    get_football_data_client,
)
from src.db.services.match_service import MatchService, StandingService
from src.db.services.prediction_service import PredictionService
from src.services.data_prefill_service import DataPrefillService
from src.services.nba_sync_service import sync_nba_games
from src.services.tennis_sync_service import sync_tennis_matches

# Initialize Sentry for error monitoring
init_sentry()

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def _sync_finished_matches(client: Any, past_date: date, today: date) -> int:
    """Sync finished matches from football-data.org for each competition."""
    total = 0
    for comp_code in COMPETITIONS.keys():
        try:
            matches = await client.get_matches(
                competition=comp_code,
                date_from=past_date,
                date_to=today,
                status="FINISHED",
            )
            total += await MatchService.save_matches([m.model_dump() for m in matches])
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"[Scheduler] Error syncing finished {comp_code}: {e}")
            await asyncio.sleep(10)
    return total


async def _sync_upcoming_matches(client: Any, today: date, future_date: date) -> int:
    """Sync upcoming/scheduled matches for the next 7 days."""
    total = 0
    for comp_code in COMPETITIONS.keys():
        try:
            matches = await client.get_matches(
                competition=comp_code,
                date_from=today,
                date_to=future_date,
                status="SCHEDULED",
            )
            total += await MatchService.save_matches([m.model_dump() for m in matches])
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"[Scheduler] Error syncing upcoming {comp_code}: {e}")
            await asyncio.sleep(10)
    return total


async def _sync_league_standings(client: Any) -> int:
    """Sync standings for all league competitions."""
    total = 0
    for comp_code in COMPETITIONS.keys():
        try:
            data = await client._request("GET", f"/competitions/{comp_code}/standings")
            for standing_group in data.get("standings", []):
                if standing_group.get("type") == "TOTAL":
                    total += await StandingService.save_standings(
                        comp_code, standing_group.get("table", [])
                    )
                    break
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"[Scheduler] Error syncing standings for {comp_code}: {e}")
    return total


async def _post_sync_maintenance() -> dict[str, int]:
    """Run post-sync maintenance: verify predictions, recalculate stats, ELO, etc."""
    r: dict[str, int] = {}
    r["verified"] = await PredictionService.verify_all_finished()

    for label, coro in [
        ("teams", _recalculate_all_team_stats()),
        ("forms", _sync_form_from_standings()),
        ("countries", _update_missing_team_countries()),
    ]:
        try:
            r[label] = await coro
        except Exception as e:
            logger.warning(f"[Scheduler] Error in {label}: {e}")
            r[label] = 0

    try:
        elo_ratings = await _calculate_proper_elo_ratings()
        r["elo"] = await _update_team_elo_ratings(elo_ratings)
    except Exception as e:
        logger.warning(f"[Scheduler] Error calculating ELO: {e}")
        r["elo"] = 0

    try:
        r["predictions"] = await DataPrefillService.prefill_predictions_for_upcoming()
    except Exception as e:
        logger.warning(f"[Scheduler] Error pre-generating predictions: {e}")
        r["predictions"] = 0

    try:
        r["cached"] = await DataPrefillService.warm_redis_cache()
    except Exception as e:
        logger.warning(f"[Scheduler] Error warming cache: {e}")
        r["cached"] = 0

    return r


async def auto_sync_and_verify() -> None:
    """
    Automatic job to sync matches, standings, and verify predictions.
    Runs every 6 hours to keep stats up to date.
    """
    logger.info("[Scheduler] Starting auto sync and verify job...")
    try:
        client = get_football_data_client()
        today = date.today()
        past_date = today - timedelta(days=7)
        future_date = today + timedelta(days=7)

        finished = await _sync_finished_matches(client, past_date, today)
        upcoming = await _sync_upcoming_matches(client, today, future_date)
        standings = await _sync_league_standings(client)
        m = await _post_sync_maintenance()

        logger.info(
            f"[Scheduler] Auto sync complete: {finished} finished, {upcoming} upcoming, "
            f"{standings} standings, {m.get('verified', 0)} verified, {m.get('teams', 0)} stats, "
            f"{m.get('forms', 0)} forms, {m.get('countries', 0)} countries, {m.get('elo', 0)} ELO, "
            f"{m.get('predictions', 0)} predictions, {m.get('cached', 0)} cached"
        )
    except Exception as e:
        logger.error(f"[Scheduler] Auto sync failed: {e}")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that binds a unique request_id to structlog context vars."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.clear_contextvars()
        return response


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
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://*.supabase.co https://*.groq.com; "
            "frame-ancestors 'none'"
        )

        # HSTS - only in production
        if settings.app_env == "production":
            hsts_value = "max-age=63072000; includeSubDomains; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global scheduler

    # Configure structured logging BEFORE anything else
    setup_logging(
        json_output=settings.is_production,
        log_level=settings.log_level,
    )

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")

    # Initialize database tables
    try:
        from src.db.database import init_db

        await init_db()
        logger.info("[Database] Tables initialized")
    except Exception as e:
        logger.error(f"[Database] Could not initialize tables: {e}")
        if settings.is_production:
            raise

    # Check API key availability (no values logged)
    groq_key = settings.groq_api_key
    if groq_key:
        logger.info("GROQ_API_KEY: configured")
    else:
        logger.warning("GROQ_API_KEY: NOT set or empty")

    # Start the scheduler for automatic sync
    scheduler = AsyncIOScheduler(
        job_defaults={"max_instances": 1, "coalesce": True},
    )
    scheduler.add_job(
        auto_sync_and_verify,
        trigger=IntervalTrigger(hours=6),
        id="auto_sync_verify",
        name="Auto sync matches and verify predictions",
        replace_existing=True,
    )

    # Add daily cache calculation job at 6am UTC
    scheduler.add_job(
        _run_daily_cache,
        trigger=CronTrigger(hour=6, minute=0),  # 6:00 AM UTC daily
        id="daily_cache_calculation",
        name="Calculate and cache stats at 6am daily",
        replace_existing=True,
    )

    # Add weekly ML training job (Sunday 3am UTC)
    scheduler.add_job(
        _run_weekly_ml_training,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_ml_training",
        name="Train ML models on HuggingFace weekly",
        replace_existing=True,
    )

    # Hourly prediction prefill for this week's matches (full enrichment: RAG, LLM, weather, etc.)
    scheduler.add_job(
        _hourly_prediction_prefill,
        trigger=IntervalTrigger(hours=1),
        id="hourly_predictions",
        name="Hourly prediction prefill (7-day window)",
        replace_existing=True,
    )

    # Tennis sync - every 12 hours
    scheduler.add_job(
        sync_tennis_matches,
        trigger=IntervalTrigger(hours=12),
        id="tennis_sync",
        name="Sync tennis matches and predictions",
        replace_existing=True,
    )

    # NBA sync - every 6 hours
    scheduler.add_job(
        sync_nba_games,
        trigger=IntervalTrigger(hours=6),
        id="nba_sync",
        name="Sync NBA games and predictions",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] Started - predictions 1h, football sync 6h, NBA 6h, tennis 12h, cache 6am UTC"
    )

    # Run startup prefill in background (delayed 30s to let server accept traffic first)
    asyncio.create_task(_delayed_startup_prefill())

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")

    # Close shared HTTP client
    from src.core.http_client import close_http_client

    await close_http_client()

    logger.info("Shutting down...")


async def _hourly_prediction_prefill() -> None:
    """Hourly job: generate predictions with full enrichment for this week's matches.

    Runs the complete pipeline (6-model ensemble, multi-markets, weather,
    LLM analysis, RAG news summary, fatigue, injuries, match importance)
    for any match in the next 7 days missing a complete prediction.
    Skips matches that already have full data.
    """
    logger.info("[Scheduler] Starting hourly prediction prefill (7-day window)...")
    try:
        generated = await DataPrefillService.prefill_predictions_for_upcoming(days=7)
        if generated > 0:
            # Warm Redis cache for newly generated predictions
            cached = await DataPrefillService.warm_redis_cache()
            logger.info(
                f"[Scheduler] Hourly prefill: {generated} predictions generated, {cached} cached"
            )
        else:
            logger.info("[Scheduler] Hourly prefill: all predictions up to date")
    except Exception as e:
        logger.error(f"[Scheduler] Hourly prediction prefill failed: {e}")


async def _delayed_startup_prefill() -> None:
    """Delay startup prefill to let the server accept health checks first."""
    await asyncio.sleep(30)
    await _startup_full_prefill()


async def _startup_full_prefill() -> None:
    """Run complete prefill pipeline at startup."""
    logger.info("[Startup] Starting full prefill pipeline...")

    try:
        from sqlalchemy import text

        from src.db import get_db_context
        from src.services.data_prefill_service import DataPrefillService, log_sync_operation

        # Check match count to decide if historical sync needed
        with get_db_context() as db:
            result = db.execute(text("SELECT COUNT(*) FROM matches WHERE status = 'FINISHED'"))
            match_count = result.scalar() or 0

        if match_count < 200:
            logger.info(
                f"[Startup] Only {match_count} matches in DB, fetching historical season data..."
            )
            await log_sync_operation("historical_sync", "running", 0, triggered_by="startup")
            await _fetch_historical_season()
            await log_sync_operation("historical_sync", "success", 0, triggered_by="startup")
        else:
            logger.info(f"[Startup] {match_count} matches in DB, running normal sync...")
            await log_sync_operation("auto_sync", "running", 0, triggered_by="startup")
            await auto_sync_and_verify()
            await log_sync_operation("auto_sync", "success", 0, triggered_by="startup")

        # Sync NBA and Tennis data
        logger.info("[Startup] Syncing NBA data...")
        try:
            await sync_nba_games()
        except Exception as e:
            logger.warning(f"[Startup] NBA sync failed: {e}")

        logger.info("[Startup] Syncing Tennis data...")
        try:
            await sync_tennis_matches()
        except Exception as e:
            logger.warning(f"[Startup] Tennis sync failed: {e}")

        # Now run full data prefill (team data, ELO, predictions, cache, news)
        logger.info("[Startup] Running data prefill...")
        prefill_result = await DataPrefillService.run_full_prefill(triggered_by="startup")
        logger.info(f"[Startup] Prefill complete: {prefill_result}")

        # Run cache calculation
        logger.info("[Startup] Running cache calculation...")
        await _run_daily_cache()

        logger.info("[Startup] Full startup pipeline complete!")

    except Exception as e:
        logger.error(f"[Startup] Error in startup prefill: {e}", exc_info=True)


async def _fetch_historical_season() -> None:
    """Fetch all matches from the start of the season."""
    import asyncio as aio
    from datetime import date

    from src.api.routes.sync import (
        _recalculate_all_team_stats,
        _sync_all_standings,
        _sync_form_from_standings,
    )
    from src.core.exceptions import FootballDataAPIError, RateLimitError

    logger.info("[Scheduler] Starting historical season sync...")

    client = get_football_data_client()
    # Dynamically calculate current season start (August 1st)
    today = date.today()
    season_year = today.year if today.month >= 8 else today.year - 1
    season_start = date(season_year, 8, 1)
    total_synced = 0

    for comp_code in COMPETITIONS.keys():
        try:
            logger.info(f"[Scheduler] Fetching historical matches for {comp_code}...")
            matches = await client.get_matches(
                competition=comp_code,
                date_from=season_start,
                date_to=today,
                status="FINISHED",
            )
            matches_dict = [m.model_dump() for m in matches]
            synced = await MatchService.save_matches(matches_dict)
            total_synced += synced
            logger.info(f"[Scheduler] Synced {synced} matches for {comp_code}")
            await aio.sleep(8)  # Respect rate limits

        except RateLimitError:
            logger.warning(f"[Scheduler] Rate limit for {comp_code}, waiting 60s...")
            await aio.sleep(60)
        except (FootballDataAPIError, Exception) as e:
            logger.error(f"[Scheduler] Error syncing {comp_code}: {e}")

    # Sync standings
    try:
        await _sync_all_standings()
    except Exception as e:
        logger.error(f"[Scheduler] Standings sync failed: {e}")

    # Recalculate team stats
    try:
        teams = await _recalculate_all_team_stats()
        logger.info(f"[Scheduler] Updated stats for {teams} teams")
    except Exception as e:
        logger.error(f"[Scheduler] Stats calculation failed: {e}")

    # Sync form
    try:
        forms = await _sync_form_from_standings()
        logger.info(f"[Scheduler] Synced form for {forms} teams")
    except Exception as e:
        logger.error(f"[Scheduler] Form sync failed: {e}")

    logger.info(f"[Scheduler] Historical sync complete: {total_synced} matches")


async def _run_daily_cache() -> None:
    """Run daily cache calculation."""
    logger.info("[Scheduler] Running daily cache calculation...")
    try:
        from src.services.cache_service import init_cache_table, run_daily_cache_calculation

        await init_cache_table()
        result = await run_daily_cache_calculation()
        logger.info(
            f"[Scheduler] Cache calculation complete: {len(result['success'])} success, {len(result['failed'])} failed"
        )
    except Exception as e:
        logger.error(f"[Scheduler] Cache calculation failed: {e}")


async def _delayed_initial_cache() -> None:
    """Run initial cache calculation after app startup."""
    await asyncio.sleep(60)  # Wait 60 seconds for app and sync to complete
    logger.info("[Scheduler] Running initial cache calculation...")
    await _run_daily_cache()


async def _run_weekly_ml_training() -> None:
    """Run weekly ML model training on HuggingFace."""
    import httpx
    from sqlalchemy import text

    from src.db import get_db_context

    hf_space_url = os.getenv("HF_SPACE_URL", "https://jdevot244-paris-sportif.hf.space")

    logger.info("[Scheduler] Running weekly ML training on HuggingFace...")

    # Fetch training data
    training_matches: list[dict[str, Any]] = []

    try:
        with get_db_context() as db:
            query = text(
                """
                SELECT
                    m.home_score, m.away_score,
                    COALESCE(ht.avg_goals_scored_home, 1.0) as home_attack,
                    COALESCE(ht.avg_goals_conceded_home, 1.0) as home_defense,
                    COALESCE(ht.elo_rating, 1500) as home_elo,
                    COALESCE(at.avg_goals_scored_away, 1.0) as away_attack,
                    COALESCE(at.avg_goals_conceded_away, 1.0) as away_defense,
                    COALESCE(at.elo_rating, 1500) as away_elo
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams at ON m.away_team_id = at.id
                WHERE m.status = 'FINISHED'
                    AND m.home_score IS NOT NULL
                ORDER BY m.match_date DESC
                LIMIT 2000
            """
            )

            result = db.execute(query)
            for row in result.fetchall():
                training_matches.append(
                    {
                        "home_attack": float(row.home_attack or 1.0),
                        "home_defense": float(row.home_defense or 1.0),
                        "away_attack": float(row.away_attack or 1.0),
                        "away_defense": float(row.away_defense or 1.0),
                        "home_elo": float(row.home_elo or 1500.0),
                        "away_elo": float(row.away_elo or 1500.0),
                        "home_form": 0.5,
                        "away_form": 0.5,
                        "home_rest_days": 7.0,
                        "away_rest_days": 7.0,
                        "home_fixture_congestion": 0.0,
                        "away_fixture_congestion": 0.0,
                        "home_score": row.home_score,
                        "away_score": row.away_score,
                    }
                )

        logger.info(f"[Scheduler] Fetched {len(training_matches)} matches for training")

        if len(training_matches) < 100:
            logger.warning("[Scheduler] Not enough matches for training")
            return

        # Send to HuggingFace
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{hf_space_url}/train",
                json={"matches": training_matches},
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"[Scheduler] ML Training complete: "
                    f"XGB={data.get('accuracy_xgboost'):.3f}, "
                    f"RF={data.get('accuracy_random_forest'):.3f}, "
                    f"samples={data.get('training_samples')}"
                )
            else:
                logger.error(f"[Scheduler] ML Training failed: {response.status_code}")

    except Exception as e:
        logger.error(f"[Scheduler] ML Training error: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de predictions de paris sportifs sur le football europeen",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request ID Middleware (binds request_id to structured logs)
app.add_middleware(RequestIdMiddleware)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware - Restricted to specific domains for security
_cors_origins = ["https://paris-sportif.vercel.app"]
if not settings.is_production:
    _cors_origins += ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
app.include_router(
    favorites.router,
    prefix=f"{settings.api_v1_prefix}/user",
    tags=["User Data"],
)
app.include_router(
    vector.router,
    prefix=f"{settings.api_v1_prefix}/vector",
    tags=["Vector Store"],
)
app.include_router(
    testimonials.router,
    prefix=f"{settings.api_v1_prefix}/testimonials",
    tags=["Testimonials"],
)
app.include_router(
    search.router,
    prefix=f"{settings.api_v1_prefix}/search",
    tags=["Search"],
)
app.include_router(
    tennis.router,
    prefix=f"{settings.api_v1_prefix}/tennis",
    tags=["Tennis"],
)
app.include_router(
    basketball.router,
    prefix=f"{settings.api_v1_prefix}/basketball",
    tags=["Basketball"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
