"""Match endpoints."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class TeamInfo(BaseModel):
    """Team information in a match."""

    id: int
    name: str
    short_name: str
    logo_url: str | None = None
    elo_rating: float = 1500.0


class MatchResponse(BaseModel):
    """Match response model."""

    id: int
    external_id: str
    home_team: TeamInfo
    away_team: TeamInfo
    competition: str
    competition_code: str
    match_date: datetime
    status: Literal["scheduled", "live", "finished", "postponed"]
    home_score: int | None = None
    away_score: int | None = None
    matchday: int | None = None


class MatchListResponse(BaseModel):
    """List of matches response."""

    matches: list[MatchResponse]
    total: int
    page: int
    per_page: int


class TeamFormResponse(BaseModel):
    """Team recent form response."""

    team_id: int
    team_name: str
    last_matches: list[dict]
    form_string: str  # e.g., "WWDLW"
    points_last_5: int
    goals_scored_avg: float
    goals_conceded_avg: float
    clean_sheets: int
    xg_for_avg: float | None = None
    xg_against_avg: float | None = None


@router.get("", response_model=MatchListResponse)
async def get_matches(
    competition: str | None = Query(None, description="Filter by competition code (e.g., PL, PD, BL1)"),
    date_from: date | None = Query(None, description="Start date filter"),
    date_to: date | None = Query(None, description="End date filter"),
    status: Literal["scheduled", "live", "finished"] | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> MatchListResponse:
    """
    Get list of matches with optional filters.

    Competition codes:
    - PL: Premier League
    - PD: La Liga
    - BL1: Bundesliga
    - SA: Serie A
    - FL1: Ligue 1
    - CL: Champions League
    - EL: Europa League
    """
    # TODO: Implement database query
    return MatchListResponse(
        matches=[],
        total=0,
        page=page,
        per_page=per_page,
    )


@router.get("/upcoming")
async def get_upcoming_matches(
    days: int = Query(2, ge=1, le=7, description="Number of days ahead"),
    competition: str | None = Query(None),
) -> MatchListResponse:
    """Get upcoming matches for the next N days."""
    # TODO: Implement
    return MatchListResponse(
        matches=[],
        total=0,
        page=1,
        per_page=50,
    )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int) -> MatchResponse:
    """Get details for a specific match."""
    # TODO: Implement database query
    raise NotImplementedError("Match detail not implemented yet")


@router.get("/{match_id}/head-to-head")
async def get_head_to_head(
    match_id: int,
    limit: int = Query(10, ge=1, le=20),
) -> dict:
    """Get head-to-head history for teams in a match."""
    # TODO: Implement
    return {
        "matches": [],
        "home_wins": 0,
        "draws": 0,
        "away_wins": 0,
        "avg_goals": 0.0,
    }


@router.get("/teams/{team_id}/form", response_model=TeamFormResponse)
async def get_team_form(
    team_id: int,
    matches_count: int = Query(5, ge=3, le=10),
) -> TeamFormResponse:
    """Get recent form for a team."""
    # TODO: Implement
    return TeamFormResponse(
        team_id=team_id,
        team_name="Unknown",
        last_matches=[],
        form_string="",
        points_last_5=0,
        goals_scored_avg=0.0,
        goals_conceded_avg=0.0,
        clean_sheets=0,
    )
