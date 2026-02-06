"""Supabase JWT authentication for FastAPI.

Validates JWT tokens issued by Supabase and extracts user information.
Supports both legacy HS256 and modern ES256 (ECC) token verification.
Supports role-based access control (free, premium, admin).
"""

import logging
import os
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
_jwks_cache_time: float = 0.0
_JWKS_CACHE_TTL = 3600  # 1 hour


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


def _fetch_jwks() -> dict[str, Any] | None:
    """Fetch JWKS from Supabase (cached with TTL)."""
    global _jwks_cache, _jwks_cache_time
    import time

    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache
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
            _jwks_cache = jwks
            _jwks_cache_time = now
            return jwks
    except Exception as e:
        logger.warning(f"Failed to fetch JWKS: {e}")
        # Return stale cache if available
        return _jwks_cache


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
            detail="Authentication required",
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
            detail="Invalid or expired token",
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
            detail="Premium subscription required",
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
            detail="Admin access required",
        )

    return user


async def get_user_from_supabase(user_id: str) -> dict[str, Any] | None:
    """
    Fetch fresh user data from Supabase Admin API.

    Args:
        user_id: The user's UUID (from JWT 'sub' claim)

    Returns:
        User data dict or None if fetch failed
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase admin credentials not configured - cannot fetch user")
        return None

    base_url = SUPABASE_URL.rstrip("/")
    url = f"{base_url}/auth/v1/admin/users/{user_id}"

    try:
        from src.core.http_client import get_http_client

        client = get_http_client()
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to fetch user from Supabase: {e.response.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching user from Supabase: {e}")
        return None


async def update_user_metadata(
    user_id: str, user_metadata: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Update user metadata in Supabase using the Admin API.
    Also updates the user_profiles table if it exists.

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
    auth_url = f"{base_url}/auth/v1/admin/users/{user_id}"

    try:
        from src.core.http_client import get_http_client

        client = get_http_client()
        # Update user_metadata in Supabase Auth
        response = await client.put(
            auth_url,
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

        # Also update user_profiles table if full_name is being updated
        if "full_name" in user_metadata:
            await _update_user_profiles_table(client, base_url, user_id, user_metadata)

        return result
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to update user metadata: {e.response.status_code} - {e.response.text}"
        )
        return None
    except Exception as e:
        logger.error(f"Error updating user metadata: {e}")
        return None


async def _update_user_profiles_table(
    client: httpx.AsyncClient,
    base_url: str,
    user_id: str,
    user_metadata: dict[str, Any],
) -> None:
    """Update the user_profiles table with the new metadata."""
    try:
        profiles_url = f"{base_url}/rest/v1/user_profiles?id=eq.{user_id}"

        # Build update payload - only include fields that exist in user_profiles
        update_payload: dict[str, Any] = {}
        if "full_name" in user_metadata:
            update_payload["full_name"] = user_metadata["full_name"]

        if not update_payload:
            return

        response = await client.patch(
            profiles_url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=update_payload,
        )
        response.raise_for_status()
        logger.info(f"Updated user_profiles table for {user_id}")
    except Exception as e:
        # Log but don't fail - user_profiles update is secondary
        logger.warning(f"Failed to update user_profiles table: {e}")


async def get_user_role_from_profiles(user_id: str) -> str | None:
    """
    Fetch user role from the user_profiles table in Supabase.

    This is used as a fallback when the role is not in app_metadata or user_metadata.

    Args:
        user_id: The user's UUID

    Returns:
        Role string or None if not found
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None

    base_url = SUPABASE_URL.rstrip("/")
    url = f"{base_url}/rest/v1/user_profiles?id=eq.{user_id}&select=role"

    try:
        from src.core.http_client import get_http_client

        client = get_http_client()
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
        )
        response.raise_for_status()
        data = response.json()
        if data and len(data) > 0:
            role = data[0].get("role")
            if role:
                logger.debug(f"Found role '{role}' in user_profiles for {user_id}")
                return str(role)
    except Exception as e:
        logger.debug(f"Failed to fetch role from user_profiles: {e}")

    return None


async def sync_role_to_app_metadata(user_id: str, role: str) -> bool:
    """
    Sync a user's role to their app_metadata in Supabase Auth.

    This ensures future JWT tokens will contain the correct role.

    Args:
        user_id: The user's UUID
        role: The role to set (e.g., 'admin', 'premium', 'free')

    Returns:
        True if successful, False otherwise
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase admin credentials not configured")
        return False

    base_url = SUPABASE_URL.rstrip("/")
    auth_url = f"{base_url}/auth/v1/admin/users/{user_id}"

    try:
        from src.core.http_client import get_http_client

        client = get_http_client()
        response = await client.put(
            auth_url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": "application/json",
            },
            json={"app_metadata": {"role": role}},
        )
        response.raise_for_status()
        logger.info(f"Synced role '{role}' to app_metadata for user {user_id}")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to sync role to app_metadata: {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Error syncing role to app_metadata: {e}")
        return False
