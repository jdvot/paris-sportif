"""Supabase JWT authentication for FastAPI.

Validates JWT tokens issued by Supabase and extracts user information.
Supports both legacy HS256 and modern ES256 (ECC) token verification.
Supports role-based access control (free, premium, admin).
"""

import logging
import os
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Security scheme - auto_error=False allows optional auth
security = HTTPBearer(auto_error=False)

# Supabase configuration from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Cache for JWKS keys
_jwks_cache: dict[str, Any] | None = None


def _get_jwt_secret() -> str:
    """Get JWT secret, with helpful error message if not configured."""
    secret = SUPABASE_JWT_SECRET
    if not secret:
        logger.warning("SUPABASE_JWT_SECRET not configured - auth will fail")
    return secret


def _get_jwks_url() -> str | None:
    """Get JWKS URL from Supabase URL."""
    if not SUPABASE_URL:
        return None
    # Remove trailing slash if present
    base_url = SUPABASE_URL.rstrip("/")
    # Supabase JWKS is at /auth/v1/.well-known/jwks.json
    return f"{base_url}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict[str, Any] | None:
    """Fetch JWKS from Supabase (cached)."""
    jwks_url = _get_jwks_url()
    if not jwks_url:
        logger.debug("No JWKS URL configured")
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(jwks_url)
            response.raise_for_status()
            jwks: dict[str, Any] = response.json()
            logger.info(f"Fetched JWKS from {jwks_url}")
            return jwks
    except Exception as e:
        logger.warning(f"Failed to fetch JWKS: {e}")
        return None


def _get_signing_key(token: str, jwks: dict[str, Any]) -> dict[str, Any] | None:
    """Get the signing key from JWKS that matches the token's kid."""
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            return None

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key  # type: ignore[no-any-return]

        logger.warning(f"No matching key found for kid: {kid}")
        return None
    except Exception as e:
        logger.debug(f"Error getting signing key: {e}")
        return None


def _decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a Supabase JWT token.

    Tries multiple verification methods:
    1. ES256 with JWKS public key (modern Supabase)
    2. HS256/HS384/HS512 with shared secret (legacy)
    """
    # First, peek at the token to see what algorithm it uses
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "")
        logger.debug(f"Token algorithm: {alg}")
    except Exception:
        alg = ""

    # Try ES256 with JWKS first if algorithm suggests it
    if alg in ("ES256", "ES384", "ES512", "RS256", "RS384", "RS512"):
        jwks = _fetch_jwks()
        if jwks:
            signing_key = _get_signing_key(token, jwks)
            if signing_key:
                try:
                    payload: dict[str, Any] = jwt.decode(
                        token,
                        signing_key,
                        algorithms=[alg],
                        audience="authenticated",
                    )
                    logger.debug("Token verified with JWKS")
                    return payload
                except JWTError as e:
                    logger.debug(f"JWKS verification failed: {e}")

    # Fallback to HMAC with shared secret
    secret = _get_jwt_secret()
    if secret:
        try:
            hmac_payload: dict[str, Any] = jwt.decode(
                token,
                secret,
                algorithms=["HS256", "HS384", "HS512"],
                audience="authenticated",
            )
            logger.debug("Token verified with shared secret")
            return hmac_payload
        except JWTError as e:
            logger.debug(f"Shared secret verification failed: {e}")
            raise

    raise JWTError("No valid verification method available")


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
        payload = _decode_token(token)
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
        payload = _decode_token(token)
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
        return str(role)

    # Fallback to user_metadata
    role = user_metadata.get("role")
    if role:
        return str(role)

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


async def update_user_metadata(user_id: str, user_metadata: dict[str, Any]) -> dict[str, Any] | None:
    """
    Update user metadata in Supabase using the Admin API.

    Args:
        user_id: The user's UUID (from JWT 'sub' claim)
        user_metadata: Dictionary of metadata fields to update

    Returns:
        Updated user data or None if update failed
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase admin credentials not configured - cannot update user metadata")
        return None

    base_url = SUPABASE_URL.rstrip("/")
    url = f"{base_url}/auth/v1/admin/users/{user_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                url,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Content-Type": "application/json",
                },
                json={"user_metadata": user_metadata},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            logger.info(f"Updated user metadata for {user_id}")
            return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to update user metadata: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error updating user metadata: {e}")
        return None
