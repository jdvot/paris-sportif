"""Rate limiting configuration for API protection."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Get Redis URL from environment for production, fallback to memory for dev
REDIS_URL = os.getenv("REDIS_URL", "")
STORAGE_URI = REDIS_URL if REDIS_URL else "memory://"

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
