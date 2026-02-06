"""Tennis endpoints.

Provides access to tennis matches, players, and tournaments data.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.db.database import get_session
from src.db.models import TennisMatch, TennisPlayer, TennisTournament

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class TennisPlayerResponse(BaseModel):
    """Tennis player response."""

    id: int
    name: str
    country: str | None = None
    photo_url: str | None = None
    circuit: str
    atp_ranking: int | None = None
    wta_ranking: int | None = None
    elo_hard: float
    elo_clay: float
    elo_grass: float
    elo_indoor: float
    win_rate_ytd: float | None = None


class TennisTournamentResponse(BaseModel):
    """Tennis tournament response."""

    id: int
    name: str
    category: str
    surface: str
    country: str | None = None
    circuit: str


class TennisMatchResponse(BaseModel):
    """Tennis match response."""

    id: int
    player1: TennisPlayerResponse
    player2: TennisPlayerResponse
    tournament: TennisTournamentResponse
    round: str | None = None
    match_date: str
    surface: str
    status: str
    winner_id: int | None = None
    score: str | None = None
    sets_player1: int | None = None
    sets_player2: int | None = None
    odds_player1: float | None = None
    odds_player2: float | None = None
    pred_player1_prob: float | None = None
    pred_player2_prob: float | None = None
    pred_confidence: float | None = None
    pred_explanation: str | None = None


class TennisMatchListResponse(BaseModel):
    """List of tennis matches response."""

    matches: list[TennisMatchResponse]
    count: int


class TennisPlayerListResponse(BaseModel):
    """List of tennis players response."""

    players: list[TennisPlayerResponse]
    count: int


class TennisTournamentListResponse(BaseModel):
    """List of tennis tournaments response."""

    tournaments: list[TennisTournamentResponse]
    count: int


# ============================================================================
# Helper Functions
# ============================================================================


def _player_to_response(player: TennisPlayer) -> TennisPlayerResponse:
    """Convert a TennisPlayer model to response."""
    return TennisPlayerResponse(
        id=player.id,
        name=player.name,
        country=player.country,
        photo_url=player.photo_url,
        circuit=player.circuit,
        atp_ranking=player.atp_ranking,
        wta_ranking=player.wta_ranking,
        elo_hard=float(player.elo_hard),
        elo_clay=float(player.elo_clay),
        elo_grass=float(player.elo_grass),
        elo_indoor=float(player.elo_indoor),
        win_rate_ytd=float(player.win_rate_ytd) if player.win_rate_ytd is not None else None,
    )


def _tournament_to_response(tournament: TennisTournament) -> TennisTournamentResponse:
    """Convert a TennisTournament model to response."""
    return TennisTournamentResponse(
        id=tournament.id,
        name=tournament.name,
        category=tournament.category,
        surface=tournament.surface,
        country=tournament.country,
        circuit=tournament.circuit,
    )


def _match_to_response(match: TennisMatch) -> TennisMatchResponse:
    """Convert a TennisMatch model to response."""
    return TennisMatchResponse(
        id=match.id,
        player1=_player_to_response(match.player1),
        player2=_player_to_response(match.player2),
        tournament=_tournament_to_response(match.tournament),
        round=match.round,
        match_date=match.match_date.isoformat(),
        surface=match.surface,
        status=match.status,
        winner_id=match.winner_id,
        score=match.score,
        sets_player1=match.sets_player1,
        sets_player2=match.sets_player2,
        odds_player1=float(match.odds_player1) if match.odds_player1 is not None else None,
        odds_player2=float(match.odds_player2) if match.odds_player2 is not None else None,
        pred_player1_prob=(
            float(match.pred_player1_prob) if match.pred_player1_prob is not None else None
        ),
        pred_player2_prob=(
            float(match.pred_player2_prob) if match.pred_player2_prob is not None else None
        ),
        pred_confidence=(
            float(match.pred_confidence) if match.pred_confidence is not None else None
        ),
        pred_explanation=match.pred_explanation,
    )


# ============================================================================
# Match Endpoints
# ============================================================================


@router.get("/matches", response_model=TennisMatchListResponse)
async def get_tennis_matches(
    circuit: str | None = Query(None, description="Filter by circuit (ATP, WTA)"),
    surface: str | None = Query(None, description="Filter by surface (hard, clay, grass, indoor)"),
    tournament_id: int | None = Query(None, description="Filter by tournament ID"),
    status: str | None = Query(None, description="Filter by status (scheduled, live, finished)"),
    date_from: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
) -> TennisMatchListResponse:
    """
    List tennis matches with optional filters.

    Supports filtering by circuit, surface, tournament, status, and date range.
    Returns matches ordered by date descending.
    """
    async with get_session() as session:
        stmt = (
            select(TennisMatch)
            .options(
                joinedload(TennisMatch.player1),
                joinedload(TennisMatch.player2),
                joinedload(TennisMatch.tournament),
            )
            .order_by(TennisMatch.match_date.desc())
            .limit(limit)
        )

        if circuit:
            stmt = stmt.join(TennisMatch.tournament).where(
                TennisTournament.circuit == circuit.upper()
            )

        if surface:
            stmt = stmt.where(TennisMatch.surface == surface.lower())

        if tournament_id:
            stmt = stmt.where(TennisMatch.tournament_id == tournament_id)

        if status:
            stmt = stmt.where(TennisMatch.status == status.lower())

        if date_from:
            stmt = stmt.where(TennisMatch.match_date >= date_from.isoformat())

        if date_to:
            end = date_to + timedelta(days=1)
            stmt = stmt.where(TennisMatch.match_date < end.isoformat())

        result = await session.execute(stmt)
        matches = result.unique().scalars().all()

    items = [_match_to_response(m) for m in matches]
    return TennisMatchListResponse(matches=items, count=len(items))


@router.get("/matches/{match_id}", response_model=TennisMatchResponse)
async def get_tennis_match(match_id: int) -> TennisMatchResponse:
    """
    Get a single tennis match by ID.

    Returns full match details including players, tournament, and prediction data.
    """
    async with get_session() as session:
        stmt = (
            select(TennisMatch)
            .options(
                joinedload(TennisMatch.player1),
                joinedload(TennisMatch.player2),
                joinedload(TennisMatch.tournament),
            )
            .where(TennisMatch.id == match_id)
        )
        result = await session.execute(stmt)
        match = result.unique().scalars().first()

    if not match:
        raise HTTPException(status_code=404, detail=f"Tennis match {match_id} not found")

    return _match_to_response(match)


# ============================================================================
# Player Endpoints
# ============================================================================


@router.get("/players", response_model=TennisPlayerListResponse)
async def get_tennis_players(
    circuit: str | None = Query(None, description="Filter by circuit (ATP, WTA)"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
) -> TennisPlayerListResponse:
    """
    List tennis players with optional circuit filter.

    Returns players ordered by ranking (ATP or WTA depending on circuit).
    """
    async with get_session() as session:
        stmt = select(TennisPlayer).limit(limit)

        if circuit:
            stmt = stmt.where(TennisPlayer.circuit == circuit.upper())

        # Order by ranking within their circuit
        stmt = stmt.order_by(
            TennisPlayer.atp_ranking.asc().nullslast(),
            TennisPlayer.wta_ranking.asc().nullslast(),
            TennisPlayer.name.asc(),
        )

        result = await session.execute(stmt)
        players = result.scalars().all()

    items = [_player_to_response(p) for p in players]
    return TennisPlayerListResponse(players=items, count=len(items))


@router.get("/players/{player_id}", response_model=TennisPlayerResponse)
async def get_tennis_player(player_id: int) -> TennisPlayerResponse:
    """
    Get a single tennis player by ID.

    Returns full player details including ELO ratings per surface.
    """
    async with get_session() as session:
        stmt = select(TennisPlayer).where(TennisPlayer.id == player_id)
        result = await session.execute(stmt)
        player = result.scalars().first()

    if not player:
        raise HTTPException(status_code=404, detail=f"Tennis player {player_id} not found")

    return _player_to_response(player)


# ============================================================================
# Tournament Endpoints
# ============================================================================


@router.get("/tournaments", response_model=TennisTournamentListResponse)
async def get_tennis_tournaments(
    circuit: str | None = Query(None, description="Filter by circuit (ATP, WTA)"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
) -> TennisTournamentListResponse:
    """
    List tennis tournaments with optional circuit filter.

    Returns tournaments ordered by start date descending.
    """
    async with get_session() as session:
        stmt = (
            select(TennisTournament)
            .order_by(TennisTournament.start_date.desc().nullslast())
            .limit(limit)
        )

        if circuit:
            stmt = stmt.where(TennisTournament.circuit == circuit.upper())

        result = await session.execute(stmt)
        tournaments = result.scalars().all()

    items = [_tournament_to_response(t) for t in tournaments]
    return TennisTournamentListResponse(tournaments=items, count=len(items))
