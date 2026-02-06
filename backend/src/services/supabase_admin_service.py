"""Supabase Admin API service for user management.

Fetches user data from the Supabase Admin API using the service_role_key.
Used by admin endpoints to get real user counts and user lists.
"""

import logging
import os
from typing import Any

import httpx

from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _get_admin_headers() -> dict[str, str]:
    """Build headers for Supabase Admin API requests."""
    return {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
    }


def _is_configured() -> bool:
    """Check if Supabase admin credentials are configured."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _base_url() -> str:
    """Get the Supabase base URL without trailing slash."""
    return SUPABASE_URL.rstrip("/")


class SupabaseAdminService:
    """Service for Supabase Admin API operations."""

    @staticmethod
    async def get_user_counts() -> dict[str, Any]:
        """Fetch user counts from Supabase Admin API.

        Paginates through all users to count total and premium users.
        Premium users are those with app_metadata.role in ('premium', 'admin').

        Returns:
            Dict with total_users, premium_users, and warning (if any).
        """
        if not _is_configured():
            logger.warning(
                "Supabase admin credentials not configured - returning 0 for user counts"
            )
            return {
                "total_users": 0,
                "premium_users": 0,
                "warning": "Supabase admin credentials not configured",
            }

        try:
            client = get_http_client()
            base = _base_url()
            total_users = 0
            premium_users = 0
            page = 1
            per_page = 100  # Supabase max per page

            while True:
                url = f"{base}/auth/v1/admin/users"
                response = await client.get(
                    url,
                    headers=_get_admin_headers(),
                    params={"page": page, "per_page": per_page},
                )
                response.raise_for_status()
                data = response.json()

                users = data.get("users", [])
                if not users:
                    break

                total_users += len(users)

                for user in users:
                    app_metadata = user.get("app_metadata", {})
                    role = app_metadata.get("role", "free")
                    if role in ("premium", "admin"):
                        premium_users += 1

                # If we got fewer than per_page, we've reached the last page
                if len(users) < per_page:
                    break

                page += 1

            return {
                "total_users": total_users,
                "premium_users": premium_users,
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Supabase Admin API HTTP error: {e.response.status_code} - "
                f"{e.response.text[:200]}"
            )
            return {
                "total_users": 0,
                "premium_users": 0,
                "warning": f"Supabase Admin API error: {e.response.status_code}",
            }
        except Exception as e:
            logger.error(f"Failed to fetch user counts from Supabase: {e}")
            return {
                "total_users": 0,
                "premium_users": 0,
                "warning": f"Supabase Admin API error: {str(e)}",
            }

    @staticmethod
    async def list_users(
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Fetch a paginated list of users from Supabase Admin API.

        Args:
            page: Page number (1-indexed).
            per_page: Number of users per page.

        Returns:
            Dict with users list, total count, page, and per_page.
        """
        if not _is_configured():
            logger.warning("Supabase admin credentials not configured")
            return {
                "users": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "warning": "Supabase admin credentials not configured",
            }

        try:
            client = get_http_client()
            base = _base_url()
            url = f"{base}/auth/v1/admin/users"

            response = await client.get(
                url,
                headers=_get_admin_headers(),
                params={"page": page, "per_page": per_page},
            )
            response.raise_for_status()
            data = response.json()

            users_raw = data.get("users", [])

            users = []
            for u in users_raw:
                app_metadata = u.get("app_metadata", {})
                user_metadata = u.get("user_metadata", {})
                role = app_metadata.get("role") or user_metadata.get("role") or "free"

                users.append(
                    {
                        "id": u.get("id", ""),
                        "email": u.get("email", ""),
                        "role": str(role),
                        "created_at": u.get("created_at", ""),
                    }
                )

            # Supabase returns total count in the response (aud field varies)
            # We need to get total from a separate count or from pagination info
            # The /admin/users endpoint returns total in the response body
            total = data.get("total", len(users_raw))

            return {
                "users": users,
                "total": total,
                "page": page,
                "per_page": per_page,
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Supabase Admin API HTTP error listing users: " f"{e.response.status_code}"
            )
            return {
                "users": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "warning": f"Supabase Admin API error: {e.response.status_code}",
            }
        except Exception as e:
            logger.error(f"Failed to list users from Supabase: {e}")
            return {
                "users": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "warning": f"Supabase Admin API error: {str(e)}",
            }

    @staticmethod
    async def update_user_role(user_id: str, role: str) -> dict[str, Any]:
        """Update a user's role via Supabase Admin API.

        Sets the role in app_metadata so it will be included in future JWTs.

        Args:
            user_id: The user's UUID.
            role: The new role ('free', 'premium', 'admin').

        Returns:
            Dict with status, message, and user_id.
        """
        if not _is_configured():
            logger.warning("Supabase admin credentials not configured")
            return {
                "status": "error",
                "message": "Supabase admin credentials not configured",
                "user_id": user_id,
            }

        try:
            client = get_http_client()
            base = _base_url()
            url = f"{base}/auth/v1/admin/users/{user_id}"

            response = await client.put(
                url,
                headers=_get_admin_headers(),
                json={"app_metadata": {"role": role}},
            )
            response.raise_for_status()

            logger.info(f"Updated role to '{role}' for user {user_id}")
            return {
                "status": "success",
                "message": f"Role updated to {role}",
                "user_id": user_id,
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to update user role via Supabase: "
                f"{e.response.status_code} - {e.response.text[:200]}"
            )
            return {
                "status": "error",
                "message": f"Supabase API error: {e.response.status_code}",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "user_id": user_id,
            }
