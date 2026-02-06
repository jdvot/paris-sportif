"""Search endpoints - Search teams and matches using PostgreSQL ilike.

Public endpoints (no auth required) for searching teams by name/TLA
and matches by team names.
"""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.db.models import Match, Team
from src.db.repositories import get_uow

router = APIRouter()
logger = logging.getLogger(__name__)

SearchType = Literal["all", "teams", "matches"]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TeamSearchResult(BaseModel):
    """A team returned by search."""

    id: int
    name: str
    short_name: str | None = None
    tla: str | None = None
    country: str | None = None
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class MatchSearchResult(BaseModel):
    """A match returned by search."""

    id: int
    home_team_name: str
    away_team_name: str
    home_team_logo: str | None = None
    away_team_logo: str | None = None
    competition_code: str
    match_date: datetime
    status: str

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Aggregated search results."""

    query: str
    teams: list[TeamSearchResult] = Field(default_factory=list)
    matches: list[MatchSearchResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search teams and matches",
    description=(
        "Search teams by name, short_name or TLA and matches by team names. "
        "Uses PostgreSQL ilike for case-insensitive partial matching."
    ),
)
async def search(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    type: SearchType = Query("all", description="Filter by result type"),
    limit: int = Query(10, ge=1, le=50, description="Max results per category"),
) -> SearchResponse:
    """Search teams and matches."""
    pattern = f"%{q}%"
    teams: list[TeamSearchResult] = []
    matches: list[MatchSearchResult] = []

    async with get_uow() as uow:
        session = uow.session

        # --- Search teams ---
        if type in ("all", "teams"):
            from sqlalchemy import or_, select

            stmt = (
                select(Team)
                .where(
                    or_(
                        Team.name.ilike(pattern),
                        Team.short_name.ilike(pattern),
                        Team.tla.ilike(pattern),
                    )
                )
                .order_by(Team.name)
                .limit(limit)
            )
            result = await session.execute(stmt)
            for team in result.scalars().all():
                teams.append(
                    TeamSearchResult(
                        id=team.id,
                        name=team.name,
                        short_name=team.short_name,
                        tla=team.tla,
                        country=team.country,
                        logo_url=team.logo_url,
                    )
                )

        # --- Search matches by team names ---
        if type in ("all", "matches"):
            from sqlalchemy import or_, select
            from sqlalchemy.orm import aliased, joinedload

            home = aliased(Team, name="home")
            away = aliased(Team, name="away")

            stmt = (
                select(Match)
                .join(home, Match.home_team_id == home.id)
                .join(away, Match.away_team_id == away.id)
                .where(
                    or_(
                        home.name.ilike(pattern),
                        home.tla.ilike(pattern),
                        away.name.ilike(pattern),
                        away.tla.ilike(pattern),
                    )
                )
                .options(joinedload(Match.home_team), joinedload(Match.away_team))
                .order_by(Match.match_date.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            for match in result.unique().scalars().all():
                matches.append(
                    MatchSearchResult(
                        id=match.id,
                        home_team_name=match.home_team.name,
                        away_team_name=match.away_team.name,
                        home_team_logo=match.home_team.logo_url,
                        away_team_logo=match.away_team.logo_url,
                        competition_code=match.competition_code,
                        match_date=match.match_date,
                        status=match.status,
                    )
                )

    return SearchResponse(query=q, teams=teams, matches=matches)
