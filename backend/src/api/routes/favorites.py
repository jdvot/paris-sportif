"""User favorites and preferences endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.db.services.user_service import FavoriteService, PreferencesService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Models
# ============================================================================


class FavoriteCreate(BaseModel):
    """Add a favorite pick."""

    match_id: int
    prediction_id: int | None = None
    note: str | None = Field(None, max_length=500)
    notify_before_match: bool = True


class FavoriteResponse(BaseModel):
    """Favorite response."""

    id: int
    match_id: int
    prediction_id: int | None
    note: str | None
    notify_before_match: bool
    created_at: str
    # Match details (from join)
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None


class FavoriteListResponse(BaseModel):
    """List of favorites."""

    favorites: list[FavoriteResponse]
    total: int


class PreferencesUpdate(BaseModel):
    """Update user preferences."""

    language: str | None = Field(None, pattern="^(fr|en|nl)$")
    timezone: str | None = None
    odds_format: str | None = Field(None, pattern="^(decimal|fractional|american)$")
    dark_mode: bool | None = None
    email_daily_picks: bool | None = None
    email_match_results: bool | None = None
    push_daily_picks: bool | None = None
    push_match_start: bool | None = None
    push_bet_results: bool | None = None
    default_stake: float | None = Field(None, gt=0)
    risk_level: str | None = Field(None, pattern="^(low|medium|high)$")
    favorite_competitions: list[str] | None = None


class PreferencesResponse(BaseModel):
    """User preferences."""

    language: str
    timezone: str
    odds_format: str
    dark_mode: bool
    email_daily_picks: bool
    email_match_results: bool
    push_daily_picks: bool
    push_match_start: bool
    push_bet_results: bool
    default_stake: float
    risk_level: str
    favorite_competitions: list[str]


# ============================================================================
# Favorites endpoints
# ============================================================================


@router.post("/favorites", response_model=FavoriteResponse, responses=AUTH_RESPONSES)
async def add_favorite(user: AuthenticatedUser, favorite: FavoriteCreate) -> FavoriteResponse:
    """Add a pick to favorites."""
    user_id = user.get("sub", "")

    try:
        result = await FavoriteService.add_favorite(
            user_id=user_id,
            match_id=favorite.match_id,
            prediction_id=favorite.prediction_id,
            note=favorite.note,
            notify_before_match=favorite.notify_before_match,
        )
        return FavoriteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/favorites", response_model=FavoriteListResponse, responses=AUTH_RESPONSES)
async def list_favorites(
    user: AuthenticatedUser,
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=50, le=100, description="Max items to return"),
) -> FavoriteListResponse:
    """List user's favorite picks with match details."""
    user_id = user.get("sub", "")

    favorites = await FavoriteService.list_favorites(user_id, limit=limit, offset=offset)
    return FavoriteListResponse(
        favorites=[FavoriteResponse(**f) for f in favorites],
        total=len(favorites),
    )


@router.delete("/favorites/{match_id}", responses=AUTH_RESPONSES)
async def remove_favorite(user: AuthenticatedUser, match_id: int) -> dict[str, Any]:
    """Remove a pick from favorites."""
    user_id = user.get("sub", "")

    deleted = await FavoriteService.remove_favorite(user_id, match_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite not found")

    return {"status": "removed", "match_id": match_id}


# ============================================================================
# Preferences endpoints
# ============================================================================


@router.get("/preferences", response_model=PreferencesResponse, responses=AUTH_RESPONSES)
async def get_preferences(user: AuthenticatedUser) -> PreferencesResponse:
    """Get user preferences."""
    user_id = user.get("sub", "")

    prefs = await PreferencesService.get_preferences(user_id)
    return PreferencesResponse(**prefs)


@router.put("/preferences", response_model=PreferencesResponse, responses=AUTH_RESPONSES)
async def update_preferences(
    user: AuthenticatedUser, prefs: PreferencesUpdate
) -> PreferencesResponse:
    """Update user preferences."""
    user_id = user.get("sub", "")

    # Convert Pydantic model to dict, excluding None values
    update_data = prefs.model_dump(exclude_none=True)

    result = await PreferencesService.update_preferences(user_id, **update_data)
    return PreferencesResponse(**result)
