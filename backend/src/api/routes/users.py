"""User profile endpoints.

Provides endpoints for user profile management.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser

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
    """
    user_metadata = user.get("user_metadata", {})
    app_metadata = user.get("app_metadata", {})

    # Get role from app_metadata first, then user_metadata, default to "free"
    role = app_metadata.get("role") or user_metadata.get("role") or "free"

    return UserProfileResponse(
        id=user.get("sub", ""),
        email=user.get("email"),
        full_name=user_metadata.get("full_name"),
        role=role,
        created_at=user.get("created_at"),
    )


@router.patch("/me", response_model=UserProfileResponse, responses=AUTH_RESPONSES)
async def update_profile(
    user: AuthenticatedUser,
    updates: UserProfileUpdate,
) -> UserProfileResponse:
    """
    Update current user's profile.

    Note: This only updates local cache. For persistent changes,
    use Supabase client directly from the frontend.
    """
    # In a real implementation, this would update the Supabase user
    # For now, we just return the current profile with the updates applied
    user_metadata = user.get("user_metadata", {})
    app_metadata = user.get("app_metadata", {})

    # Apply updates to metadata
    if updates.full_name is not None:
        user_metadata["full_name"] = updates.full_name

    role = app_metadata.get("role") or user_metadata.get("role") or "free"

    return UserProfileResponse(
        id=user.get("sub", ""),
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
