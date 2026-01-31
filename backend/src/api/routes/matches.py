"""Match endpoints - Real data from football-data.org API."""

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from src.data.sources.football_data import football_data_client, MatchData, COMPETITIONS
from src.core.exceptions import FootballDataAPIError, RateLimitError

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


def _convert_api_match(api_match: MatchData) -> MatchResponse:
    """Convert football-data.org match to our response format."""
    # Map API status to our status
    status_map = {
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

    status = status_map.get(api_match.status, "scheduled")

    # Extract scores
    home_score = None
    away_score = None
    if api_match.score:
        full_time = api_match.score.get("fullTime")
        if full_time:
            home_score = full_time.home
            away_score = full_time.away

    return MatchResponse(
        id=api_match.id,
        external_id=f"{api_match.competition.code}_{api_match.id}",
        home_team=TeamInfo(
            id=api_match.homeTeam.id,
            name=api_match.homeTeam.name,
            short_name=api_match.homeTeam.tla or api_match.homeTeam.shortName or api_match.homeTeam.name[:3].upper(),
            logo_url=api_match.homeTeam.crest,
        ),
        away_team=TeamInfo(
            id=api_match.awayTeam.id,
            name=api_match.awayTeam.name,
            short_name=api_match.awayTeam.tla or api_match.awayTeam.shortName or api_match.awayTeam.name[:3].upper(),
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
    try:
        # Map our status to API status
        api_status = None
        if status:
            status_map = {
                "scheduled": "SCHEDULED",
                "live": "LIVE",
                "finished": "FINISHED",
            }
            api_status = status_map.get(status)

        # Default date range if not specified: next 14 days
        if not date_from and not date_to:
            date_from = date.today()
            date_to = date.today() + timedelta(days=14)

        # Fetch matches from API
        api_matches = await football_data_client.get_matches(
            competition=competition,
            date_from=date_from,
            date_to=date_to,
            status=api_status,
        )

        # Convert to our format
        matches = [_convert_api_match(m) for m in api_matches]

        # Sort by match date
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
        )

    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching data from football API: {str(e)}",
        )


@router.get("/upcoming")
async def get_upcoming_matches(
    days: int = Query(2, ge=1, le=7, description="Number of days ahead"),
    competition: str | None = Query(None),
) -> MatchListResponse:
    """Get upcoming matches for the next N days."""
    try:
        api_matches = await football_data_client.get_upcoming_matches(
            days=days,
            competition=competition,
        )

        matches = [_convert_api_match(m) for m in api_matches]
        matches = sorted(matches, key=lambda m: m.match_date)

        return MatchListResponse(
            matches=matches,
            total=len(matches),
            page=1,
            per_page=len(matches),
        )

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching data from football API: {str(e)}",
        )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int) -> MatchResponse:
    """Get details for a specific match."""
    try:
        api_match = await football_data_client.get_match(match_id)
        return _convert_api_match(api_match)

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 502,
            detail=f"Match {match_id} not found" if "not found" in str(e).lower() else str(e),
        )


@router.get("/{match_id}/head-to-head", response_model=HeadToHeadResponse)
async def get_head_to_head(
    match_id: int,
    limit: int = Query(10, ge=1, le=20),
) -> HeadToHeadResponse:
    """Get head-to-head history for teams in a match."""
    try:
        api_matches = await football_data_client.get_head_to_head(match_id, limit=limit)

        matches = []
        home_wins = 0
        draws = 0
        away_wins = 0
        total_goals = 0

        for api_match in api_matches:
            home_score = 0
            away_score = 0

            if api_match.score:
                full_time = api_match.score.get("fullTime")
                if full_time:
                    home_score = full_time.home or 0
                    away_score = full_time.away or 0

            total_goals += home_score + away_score

            if home_score > away_score:
                home_wins += 1
            elif away_score > home_score:
                away_wins += 1
            else:
                draws += 1

            matches.append(HeadToHeadMatch(
                date=datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00")),
                home_team=api_match.homeTeam.name,
                away_team=api_match.awayTeam.name,
                home_score=home_score,
                away_score=away_score,
                competition=api_match.competition.name,
            ))

        total_matches = len(matches)
        avg_goals = total_goals / total_matches if total_matches > 0 else 0.0

        return HeadToHeadResponse(
            matches=matches,
            home_wins=home_wins,
            draws=draws,
            away_wins=away_wins,
            avg_goals=round(avg_goals, 2),
            total_matches=total_matches,
        )

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching head-to-head data: {str(e)}",
        )


@router.get("/teams/{team_id}/form", response_model=TeamFormResponse)
async def get_team_form(
    team_id: int,
    matches_count: int = Query(5, ge=3, le=10),
) -> TeamFormResponse:
    """Get recent form for a team."""
    try:
        # Get team info
        team_data = await football_data_client.get_team(team_id)
        team_name = team_data.get("name", "Unknown")

        # Get recent finished matches
        api_matches = await football_data_client.get_team_matches(
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

            if api_match.score:
                full_time = api_match.score.get("fullTime")
                if full_time:
                    home_score = full_time.home or 0
                    away_score = full_time.away or 0

            team_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score

            goals_scored += team_score
            goals_conceded += opp_score

            if opp_score == 0:
                clean_sheets += 1

            # Determine result
            if team_score > opp_score:
                result = "W"
                total_points += 3
            elif team_score < opp_score:
                result = "L"
            else:
                result = "D"
                total_points += 1

            form_string += result

            last_matches.append(TeamFormMatch(
                opponent=opponent,
                result=result,
                score=f"{team_score}-{opp_score}",
                home_away="H" if is_home else "A",
                date=datetime.fromisoformat(api_match.utcDate.replace("Z", "+00:00")),
            ))

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
        )

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )
    except FootballDataAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching team form: {str(e)}",
        )
