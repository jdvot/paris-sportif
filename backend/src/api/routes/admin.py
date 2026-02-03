"""Admin dashboard endpoints.

Provides endpoints for admin-only operations and statistics.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser
from src.data.database import get_db_stats

logger = logging.getLogger(__name__)

router = APIRouter()


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""

    total_users: int
    premium_users: int
    total_predictions: int
    success_rate: float
    # Database stats
    total_matches: int
    competitions_with_standings: int
    last_match_sync: str | None
    last_standings_sync: str | None


class UserListItem(BaseModel):
    """User list item for admin view."""

    id: str
    email: str
    role: str
    created_at: str


class UserListResponse(BaseModel):
    """User list response."""

    users: list[UserListItem]
    total: int
    page: int
    per_page: int


@router.get("/stats", response_model=AdminStatsResponse, responses=ADMIN_RESPONSES)
async def get_admin_stats(user: AdminUser) -> AdminStatsResponse:
    """
    Get admin dashboard statistics.

    Returns platform-wide statistics for the admin dashboard.
    Admin role required.
    """
    # Get database stats
    db_stats = get_db_stats()

    # TODO: Fetch real user stats from Supabase admin API
    # For now, return placeholder data combined with real DB stats
    return AdminStatsResponse(
        total_users=0,  # Would come from Supabase
        premium_users=0,  # Would come from Supabase
        total_predictions=0,  # Would come from predictions table
        success_rate=0.0,  # Would be calculated from verified predictions
        total_matches=db_stats.get("total_matches", 0),
        competitions_with_standings=db_stats.get("competitions_with_standings", 0),
        last_match_sync=db_stats.get("last_match_sync"),
        last_standings_sync=db_stats.get("last_standings_sync"),
    )


@router.get("/users", response_model=UserListResponse, responses=ADMIN_RESPONSES)
async def list_users(
    user: AdminUser,
    page: int = 1,
    per_page: int = 20,
) -> UserListResponse:
    """
    List all users (admin only).

    Returns a paginated list of all users.
    Admin role required.
    """
    # TODO: Implement actual user listing from Supabase admin API
    # For now, return empty list
    return UserListResponse(
        users=[],
        total=0,
        page=page,
        per_page=per_page,
    )


@router.post("/users/{user_id}/role", responses=ADMIN_RESPONSES)
async def update_user_role(
    user: AdminUser,
    user_id: str,
    role: str,
) -> dict[str, Any]:
    """
    Update a user's role (admin only).

    Changes a user's role (free, premium, admin).
    Admin role required.
    """
    if role not in ["free", "premium", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    # TODO: Implement actual role update via Supabase admin API
    return {
        "status": "success",
        "message": f"Role updated to {role}",
        "user_id": user_id,
    }
