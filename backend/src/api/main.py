"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.api.routes import matches, predictions, health, debug, ml, sync, rag, enrichment, users, admin
from src.core.config import settings
from src.core.exceptions import ParisportifError


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS - only in production
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
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

    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de predictions de paris sportifs sur le football europeen",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Exception handlers
@app.exception_handler(ParisportifError)
async def parisportif_exception_handler(
    request: Request, exc: ParisportifError
) -> JSONResponse:
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


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
