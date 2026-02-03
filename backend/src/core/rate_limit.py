"""Rate limiting configuration for API protection."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance with IP-based rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
)

# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    "default": "100/minute",
    "predictions": "30/minute",  # Heavy compute endpoints
    "matches": "60/minute",      # Data fetching endpoints
    "auth": "10/minute",         # Auth endpoints (strict)
    "admin": "20/minute",        # Admin endpoints
}
