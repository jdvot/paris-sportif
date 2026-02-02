"""Authentication module for Supabase JWT validation."""

from src.auth.supabase_auth import (
    get_current_user,
    get_optional_user,
    require_auth,
    require_premium,
    require_admin,
)
from src.auth.dependencies import (
    AuthenticatedUser,
    PremiumUser,
    AdminUser,
    OptionalUser,
)
from src.auth.responses import (
    HTTPErrorResponse,
    AUTH_RESPONSES,
    PREMIUM_RESPONSES,
    ADMIN_RESPONSES,
)

__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_auth",
    "require_premium",
    "require_admin",
    "AuthenticatedUser",
    "PremiumUser",
    "AdminUser",
    "OptionalUser",
    "HTTPErrorResponse",
    "AUTH_RESPONSES",
    "PREMIUM_RESPONSES",
    "ADMIN_RESPONSES",
]
