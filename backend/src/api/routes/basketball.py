"""Basketball endpoints."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from src.db.database import get_session
from src.db.models import BasketballMatch, BasketballTeam

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class BasketballTeamResponse(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    country: str | None = None
    logo_url: str | None = None
    league: str
    elo_rating: float
    offensive_rating: float | None = None
    defensive_rating: float | None = None
    pace: float | None = None
    win_rate_ytd: float | None = None


class BasketballMatchResponse(BaseModel):
    id: int
    home_team: BasketballTeamResponse
    away_team: BasketballTeamResponse
    league: str
    match_date: str
    status: str
    # Scores
    home_score: int | None = None
    away_score: int | None = None
    home_q1: int | None = None
    away_q1: int | None = None
    home_q2: int | None = None
    away_q2: int | None = None
    home_q3: int | None = None
    away_q3: int | None = None
    home_q4: int | None = None
    away_q4: int | None = None
    # Odds
    odds_home: float | None = None
    odds_away: float | None = None
    spread: float | None = None
    over_under: float | None = None
    # Prediction
    pred_home_prob: float | None = None
    pred_away_prob: float | None = None
    pred_confidence: float | None = None
    pred_explanation: str | None = None
    is_back_to_back_home: bool = False
    is_back_to_back_away: bool = False


class BasketballMatchListResponse(BaseModel):
    matches: list[BasketballMatchResponse]
    count: int


class BasketballTeamListResponse(BaseModel):
    teams: list[BasketballTeamResponse]
    count: int


class BasketballStandingEntry(BaseModel):
    team: BasketballTeamResponse
    wins: int
    losses: int
    win_rate: float | None = None
    conference: str | None = None
    division: str | None = None


class BasketballStandingsResponse(BaseModel):
    league: str
    standings: list[BasketballStandingEntry]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _team_to_response(team: BasketballTeam) -> BasketballTeamResponse:
    """Convert a BasketballTeam ORM instance to a response model."""
    return BasketballTeamResponse(
        id=team.id,
        name=team.name,
        short_name=team.short_name,
        country=team.country,
        logo_url=team.logo_url,
        league=team.league,
        elo_rating=float(team.elo_rating),
        offensive_rating=float(team.offensive_rating) if team.offensive_rating else None,
        defensive_rating=float(team.defensive_rating) if team.defensive_rating else None,
        pace=float(team.pace) if team.pace else None,
        win_rate_ytd=float(team.win_rate_ytd) if team.win_rate_ytd else None,
    )


def _match_to_response(match: BasketballMatch) -> BasketballMatchResponse:
    """Convert a BasketballMatch ORM instance to a response model."""
    return BasketballMatchResponse(
        id=match.id,
        home_team=_team_to_response(match.home_team),
        away_team=_team_to_response(match.away_team),
        league=match.league,
        match_date=match.match_date.isoformat(),
        status=match.status,
        home_score=match.home_score,
        away_score=match.away_score,
        home_q1=match.home_q1,
        away_q1=match.away_q1,
        home_q2=match.home_q2,
        away_q2=match.away_q2,
        home_q3=match.home_q3,
        away_q3=match.away_q3,
        home_q4=match.home_q4,
        away_q4=match.away_q4,
        odds_home=float(match.odds_home) if match.odds_home else None,
        odds_away=float(match.odds_away) if match.odds_away else None,
        spread=float(match.spread) if match.spread else None,
        over_under=float(match.over_under) if match.over_under else None,
        pred_home_prob=float(match.pred_home_prob) if match.pred_home_prob else None,
        pred_away_prob=float(match.pred_away_prob) if match.pred_away_prob else None,
        pred_confidence=float(match.pred_confidence) if match.pred_confidence else None,
        pred_explanation=match.pred_explanation,
        is_back_to_back_home=match.is_back_to_back_home,
        is_back_to_back_away=match.is_back_to_back_away,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/matches", response_model=BasketballMatchListResponse)
async def list_basketball_matches(
    league: str | None = Query(None, description="Filter by league (NBA, EUROLEAGUE)"),
    status: str | None = Query(None, description="Filter by status (scheduled, live, finished)"),
    date_from: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> BasketballMatchListResponse:
    """List basketball matches with optional filters."""
    async with get_session() as session:
        stmt = (
            select(BasketballMatch)
            .options(
                joinedload(BasketballMatch.home_team),
                joinedload(BasketballMatch.away_team),
            )
            .order_by(BasketballMatch.match_date.desc())
        )

        if league:
            stmt = stmt.where(BasketballMatch.league == league.upper())
        if status:
            stmt = stmt.where(BasketballMatch.status == status.lower())
        if date_from:
            stmt = stmt.where(BasketballMatch.match_date >= date_from.isoformat())
        if date_to:
            end = date_to + timedelta(days=1)
            stmt = stmt.where(BasketballMatch.match_date < end.isoformat())

        # Total count (without pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        matches = result.scalars().unique().all()

        return BasketballMatchListResponse(
            matches=[_match_to_response(m) for m in matches],
            count=total,
        )


@router.get("/matches/{match_id}", response_model=BasketballMatchResponse)
async def get_basketball_match(match_id: int) -> BasketballMatchResponse:
    """Get a single basketball match by ID."""
    async with get_session() as session:
        stmt = (
            select(BasketballMatch)
            .options(
                joinedload(BasketballMatch.home_team),
                joinedload(BasketballMatch.away_team),
            )
            .where(BasketballMatch.id == match_id)
        )
        result = await session.execute(stmt)
        match = result.scalars().unique().one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail="Basketball match not found")

        return _match_to_response(match)


@router.get("/teams", response_model=BasketballTeamListResponse)
async def list_basketball_teams(
    league: str | None = Query(None, description="Filter by league (NBA, EUROLEAGUE)"),
    conference: str | None = Query(None, description="Filter by conference (East, West)"),
) -> BasketballTeamListResponse:
    """List basketball teams with optional filters."""
    async with get_session() as session:
        stmt = select(BasketballTeam).order_by(BasketballTeam.name)

        if league:
            stmt = stmt.where(BasketballTeam.league == league.upper())
        if conference:
            stmt = stmt.where(BasketballTeam.conference == conference)

        result = await session.execute(stmt)
        teams = result.scalars().all()

        return BasketballTeamListResponse(
            teams=[_team_to_response(t) for t in teams],
            count=len(teams),
        )


@router.get("/teams/{team_id}", response_model=BasketballTeamResponse)
async def get_basketball_team(team_id: int) -> BasketballTeamResponse:
    """Get a single basketball team by ID."""
    async with get_session() as session:
        stmt = select(BasketballTeam).where(BasketballTeam.id == team_id)
        result = await session.execute(stmt)
        team = result.scalars().one_or_none()

        if not team:
            raise HTTPException(status_code=404, detail="Basketball team not found")

        return _team_to_response(team)


@router.get("/standings", response_model=BasketballStandingsResponse)
async def get_basketball_standings(
    league: str = Query("NBA", description="League (NBA, EUROLEAGUE)"),
    conference: str | None = Query(None, description="Conference filter (East, West)"),
) -> BasketballStandingsResponse:
    """Get basketball standings by league."""
    async with get_session() as session:
        stmt = select(BasketballTeam).where(BasketballTeam.league == league.upper())

        if conference:
            stmt = stmt.where(BasketballTeam.conference == conference)

        # Order by win rate descending, then wins descending
        stmt = stmt.order_by(
            BasketballTeam.win_rate_ytd.desc().nullslast(),
            BasketballTeam.wins.desc(),
        )

        result = await session.execute(stmt)
        teams = result.scalars().all()

        standings = [
            BasketballStandingEntry(
                team=_team_to_response(t),
                wins=t.wins,
                losses=t.losses,
                win_rate=float(t.win_rate_ytd) if t.win_rate_ytd else None,
                conference=t.conference,
                division=t.division,
            )
            for t in teams
        ]

        return BasketballStandingsResponse(
            league=league.upper(),
            standings=standings,
        )
