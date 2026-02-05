"""User profile endpoints.

Provides endpoints for user profile management.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.auth.supabase_auth import update_user_metadata

logger = logging.getLogger(__name__)

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str | None
    full_name: str | None
    role: str
    created_at: str | None


class UserProfileUpdate(BaseModel):
    """User profile update request."""

    full_name: str | None = None


class UserStatsResponse(BaseModel):
    """User statistics response."""

    total_predictions_viewed: int = 0
    favorite_competition: str | None = None
    member_since_days: int = 0


@router.get("/me", response_model=UserProfileResponse, responses=AUTH_RESPONSES)
async def get_current_profile(user: AuthenticatedUser) -> UserProfileResponse:
    """
    Get current user's profile.

    Returns the authenticated user's profile information.
    Fetches fresh data from Supabase to reflect recent updates.
    """
    from src.auth.supabase_auth import get_user_from_supabase

    user_id = user.get("sub", "")

    # Try to get fresh user data from Supabase
    fresh_user = await get_user_from_supabase(user_id)

    if fresh_user:
        user_metadata = fresh_user.get("user_metadata", {})
        app_metadata = fresh_user.get("app_metadata", {})
        email = fresh_user.get("email")
        created_at = fresh_user.get("created_at")
    else:
        # Fallback to JWT data if Supabase fetch fails
        user_metadata = user.get("user_metadata", {})
        app_metadata = user.get("app_metadata", {})
        email = user.get("email")
        created_at = user.get("created_at")

    # Get role from app_metadata first, then user_metadata, default to "free"
    role = app_metadata.get("role") or user_metadata.get("role") or "free"

    return UserProfileResponse(
        id=user_id,
        email=email,
        full_name=user_metadata.get("full_name"),
        role=role,
        created_at=created_at,
    )


@router.patch("/me", response_model=UserProfileResponse, responses=AUTH_RESPONSES)
async def update_profile(
    user: AuthenticatedUser,
    updates: UserProfileUpdate,
) -> UserProfileResponse:
    """
    Update current user's profile.

    Persists changes to Supabase user metadata.
    """
    user_id = user.get("sub", "")
    user_metadata = user.get("user_metadata", {}).copy()
    app_metadata = user.get("app_metadata", {})

    # Build metadata updates
    metadata_updates: dict[str, str | None] = {}
    if updates.full_name is not None:
        metadata_updates["full_name"] = updates.full_name
        user_metadata["full_name"] = updates.full_name

    # Persist to Supabase if there are updates
    if metadata_updates and user_id:
        result = await update_user_metadata(user_id, metadata_updates)
        if result is None:
            logger.warning(f"Failed to persist profile update for user {user_id}")
            raise HTTPException(
                status_code=500,
                detail="Impossible de sauvegarder les modifications du profil",
            )
        logger.info(f"Profile updated for user {user_id}")

    role = app_metadata.get("role") or user_metadata.get("role") or "free"

    return UserProfileResponse(
        id=user_id,
        email=user.get("email"),
        full_name=user_metadata.get("full_name"),
        role=role,
        created_at=user.get("created_at"),
    )


@router.get("/me/stats", response_model=UserStatsResponse, responses=AUTH_RESPONSES)
async def get_user_stats(user: AuthenticatedUser) -> UserStatsResponse:
    """
    Get current user's usage statistics.

    Returns statistics about the user's activity on the platform.
    """
    # In a real implementation, this would fetch from database
    # For now, return placeholder data
    return UserStatsResponse(
        total_predictions_viewed=0,
        favorite_competition=None,
        member_since_days=0,
    )
