"""Rate limiting configuration for API protection."""

import logging
import os
import re

from slowapi import Limiter
from slowapi.util import get_remote_address

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

# Create limiter instance with IP-based rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri=STORAGE_URI,
)

# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    "default": "100/minute",
    "predictions": "30/minute",  # Heavy compute endpoints
    "matches": "60/minute",  # Data fetching endpoints
    "auth": "10/minute",  # Auth endpoints (strict)
    "admin": "20/minute",  # Admin endpoints
    "sync": "5/minute",  # Sync endpoints (very heavy)
}
