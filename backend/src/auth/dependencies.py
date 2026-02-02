"""FastAPI dependencies for authentication.

Provides typed dependencies for route protection:
- AuthenticatedUser: Any logged-in user
- PremiumUser: Premium or admin users
- AdminUser: Admin users only
- OptionalUser: Optional authentication (may be None)
"""

from typing import Annotated, Any

from fastapi import Depends

from src.auth.supabase_auth import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_auth,
    require_premium,
)

# Type aliases for cleaner route signatures
AuthenticatedUser = Annotated[dict[str, Any], Depends(require_auth)]
PremiumUser = Annotated[dict[str, Any], Depends(require_premium)]
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]
OptionalUser = Annotated[dict[str, Any] | None, Depends(get_optional_user)]


def get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from JWT payload."""
    return user.get("sub", "")


def get_user_email(user: dict[str, Any]) -> str | None:
    """Extract email from JWT payload."""
    return user.get("email")


def get_user_role(user: dict[str, Any]) -> str:
    """Extract role from JWT payload."""
    app_metadata = user.get("app_metadata", {})
    user_metadata = user.get("user_metadata", {})
    return app_metadata.get("role") or user_metadata.get("role") or "free"
