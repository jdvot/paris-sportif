"""Sentry configuration for error monitoring and alerting."""

import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration


def init_sentry() -> None:
    """Initialize Sentry SDK for error monitoring."""
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        print("WARNING: SENTRY_DSN not set, Sentry disabled")
        return

    environment = os.getenv("APP_ENV", "development")

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        # Performance monitoring
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        # Profiling
        profiles_sample_rate=0.1 if environment == "production" else 1.0,
        # Integrations
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        # Send user info (without PII)
        send_default_pii=False,
        # Only enable in production
        enabled=environment == "production",
    )

    print(f"Sentry initialized for environment: {environment}")
