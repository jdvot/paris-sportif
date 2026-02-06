"""Rate limiting configuration for API protection.

Supports per-user rate limiting based on JWT identity and role-based tiers:
- Unauthenticated: 30 requests/minute (IP-based)
- Authenticated (free): 100 requests/minute (user-based)
- Admin: 500 requests/minute (user-based)
"""

import base64
import json
import logging
import os
import re
from typing import Any

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


def parse_redis_url(raw_url: str) -> str:
    """Parse and normalize Redis URL from environment.

    Handles cases where the URL might be wrapped in a redis-cli command,
    and ensures proper scheme for TLS connections.
    """
    if not raw_url:
        return ""

    # Extract URL if wrapped in redis-cli command
    # e.g., "redis-cli --tls -u redis://..." -> "redis://..."
    url_match = re.search(r"(rediss?://[^\s]+)", raw_url)
    if url_match:
        url = url_match.group(1)
    else:
        url = raw_url

    # If --tls flag was present but URL uses redis://, convert to rediss://
    if "--tls" in raw_url and url.startswith("redis://"):
        url = url.replace("redis://", "rediss://", 1)

    return url


def _extract_jwt_payload(token: str) -> dict[str, Any] | None:
    """Extract payload from a JWT token without cryptographic verification.

    This is used only for rate limiting key extraction, where we need the user ID
    and role to assign the correct rate limit bucket. Full token verification is
    handled separately by the auth middleware.
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Base64url decode the payload (second part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload: dict[str, Any] = json.loads(payload_bytes)
        return payload
    except Exception:
        return None


def _get_role_from_payload(payload: dict[str, Any]) -> str:
    """Extract user role from JWT payload.

    Mirrors the role extraction logic in supabase_auth._get_user_role.
    """
    app_metadata = payload.get("app_metadata", {})
    user_metadata = payload.get("user_metadata", {})

    role = app_metadata.get("role")
    if role:
        return str(role)

    role = user_metadata.get("role")
    if role:
        return str(role)

    return "free"


def get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key from request.

    If the request has a valid JWT Authorization header, uses 'user:{user_id}'
    as the key for per-user rate limiting. Otherwise falls back to IP-based limiting.
    """
    auth_header = request.headers.get("authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # len("Bearer ") == 7
        payload = _extract_jwt_payload(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"

    # Fallback to IP-based limiting for unauthenticated requests
    return get_remote_address(request)


# --- Rate limit tier definitions ---

TIER_LIMITS = {
    "unauthenticated": "30/minute",
    "free": "100/minute",
    "premium": "100/minute",
    "admin": "500/minute",
}


def get_user_tier_limit(request: Request) -> str:
    """Return the rate limit string based on the user's authentication tier.

    Used as a dynamic rate limit callable with slowapi's @limiter.limit().
    Example usage in routes: @limiter.limit(limit_value=get_user_tier_limit)
    """
    auth_header = request.headers.get("authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _extract_jwt_payload(token)
        if payload and payload.get("sub"):
            role = _get_role_from_payload(payload)
            return TIER_LIMITS.get(role, TIER_LIMITS["free"])

    return TIER_LIMITS["unauthenticated"]


# Get Redis URL from environment for production, fallback to memory for dev
RAW_REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_URL = parse_redis_url(RAW_REDIS_URL)
APP_ENV = os.getenv("APP_ENV", "development")
STORAGE_URI = REDIS_URL if REDIS_URL else "memory://"

# In production, warn critically if Redis is not configured.
# We don't block startup because Upstash may have brief outages,
# but rate limiting without Redis means each worker has its own counter.
if APP_ENV == "production" and STORAGE_URI == "memory://":
    logger.critical(
        "REDIS_URL is not set in production! "
        "Rate limiting will use in-memory storage (per-worker, not shared). "
        "Set REDIS_URL to an Upstash or Redis instance for proper rate limiting."
    )

# Create limiter instance with per-user rate limiting
# Uses user:{user_id} as key for authenticated requests, IP for unauthenticated
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Default: 100 requests per minute
    storage_uri=STORAGE_URI,
)

# Rate limit configurations for different endpoint types
# These are used with @limiter.limit(RATE_LIMITS["..."]) in route files.
# For tier-based limits, use @limiter.limit(limit_value=get_user_tier_limit) instead.
RATE_LIMITS = {
    "default": "100/minute",
    "predictions": "30/minute",  # Heavy compute endpoints
    "matches": "60/minute",  # Data fetching endpoints
    "auth": "10/minute",  # Auth endpoints (strict)
    "admin": "20/minute",  # Admin endpoints
    "sync": "5/minute",  # Sync endpoints (very heavy)
}
