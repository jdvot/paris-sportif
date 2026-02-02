"""Supabase JWT authentication for FastAPI.

Validates JWT tokens issued by Supabase and extracts user information.
Supports role-based access control (free, premium, admin).
"""

import logging
import os
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Security scheme - auto_error=False allows optional auth
security = HTTPBearer(auto_error=False)

# Supabase configuration from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")


def _get_jwt_secret() -> str:
    """Get JWT secret, with helpful error message if not configured."""
    secret = SUPABASE_JWT_SECRET
    if not secret:
        logger.warning("SUPABASE_JWT_SECRET not configured - auth will fail")
    return secret


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    """
    Extract user from JWT token if present, return None otherwise.

    Use this for routes that work with or without authentication,
    but may provide enhanced features for authenticated users.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        secret = _get_jwt_secret()

        if not secret:
            logger.warning("Cannot validate token: JWT secret not configured")
            return None

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )

        logger.debug(f"Token validated for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.debug(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """
    Extract and validate user from JWT token.

    Raises HTTPException 401 if token is missing or invalid.
    Use this for routes that require authentication.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
        secret = _get_jwt_secret()

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration serveur invalide",
            )

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )

        logger.debug(f"Authenticated user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _get_user_role(user: dict[str, Any]) -> str:
    """Extract user role from JWT payload."""
    # Role can be in app_metadata or user_metadata
    app_metadata = user.get("app_metadata", {})
    user_metadata = user.get("user_metadata", {})

    # Check app_metadata first (more authoritative)
    role = app_metadata.get("role")
    if role:
        return role

    # Fallback to user_metadata
    role = user_metadata.get("role")
    if role:
        return role

    # Default to free
    return "free"


def require_auth(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Dependency that requires authentication.

    Simply returns the authenticated user or raises 401.
    Use as: user = Depends(require_auth)
    """
    return user


def require_premium(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Dependency that requires premium or admin role.

    Raises 401 if not authenticated, 403 if not premium/admin.
    Use as: user = Depends(require_premium)
    """
    role = _get_user_role(user)

    if role not in ("premium", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Abonnement premium requis pour acceder a cette ressource",
        )

    return user


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Dependency that requires admin role.

    Raises 401 if not authenticated, 403 if not admin.
    Use as: user = Depends(require_admin)
    """
    role = _get_user_role(user)

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces administrateur requis",
        )

    return user
