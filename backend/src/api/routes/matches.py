"""Match endpoints - Real data from football-data.org API with DB fallback.

All endpoints require authentication.
Returns HTTP errors (429, 503) when data is unavailable rather than mock data.
"""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.core.cache import cache_get, cache_set
from src.core.constants import COMPETITION_NAMES, COMPETITIONS
from src.core.exceptions import FootballDataAPIError, RateLimitError
from src.core.messages import api_msg, detect_language_from_header
from src.core.rate_limit import RATE_LIMITS, limiter
from src.data.sources.football_data import (
    MatchData,
    get_football_data_client,
)
from src.db.services import MatchService, StandingService

router = APIRouter()
logger = logging.getLogger(__name__)

# Type aliases for match status
MatchStatus = Literal["scheduled", "live", "finished", "postponed"]
APIStatus = Literal["SCHEDULED", "LIVE", "FINISHED"]
DataSourceType = Literal["live_api", "cache", "database"]

# Map football-data.org API statuses to our internal status values
STATUS_MAP: dict[str, MatchStatus] = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "LIVE": "live",
    "IN_PLAY": "live",
    "PAUSED": "live",
    "FINISHED": "finished",
    "POSTPONED": "postponed",
    "CANCELLED": "postponed",
    "SUSPENDED": "postponed",
}


def _normalize_status(raw_status: str | None) -> MatchStatus:
    """Normalize a raw status string (from DB or API) to our MatchStatus."""
    if not raw_status:
        return "scheduled"
    return STATUS_MAP.get(raw_status, STATUS_MAP.get(raw_status.upper(), "scheduled"))


class DataSourceInfo(BaseModel):
    """Information about data source and any warnings (Beta feature).

    Distinguishes between:
    - external_api_limited: football-data.org rate limit (10 req/min free tier)
    - app_rate_limited: our API rate limit for user protection
    """

    source: DataSourceType = "live_api"
    is_fallback: bool = False
    warning: str | None = None
    warning_code: str | None = None  # e.g., "EXTERNAL_API_RATE_LIMIT", "STALE_CACHE"
    details: str | None = None
    retry_after_seconds: int | None = None  # When to retry for fresh data


# NOTE: Mock data removed - we only return real data from API or DB
# If both are unavailable, we return HTTP errors with clear messages


class TeamInfo(BaseModel):
    """Team information in a match."""

    id: int
    name: str
    short_name: str
    logo_url: str | None = None
    elo_rating: float | None = None  # Real ELO from DB, None if not found
    form: str | None = None  # Recent form (e.g., "WLDDW")


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
    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class TeamFormMatch(BaseModel):
    """A match in team form history."""

    opponent: str
    result: Literal["W", "D", "L"]
    score: str
    home_away: Literal["H", "A"]
    date: datetime


class TeamFormResponse(BaseModel):
    """Team recent form response."""

    team_id: int
    team_name: str
    last_matches: list[TeamFormMatch]
    form_string: str  # e.g., "WWDLW"
    points_last_5: int
    goals_scored_avg: float
    goals_conceded_avg: float
    clean_sheets: int
    xg_for_avg: float | None = None
    xg_against_avg: float | None = None
    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class StandingTeamResponse(BaseModel):
    """Team standing in league table."""

    position: int
    team_id: int
    team_name: str
    team_logo_url: str | None = None
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class StandingsResponse(BaseModel):
    """League standings response."""

    competition_code: str
    competition_name: str
    standings: list[StandingTeamResponse]
    last_updated: datetime | None = None
    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class HeadToHeadMatch(BaseModel):
    """A match in head-to-head history."""

    date: datetime
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    competition: str


class HeadToHeadResponse(BaseModel):
    """Head-to-head response."""

    matches: list[HeadToHeadMatch]
    home_wins: int
    draws: int
    away_wins: int
    avg_goals: float
    total_matches: int
    # Beta: data source info for transparency
    data_source: DataSourceInfo | None = None


class CompetitionResponse(BaseModel):
    """Single competition info."""

    code: str
    name: str
    country: str
    flag: str


class CompetitionsListResponse(BaseModel):
    """List of supported competitions."""

    competitions: list[CompetitionResponse]
    total: int


# Cache for team data to avoid repeated DB calls (TTL: 10 min, max 200 entries)
_TEAM_CACHE_TTL = 600  # 10 minutes
_TEAM_CACHE_MAX = 200
_team_cache: dict[str, tuple[dict, float]] = {}  # name -> (data, timestamp)


def _clean_team_cache() -> None:
    """Remove expired entries and enforce size limit."""
    import time

    now = time.time()
    # Remove expired
    expired = [k for k, (_, ts) in _team_cache.items() if now - ts > _TEAM_CACHE_TTL]
    for k in expired:
        del _team_cache[k]
    # Enforce max size (remove oldest)
    if len(_team_cache) > _TEAM_CACHE_MAX:
        sorted_keys = sorted(_team_cache, key=lambda k: _team_cache[k][1])
        for k in sorted_keys[: len(_team_cache) - _TEAM_CACHE_MAX]:
            del _team_cache[k]


async def _get_team_from_db(team_name: str) -> dict | None:
    """Fetch real team data from database by name."""
    import time

    now = time.time()

    # Check cache first (with TTL)
    if team_name in _team_cache:
        data, ts = _team_cache[team_name]
        if now - ts < _TEAM_CACHE_TTL:
            return data
        del _team_cache[team_name]

    try:
        from src.db.repositories import get_uow

        async with get_uow() as uow:
            # Try exact match first
            team = await uow.teams.get_by_name(team_name)
            if not team:
                # Try partial match
                team = await uow.teams.get_by_name_fuzzy(team_name)

            if team:
                data = {
                    "elo_rating": float(team.elo_rating) if team.elo_rating else None,
                    "form": team.form,
                }
                _team_cache[team_name] = (data, now)
                # Periodic cleanup
                if len(_team_cache) > _TEAM_CACHE_MAX:
                    _clean_team_cache()
                return data
    except Exception as e:
        logger.debug(f"Could not fetch team {team_name} from DB: {e}")

    return None


async def _convert_api_match_with_db(api_match: MatchData) -> MatchResponse:
    """Convert football-data.org match to our response format with real DB data."""
    # Map API status to our status
    status: MatchStatus = _normalize_status(api_match.status)

    # Extract scores
    home_score = None
    away_score = None
    if api_match.score and api_match.score.fullTime:
        home_score = api_match.score.fullTime.home
        away_score = api_match.score.fullTime.away

    # Fetch real team data from DB
    home_db = await _get_team_from_db(api_match.homeTeam.name)
    away_db = await _get_team_from_db(api_match.awayTeam.name)

    return MatchResponse(
        id=api_match.id,
        external_id=f"{api_match.competition.code}_{api_match.id}",
        home_team=TeamInfo(
            id=api_match.homeTeam.id,
            name=api_match.homeTeam.name,
            short_name=(
                api_match.homeTeam.tla
                or api_match.homeTeam.shortName
                or api_match.homeTeam.name[:3].upper()
            ),
            logo_url=api_match.homeTeam.crest,
            elo_rating=home_db.get("elo_rating") if home_db else None,
            form=home_db.get("form") if home_db else None,
        ),
        away_team=TeamInfo(
            id=api_match.awayTeam.id,
            name=api_match.awayTeam.name,
            short_name=(
                api_match.awayTeam.tla
                or api_match.awayTeam.shortName
                or api_match.awayTeam.name[:3].upper()
            ),
            logo_url=api_match.awayTeam.crest,
            elo_rating=away_db.get("elo_rating") if away_db else None,
            form=away_db.get("form") if away_db else None,
        ),
        competition=api_match.competition.name,
        competition_code=api_match.competition.code,
        match_date=datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00")),
        status=status,
        home_score=home_score,
        away_score=away_score,
        matchday=api_match.matchday,
    )


def _convert_api_match(api_match: MatchData) -> MatchResponse:
    """Convert football-data.org match to our response format."""
    status: MatchStatus = _normalize_status(api_match.status)

    # Extract scores
    home_score = None
    away_score = None
    if api_match.score and api_match.score.fullTime:
        home_score = api_match.score.fullTime.home
        away_score = api_match.score.fullTime.away

    return MatchResponse(
        id=api_match.id,
        external_id=f"{api_match.competition.code}_{api_match.id}",
        home_team=TeamInfo(
            id=api_match.homeTeam.id,
            name=api_match.homeTeam.name,
            short_name=(
                api_match.homeTeam.tla
                or api_match.homeTeam.shortName
                or api_match.homeTeam.name[:3].upper()
            ),
            logo_url=api_match.homeTeam.crest,
        ),
        away_team=TeamInfo(
            id=api_match.awayTeam.id,
            name=api_match.awayTeam.name,
            short_name=(
                api_match.awayTeam.tla
                or api_match.awayTeam.shortName
                or api_match.awayTeam.name[:3].upper()
            ),
            logo_url=api_match.awayTeam.crest,
        ),
        competition=api_match.competition.name,
        competition_code=api_match.competition.code,
        match_date=datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00")),
        status=status,
        home_score=home_score,
        away_score=away_score,
        matchday=api_match.matchday,
    )


@router.get(
    "",
    response_model=MatchListResponse,
    responses=AUTH_RESPONSES,
    operation_id="getMatches",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_matches(
    request: Request,
    user: AuthenticatedUser,
    competition: str | None = Query(None, description="Competition code (PL, PD, BL1)"),
    date_from: date | None = Query(None, description="Start date filter"),
    date_to: date | None = Query(None, description="End date filter"),
    status: Literal["scheduled", "live", "finished"] | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> MatchListResponse:
    """
    Get list of matches with optional filters from database.

    Competition codes:
    - PL: Premier League
    - PD: La Liga
    - BL1: Bundesliga
    - SA: Serie A
    - FL1: Ligue 1
    - CL: Champions League
    - EL: Europa League
    """
    # Default date range if not specified: next 10 days
    if not date_from and not date_to:
        date_from = date.today()
        date_to = date.today() + timedelta(days=10)

    # Fetch matches from database only
    db_matches = await MatchService.get_matches(
        date_from=date_from,
        date_to=date_to,
        competition=competition,
        status=status.upper() if status else None,
    )

    matches = [
        MatchResponse(
            id=m["id"],
            external_id=m.get("external_id", f"DB_{m['id']}"),
            home_team=TeamInfo(
                id=m["home_team"]["id"],
                name=m["home_team"]["name"] or "Unknown",
                short_name=m["home_team"].get("short_name")
                or (m["home_team"]["name"] or "UNK")[:3].upper(),
                logo_url=m["home_team"].get("logo_url"),
                elo_rating=m["home_team"].get("elo_rating", 1500.0),
                form=m["home_team"].get("form"),
            ),
            away_team=TeamInfo(
                id=m["away_team"]["id"],
                name=m["away_team"]["name"] or "Unknown",
                short_name=m["away_team"].get("short_name")
                or (m["away_team"]["name"] or "UNK")[:3].upper(),
                logo_url=m["away_team"].get("logo_url"),
                elo_rating=m["away_team"].get("elo_rating", 1500.0),
                form=m["away_team"].get("form"),
            ),
            competition=COMPETITION_NAMES.get(m.get("competition_code", ""), "Unknown"),
            competition_code=m.get("competition_code") or competition or "UNK",
            match_date=(
                datetime.fromisoformat(m["match_date"])
                if m.get("match_date")
                else datetime.now(UTC)
            ),
            status=_normalize_status(m.get("status")),
            home_score=m.get("home_score"),
            away_score=m.get("away_score"),
            matchday=m.get("matchday"),
        )
        for m in db_matches
    ]
    matches = sorted(matches, key=lambda m: m.match_date)

    # Pagination
    total = len(matches)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_matches = matches[start_idx:end_idx]

    return MatchListResponse(
        matches=paginated_matches,
        total=total,
        page=page,
        per_page=per_page,
        data_source=DataSourceInfo(source="database"),
    )


@router.get("/upcoming", responses=AUTH_RESPONSES, operation_id="getUpcomingMatches")
@limiter.limit(RATE_LIMITS["matches"])
async def get_upcoming_matches(
    request: Request,
    user: AuthenticatedUser,
    days: int = Query(2, ge=1, le=7, description="Number of days ahead"),
    competition: str | None = Query(None),
) -> MatchListResponse:
    """Get upcoming matches for the next N days from database."""
    date_from = date.today()
    date_to = date.today() + timedelta(days=days)

    # Check Redis cache (2-minute TTL for upcoming matches)
    redis_key = f"upcoming:{date_from}:{days}:{competition or 'all'}"
    cached = await cache_get(redis_key)
    if cached:
        try:
            return MatchListResponse(**json.loads(cached))
        except Exception as e:
            logger.debug(f"Invalid Redis cache for upcoming matches: {e}")

    # Fetch from database - teams are eager-loaded (no N+1)
    db_matches = await MatchService.get_scheduled(
        date_from=date_from,
        date_to=date_to,
        competition=competition,
    )

    matches = [
        MatchResponse(
            id=int(m["external_id"].split("_")[-1]) if "_" in m.get("external_id", "") else m["id"],
            external_id=m["external_id"],
            home_team=TeamInfo(
                id=m["home_team"]["id"],
                name=m["home_team"]["name"] or "Unknown",
                short_name=m["home_team"].get("short_name")
                or (m["home_team"]["name"] or "UNK")[:3].upper(),
                logo_url=m["home_team"].get("logo_url"),
                elo_rating=m["home_team"].get("elo_rating", 1500.0),
                form=m["home_team"].get("form"),
            ),
            away_team=TeamInfo(
                id=m["away_team"]["id"],
                name=m["away_team"]["name"] or "Unknown",
                short_name=m["away_team"].get("short_name")
                or (m["away_team"]["name"] or "UNK")[:3].upper(),
                logo_url=m["away_team"].get("logo_url"),
                elo_rating=m["away_team"].get("elo_rating", 1500.0),
                form=m["away_team"].get("form"),
            ),
            competition=COMPETITION_NAMES.get(m.get("competition_code", ""), "Unknown"),
            competition_code=m.get("competition_code") or competition or "UNK",
            match_date=(
                datetime.fromisoformat(m["match_date"])
                if m.get("match_date")
                else datetime.now(UTC)
            ),
            status=_normalize_status(m.get("status")),
            matchday=m.get("matchday"),
        )
        for m in db_matches
    ]
    matches = sorted(matches, key=lambda m: m.match_date)

    response = MatchListResponse(
        matches=matches,
        total=len(matches),
        page=1,
        per_page=len(matches),
        data_source=DataSourceInfo(source="database"),
    )
    # Cache in Redis for 2 minutes
    try:
        await cache_set(redis_key, json.dumps(response.model_dump(mode="json"), default=str), 120)
    except Exception as e:
        logger.debug(f"Failed to cache upcoming matches in Redis: {e}")
    return response


# ============================================================================
# Live Scores Endpoint
# ============================================================================


class LiveMatchEvent(BaseModel):
    """Event in a live match (goal, card, etc.)."""

    type: str  # goal, yellow_card, red_card, substitution
    minute: int
    team: str  # home, away
    player: str | None = None


class LiveMatchInfo(BaseModel):
    """Live match with score and events."""

    id: int
    external_id: str
    home_team: TeamInfo
    away_team: TeamInfo
    home_score: int
    away_score: int
    minute: int | None = None
    status: str  # 1H, HT, 2H, FT, ET, PEN
    competition: str
    competition_code: str
    events: list[LiveMatchEvent] = []


class LiveScoresResponse(BaseModel):
    """Live scores response."""

    matches: list[LiveMatchInfo]
    total: int
    updated_at: datetime
    data_source: DataSourceInfo | None = None


@router.get(
    "/live",
    response_model=LiveScoresResponse,
    responses=AUTH_RESPONSES,
    operation_id="getLiveScores",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_live_scores(
    request: Request,
    user: AuthenticatedUser,
    competition: str | None = Query(None, description="Filter by competition code"),
) -> LiveScoresResponse:
    """
    Get live match scores with real-time updates.

    Returns all currently playing matches with scores, minute, and status.
    Results are cached for 30 seconds to reduce API calls.
    """
    import json

    cache_key = f"live_scores:{competition or 'all'}"

    # Try Redis cache first (using shared pool)
    try:
        cached = await cache_get(cache_key)
        if cached:
            data = json.loads(cached)
            return LiveScoresResponse(
                matches=[LiveMatchInfo(**m) for m in data["matches"]],
                total=data["total"],
                updated_at=datetime.fromisoformat(data["updated_at"]),
                data_source=DataSourceInfo(
                    source="cache",
                    is_fallback=False,
                    details="Cached for 30 seconds",
                ),
            )
    except Exception as e:
        logger.debug(f"Redis cache miss or error: {e}")

    # Fetch from football-data.org API
    try:
        client = get_football_data_client()

        # Get matches with LIVE status
        api_matches = await client.get_matches(
            competition=competition,
            status="LIVE",
            date_from=date.today(),
            date_to=date.today(),
        )

        live_matches: list[LiveMatchInfo] = []

        for api_match in api_matches:
            # Map status to display format
            status_display_map = {
                "IN_PLAY": "2H",
                "LIVE": "LIVE",
                "PAUSED": "HT",
                "HALFTIME": "HT",
            }
            display_status = status_display_map.get(api_match.status, api_match.status)

            # Extract scores
            home_score = 0
            away_score = 0
            if api_match.score and api_match.score.fullTime:
                home_score = api_match.score.fullTime.home or 0
                away_score = api_match.score.fullTime.away or 0

            # Get minute if available (API may provide this)
            minute = getattr(api_match, "minute", None)

            live_matches.append(
                LiveMatchInfo(
                    id=api_match.id,
                    external_id=f"{api_match.competition.code}_{api_match.id}",
                    home_team=TeamInfo(
                        id=api_match.homeTeam.id,
                        name=api_match.homeTeam.name,
                        short_name=(
                            api_match.homeTeam.tla
                            or api_match.homeTeam.shortName
                            or api_match.homeTeam.name[:3].upper()
                        ),
                        logo_url=api_match.homeTeam.crest,
                    ),
                    away_team=TeamInfo(
                        id=api_match.awayTeam.id,
                        name=api_match.awayTeam.name,
                        short_name=(
                            api_match.awayTeam.tla
                            or api_match.awayTeam.shortName
                            or api_match.awayTeam.name[:3].upper()
                        ),
                        logo_url=api_match.awayTeam.crest,
                    ),
                    home_score=home_score,
                    away_score=away_score,
                    minute=minute,
                    status=display_status,
                    competition=api_match.competition.name,
                    competition_code=api_match.competition.code,
                    events=[],  # Events would require additional API calls
                )
            )

        now = datetime.utcnow()

        # Cache result for 30 seconds
        try:
            cache_data = {
                "matches": [m.model_dump() for m in live_matches],
                "total": len(live_matches),
                "updated_at": now.isoformat(),
            }
            await cache_set(cache_key, json.dumps(cache_data, default=str), 30)
        except Exception as e:
            logger.debug(f"Failed to cache live scores: {e}")

        return LiveScoresResponse(
            matches=live_matches,
            total=len(live_matches),
            updated_at=now,
            data_source=DataSourceInfo(source="live_api"),
        )

    except RateLimitError as e:
        logger.warning(f"External API rate limit for live scores: {e}")
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        lang = detect_language_from_header(request.headers.get("Accept-Language", ""))
        raise HTTPException(
            status_code=429,
            detail={
                "message": api_msg("live_scores_rate_limit", lang),
                "error_code": "EXTERNAL_API_RATE_LIMIT",
                "details": api_msg("live_scores_unavailable", lang),
                "retry_after_seconds": retry_after,
            },
        )

    except (FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for live scores: {e}")
        lang = detect_language_from_header(request.headers.get("Accept-Language", ""))
        raise HTTPException(
            status_code=503,
            detail={
                "message": api_msg("live_scores_service_unavailable", lang),
                "error_code": "SERVICE_UNAVAILABLE",
                "details": api_msg("external_api_unavailable", lang, detail=str(e)[:80]),
            },
        )


@router.get(
    "/competitions",
    response_model=CompetitionsListResponse,
    responses=AUTH_RESPONSES,
    operation_id="getCompetitions",
)
async def get_competitions(
    request: Request,
    user: AuthenticatedUser,
) -> CompetitionsListResponse:
    """
    Get list of all supported competitions.

    Returns competition codes, names, countries, and flag codes for UI display.
    This is the single source of truth for competition data.
    """
    return CompetitionsListResponse(
        competitions=[
            CompetitionResponse(
                code=comp["code"],
                name=comp["name"],
                country=comp["country"],
                flag=comp["flag"],
            )
            for comp in COMPETITIONS
        ],
        total=len(COMPETITIONS),
    )


@router.get(
    "/{match_id}",
    response_model=MatchResponse,
    responses=AUTH_RESPONSES,
    operation_id="getMatch",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_match(request: Request, match_id: int, user: AuthenticatedUser) -> MatchResponse:
    """Get details for a specific match from database (requires authentication)."""
    # Use database directly - no external API call
    match_data = await MatchService.get_match_by_api_id(match_id)

    if not match_data:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    # Convert DB data to MatchResponse format
    home_team = match_data["home_team"]
    away_team = match_data["away_team"]

    comp_code = match_data.get("competition_code", "")
    return MatchResponse(
        id=match_id,
        external_id=match_data.get("external_id", str(match_id)),
        home_team=TeamInfo(
            id=home_team["id"],
            name=home_team["name"],
            short_name=home_team["short_name"] or home_team["name"][:3].upper(),
            logo_url=home_team.get("logo_url"),
            elo_rating=home_team.get("elo_rating"),
            form=home_team.get("form"),
        ),
        away_team=TeamInfo(
            id=away_team["id"],
            name=away_team["name"],
            short_name=away_team["short_name"] or away_team["name"][:3].upper(),
            logo_url=away_team.get("logo_url"),
            elo_rating=away_team.get("elo_rating"),
            form=away_team.get("form"),
        ),
        match_date=(
            datetime.fromisoformat(match_data["match_date"])
            if match_data["match_date"]
            else datetime.now()
        ),
        status=_normalize_status(match_data.get("status")),
        competition=comp_code,
        competition_code=comp_code,
        matchday=match_data.get("matchday"),
        home_score=match_data.get("home_score"),
        away_score=match_data.get("away_score"),
    )


@router.get(
    "/{match_id}/head-to-head",
    response_model=HeadToHeadResponse,
    responses=AUTH_RESPONSES,
    operation_id="getHeadToHead",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_head_to_head(
    request: Request,
    match_id: int,
    user: AuthenticatedUser,
    limit: int = Query(10, ge=1, le=20),
) -> HeadToHeadResponse:
    """Get head-to-head history for teams in a match from database."""
    # First get the match to find team IDs
    match_data = await MatchService.get_match_by_api_id(match_id)
    if not match_data:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    home_team_id = match_data["home_team"]["id"]
    away_team_id = match_data["away_team"]["id"]

    # Get head-to-head from database
    h2h_matches = await MatchService.get_head_to_head_from_db(
        home_team_id, away_team_id, limit=limit
    )

    matches = []
    home_wins = 0
    draws = 0
    away_wins = 0
    total_goals = 0

    for m in h2h_matches:
        home_score = m.get("home_score") or 0
        away_score = m.get("away_score") or 0

        total_goals += home_score + away_score

        if home_score > away_score:
            home_wins += 1
        elif away_score > home_score:
            away_wins += 1
        else:
            draws += 1

        matches.append(
            HeadToHeadMatch(
                date=datetime.fromisoformat(m["date"]) if m["date"] else datetime.now(),
                home_team=m["home_team"],
                away_team=m["away_team"],
                home_score=home_score,
                away_score=away_score,
                competition=COMPETITION_NAMES.get(m.get("competition"), m.get("competition", "")),
            )
        )

    total_matches = len(matches)
    avg_goals = total_goals / total_matches if total_matches > 0 else 0.0

    return HeadToHeadResponse(
        matches=matches,
        home_wins=home_wins,
        draws=draws,
        away_wins=away_wins,
        avg_goals=round(avg_goals, 2),
        total_matches=total_matches,
        data_source=DataSourceInfo(source="database"),
    )


@router.get(
    "/teams/{team_id}/form",
    response_model=TeamFormResponse,
    responses=AUTH_RESPONSES,
    operation_id="getTeamForm",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_team_form(
    request: Request,
    team_id: int,
    user: AuthenticatedUser,
    matches_count: int = Query(5, ge=3, le=10),
    team_name: str | None = Query(None, description="Team name for API fallback"),
) -> TeamFormResponse:
    """Get recent form for a team."""
    try:
        # Get team info
        client = get_football_data_client()
        team_data = await client.get_team(team_id)
        team_name = team_data.get("name", "Unknown")

        # Get recent finished matches
        api_matches = await client.get_team_matches(
            team_id=team_id,
            status="FINISHED",
            limit=matches_count,
        )

        last_matches = []
        form_string = ""
        total_points = 0
        goals_scored = 0
        goals_conceded = 0
        clean_sheets = 0

        for api_match in api_matches:
            is_home = api_match.homeTeam.id == team_id
            opponent = api_match.awayTeam.name if is_home else api_match.homeTeam.name

            home_score = 0
            away_score = 0

            if api_match.score and api_match.score.fullTime:
                home_score = api_match.score.fullTime.home or 0
                away_score = api_match.score.fullTime.away or 0

            team_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score

            goals_scored += team_score
            goals_conceded += opp_score

            if opp_score == 0:
                clean_sheets += 1

            # Determine result
            result: Literal["W", "D", "L"]
            if team_score > opp_score:
                result = "W"
                total_points += 3
            elif team_score < opp_score:
                result = "L"
            else:
                result = "D"
                total_points += 1

            form_string += result

            last_matches.append(
                TeamFormMatch(
                    opponent=opponent,
                    result=result,
                    score=f"{team_score}-{opp_score}",
                    home_away="H" if is_home else "A",
                    date=datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00")),
                )
            )

        num_matches = len(last_matches)

        return TeamFormResponse(
            team_id=team_id,
            team_name=team_name,
            last_matches=last_matches,
            form_string=form_string,
            points_last_5=total_points,
            goals_scored_avg=round(goals_scored / num_matches, 2) if num_matches > 0 else 0.0,
            goals_conceded_avg=round(goals_conceded / num_matches, 2) if num_matches > 0 else 0.0,
            clean_sheets=clean_sheets,
            data_source=DataSourceInfo(source="live_api"),
        )

    except RateLimitError as e:
        logger.warning(f"External API rate limit for team form: {e}")
        retry_after = e.details.get("retry_after", 60) if e.details else 60
        raise HTTPException(
            status_code=429,
            detail={
                "message": "External API rate limit reached. Please retry later.",
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    except FootballDataAPIError as e:
        logger.error(f"Football Data API error for team form: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "message": "External football data service unavailable. Please retry later.",
                "warning_code": "EXTERNAL_API_ERROR",
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error for team form {team_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error while fetching team form.",
                "warning_code": "INTERNAL_ERROR",
            },
        )


@router.get(
    "/standings/{competition_code}",
    response_model=StandingsResponse,
    responses=AUTH_RESPONSES,
    operation_id="getStandings",
)
@limiter.limit(RATE_LIMITS["matches"])
async def get_standings(
    request: Request,
    competition_code: str,
    user: AuthenticatedUser,
) -> StandingsResponse:
    """
    Get current league standings for a competition.

    Standings are pre-calculated daily at 6am and cached.

    Competition codes:
    - PL: Premier League
    - PD: La Liga
    - BL1: Bundesliga
    - SA: Serie A
    - FL1: Ligue 1
    """
    try:
        # Validate competition code
        if competition_code not in COMPETITION_NAMES:
            valid_codes = ", ".join(COMPETITION_NAMES.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid competition: {competition_code}. Use: {valid_codes}",
            )

        # Try to get cached data first
        try:
            from src.services.cache_service import get_cached_data

            cached = await get_cached_data(f"standings_{competition_code}")
            if cached:
                logger.debug(f"Returning cached standings for {competition_code}")
                standings = [
                    StandingTeamResponse(
                        position=team.get("position", 0),
                        team_id=team.get("team_id", 0),
                        team_name=team.get("team_name", "Unknown"),
                        team_logo_url=team.get("team_logo_url"),
                        played=team.get("played", 0),
                        won=team.get("won", 0),
                        drawn=team.get("drawn", 0),
                        lost=team.get("lost", 0),
                        goals_for=team.get("goals_for", 0),
                        goals_against=team.get("goals_against", 0),
                        goal_difference=team.get("goal_difference", 0),
                        points=team.get("points", 0),
                    )
                    for team in cached.get("standings", [])
                ]
                return StandingsResponse(
                    competition_code=competition_code,
                    competition_name=cached.get(
                        "competition_name",
                        COMPETITION_NAMES.get(competition_code, competition_code),
                    ),
                    standings=standings,
                    last_updated=datetime.fromisoformat(
                        cached.get("calculated_at", datetime.now().isoformat())
                    ),
                    data_source=DataSourceInfo(source="cache"),
                )
        except Exception as e:
            logger.warning(f"Cache lookup failed for standings {competition_code}: {e}")

        # Fetch standings from API
        client = get_football_data_client()
        api_standings = await client.get_standings(competition_code)

        # Convert to our format
        standings = []
        for api_team in api_standings:
            standings.append(
                StandingTeamResponse(
                    position=api_team.position,
                    team_id=api_team.team.id,
                    team_name=api_team.team.name,
                    team_logo_url=api_team.team.crest,
                    played=api_team.playedGames,
                    won=api_team.won,
                    drawn=api_team.draw,
                    lost=api_team.lost,
                    goals_for=api_team.goalsFor,
                    goals_against=api_team.goalsAgainst,
                    goal_difference=api_team.goalDifference,
                    points=api_team.points,
                )
            )

        return StandingsResponse(
            competition_code=competition_code,
            competition_name=COMPETITION_NAMES.get(competition_code, competition_code),
            standings=standings,
            last_updated=datetime.now(),
            data_source=DataSourceInfo(source="live_api"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except RateLimitError as e:
        logger.warning(f"External API rate limit for standings {competition_code}: {e}")
        retry_after = e.details.get("retry_after", 60) if e.details else 60

        # Try database first using async service
        try:
            db_standings = await StandingService.get_standings(competition_code)
            if db_standings:
                logger.info(f"Found {len(db_standings)} standings in DB for {competition_code}")
                standings = []
                for db_team in db_standings:
                    team_data = db_team.get("team", {})
                    standings.append(
                        StandingTeamResponse(
                            position=db_team.get("position", 0),
                            team_id=team_data.get("id", 0),
                            team_name=team_data.get("name", "Unknown"),
                            team_logo_url=team_data.get("crest"),
                            played=db_team.get("playedGames", 0),
                            won=db_team.get("won", 0),
                            drawn=db_team.get("draw", 0),
                            lost=db_team.get("lost", 0),
                            goals_for=db_team.get("goalsFor", 0),
                            goals_against=db_team.get("goalsAgainst", 0),
                            goal_difference=db_team.get("goalDifference", 0),
                            points=db_team.get("points", 0),
                        )
                    )

                return StandingsResponse(
                    competition_code=competition_code,
                    competition_name=COMPETITION_NAMES.get(competition_code, competition_code),
                    standings=standings,
                    last_updated=datetime.now(),
                    data_source=DataSourceInfo(
                        source="database",
                        is_fallback=True,
                        warning=api_msg(
                            "standings_cache_warning",
                            detect_language_from_header(request.headers.get("Accept-Language", "")),
                        ),
                        warning_code="EXTERNAL_API_RATE_LIMIT",
                        details=api_msg(
                            "rate_limit_reached",
                            detect_language_from_header(request.headers.get("Accept-Language", "")),
                        ),
                        retry_after_seconds=retry_after,
                    ),
                )
        except Exception as db_error:
            logger.warning(f"Database fallback failed for standings: {db_error}")

    except (FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for standings {competition_code}: {e}, trying database...")

        # Try database first using async service
        try:
            db_standings = await StandingService.get_standings(competition_code)
            if db_standings:
                logger.info(f"Found {len(db_standings)} standings in DB for {competition_code}")
                standings = []
                for db_team in db_standings:
                    team_data = db_team.get("team", {})
                    standings.append(
                        StandingTeamResponse(
                            position=db_team.get("position", 0),
                            team_id=team_data.get("id", 0),
                            team_name=team_data.get("name", "Unknown"),
                            team_logo_url=team_data.get("crest"),
                            played=db_team.get("playedGames", 0),
                            won=db_team.get("won", 0),
                            drawn=db_team.get("draw", 0),
                            lost=db_team.get("lost", 0),
                            goals_for=db_team.get("goalsFor", 0),
                            goals_against=db_team.get("goalsAgainst", 0),
                            goal_difference=db_team.get("goalDifference", 0),
                            points=db_team.get("points", 0),
                        )
                    )

                return StandingsResponse(
                    competition_code=competition_code,
                    competition_name=COMPETITION_NAMES.get(competition_code, competition_code),
                    standings=standings,
                    last_updated=datetime.now(),
                    data_source=DataSourceInfo(
                        source="database",
                        is_fallback=True,
                        warning=api_msg(
                            "standings_cache_warning",
                            detect_language_from_header(request.headers.get("Accept-Language", "")),
                        ),
                        warning_code="EXTERNAL_API_ERROR",
                        details=api_msg(
                            "error_detail",
                            detect_language_from_header(request.headers.get("Accept-Language", "")),
                            detail=str(e)[:80],
                        ),
                    ),
                )
        except Exception as db_error:
            logger.warning(f"Database fallback failed for standings: {db_error}")

        # If we reach here after RateLimitError, no data available
        raise HTTPException(
            status_code=429,
            detail={
                "message": "External API rate limit reached and no cached data available.",
                "warning_code": "EXTERNAL_API_RATE_LIMIT",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # If we reach here after other exceptions, raise 503
    raise HTTPException(
        status_code=503,
        detail={
            "message": "Standings data unavailable. External API and database both failed.",
            "warning_code": "SERVICE_UNAVAILABLE",
        },
    )
