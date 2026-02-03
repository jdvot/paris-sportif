"""Authentication module for Supabase JWT validation."""

from src.auth.dependencies import (
    AdminUser,
    AuthenticatedUser,
    OptionalUser,
    PremiumUser,
)
from src.auth.responses import (
    ADMIN_RESPONSES,
    AUTH_RESPONSES,
    PREMIUM_RESPONSES,
    HTTPErrorResponse,
)
from src.auth.supabase_auth import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_auth,
    require_premium,
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
