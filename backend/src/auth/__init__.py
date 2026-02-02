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
]
