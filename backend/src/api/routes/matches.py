"""Match endpoints - Real data from football-data.org API with DB and mock fallback."""

from datetime import date, datetime, timedelta
from typing import Literal
import logging

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from src.data.sources.football_data import get_football_data_client, MatchData, COMPETITIONS
from src.data.database import get_matches_from_db, get_standings_from_db
from src.core.exceptions import FootballDataAPIError, RateLimitError

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_mock_matches() -> list["MatchResponse"]:
    """Generate mock matches when API is unavailable."""
    from datetime import timezone

    base_date = datetime.now(timezone.utc)

    mock_data = [
        {"home": "Manchester City", "away": "Chelsea", "comp": "Premier League", "code": "PL"},
        {"home": "Liverpool", "away": "Arsenal", "comp": "Premier League", "code": "PL"},
        {"home": "Real Madrid", "away": "Barcelona", "comp": "La Liga", "code": "PD"},
        {"home": "Atletico Madrid", "away": "Sevilla", "comp": "La Liga", "code": "PD"},
        {"home": "Bayern Munich", "away": "Borussia Dortmund", "comp": "Bundesliga", "code": "BL1"},
        {"home": "RB Leipzig", "away": "Bayer Leverkusen", "comp": "Bundesliga", "code": "BL1"},
        {"home": "Inter", "away": "AC Milan", "comp": "Serie A", "code": "SA"},
        {"home": "Juventus", "away": "Napoli", "comp": "Serie A", "code": "SA"},
        {"home": "PSG", "away": "Marseille", "comp": "Ligue 1", "code": "FL1"},
        {"home": "Lyon", "away": "Monaco", "comp": "Ligue 1", "code": "FL1"},
    ]

    matches = []
    for i, m in enumerate(mock_data):
        match_time = base_date + timedelta(days=i // 3, hours=15 + (i % 3) * 2)
        matches.append(MatchResponse(
            id=1000 + i,
            external_id=f"{m['code']}_{1000 + i}",
            home_team=TeamInfo(
                id=100 + i * 2,
                name=m["home"],
                short_name=m["home"][:3].upper(),
            ),
            away_team=TeamInfo(
                id=101 + i * 2,
                name=m["away"],
                short_name=m["away"][:3].upper(),
            ),
            competition=m["comp"],
            competition_code=m["code"],
            match_date=match_time,
            status="scheduled",
            matchday=i % 20 + 1,
        ))

    return matches


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
    if api_match.score and api_match.score.fullTime:
        home_score = api_match.score.fullTime.home
        away_score = api_match.score.fullTime.away

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

        # Default date range if not specified: next 10 days (API free tier limit)
        if not date_from and not date_to:
            date_from = date.today()
            date_to = date.today() + timedelta(days=10)

        # Fetch matches from API
        client = get_football_data_client()
        api_matches = await client.get_matches(
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

    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error: {e}, trying database fallback...")

        # Try database first
        try:
            db_matches = get_matches_from_db(
                date_from=date_from,
                date_to=date_to,
                competition=competition,
            )

            if db_matches:
                logger.info(f"Found {len(db_matches)} matches in database")
                matches = [_convert_api_match(MatchData(**m)) for m in db_matches]
                matches = sorted(matches, key=lambda m: m.match_date)

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
        except Exception as db_error:
            logger.warning(f"Database fallback failed: {db_error}")

        # Final fallback to mock data
        logger.warning("Using mock data as final fallback")
        matches = _generate_mock_matches()
        return MatchListResponse(
            matches=matches[:per_page],
            total=len(matches),
            page=page,
            per_page=per_page,
        )


@router.get("/upcoming")
async def get_upcoming_matches(
    days: int = Query(2, ge=1, le=7, description="Number of days ahead"),
    competition: str | None = Query(None),
) -> MatchListResponse:
    """Get upcoming matches for the next N days."""
    try:
        client = get_football_data_client()
        api_matches = await client.get_upcoming_matches(
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

    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error in upcoming: {e}, using mock data")
        matches = _generate_mock_matches()[:5]  # Only first 5 for upcoming
        return MatchListResponse(
            matches=matches,
            total=len(matches),
            page=1,
            per_page=len(matches),
        )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int) -> MatchResponse:
    """Get details for a specific match."""
    try:
        client = get_football_data_client()
        api_match = await client.get_match(match_id)
        return _convert_api_match(api_match)

    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for match {match_id}: {e}, using mock data")
        # Return mock match
        mock_matches = _generate_mock_matches()
        # Find by ID or return first one
        for m in mock_matches:
            if m.id == match_id:
                return m
        # Clone the first mock match and set the requested ID (avoid mutation)
        mock = mock_matches[0].model_copy()
        mock.id = match_id
        return mock


@router.get("/{match_id}/head-to-head", response_model=HeadToHeadResponse)
async def get_head_to_head(
    match_id: int,
    limit: int = Query(10, ge=1, le=20),
) -> HeadToHeadResponse:
    """Get head-to-head history for teams in a match."""
    try:
        client = get_football_data_client()
        api_matches = await client.get_head_to_head(match_id, limit=limit)

        matches = []
        home_wins = 0
        draws = 0
        away_wins = 0
        total_goals = 0

        for api_match in api_matches:
            home_score = 0
            away_score = 0

            if api_match.score and api_match.score.fullTime:
                home_score = api_match.score.fullTime.home or 0
                away_score = api_match.score.fullTime.away or 0

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

    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for head-to-head: {e}, using mock data")
        # Return mock head-to-head data
        return HeadToHeadResponse(
            matches=[],
            home_wins=3,
            draws=2,
            away_wins=2,
            avg_goals=2.8,
            total_matches=7,
        )


@router.get("/teams/{team_id}/form", response_model=TeamFormResponse)
async def get_team_form(
    team_id: int,
    matches_count: int = Query(5, ge=3, le=10),
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

    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for team form: {e}, using mock data")
        # Return mock form data
        return TeamFormResponse(
            team_id=team_id,
            team_name=f"Team {team_id}",
            last_matches=[],
            form_string="WDWLW",
            points_last_5=10,
            goals_scored_avg=1.8,
            goals_conceded_avg=0.8,
            clean_sheets=2,
        )


@router.get("/standings/{competition_code}", response_model=StandingsResponse)
async def get_standings(
    competition_code: str,
) -> StandingsResponse:
    """
    Get current league standings for a competition.

    Competition codes:
    - PL: Premier League
    - PD: La Liga
    - BL1: Bundesliga
    - SA: Serie A
    - FL1: Ligue 1
    """
    try:
        # Validate competition code
        if competition_code not in COMPETITIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid competition code: {competition_code}. Must be one of: {', '.join(COMPETITIONS.keys())}"
            )

        # Fetch standings from API
        client = get_football_data_client()
        api_standings = await client.get_standings(competition_code)

        # Convert to our format
        standings = []
        for api_team in api_standings:
            standings.append(StandingTeamResponse(
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
            ))

        return StandingsResponse(
            competition_code=competition_code,
            competition_name=COMPETITIONS.get(competition_code, competition_code),
            standings=standings,
            last_updated=datetime.now(),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except (RateLimitError, FootballDataAPIError, Exception) as e:
        logger.warning(f"API error for standings {competition_code}: {e}, trying database...")

        # Try database first
        try:
            from src.data.sources.football_data import StandingTeam

            db_standings = get_standings_from_db(competition_code)
            if db_standings:
                logger.info(f"Found {len(db_standings)} standings in database for {competition_code}")
                standings = []
                for api_team in db_standings:
                    team_data = api_team.get("team", {})
                    standings.append(StandingTeamResponse(
                        position=api_team.get("position", 0),
                        team_id=team_data.get("id", 0),
                        team_name=team_data.get("name", "Unknown"),
                        team_logo_url=team_data.get("crest"),
                        played=api_team.get("playedGames", 0),
                        won=api_team.get("won", 0),
                        drawn=api_team.get("draw", 0),
                        lost=api_team.get("lost", 0),
                        goals_for=api_team.get("goalsFor", 0),
                        goals_against=api_team.get("goalsAgainst", 0),
                        goal_difference=api_team.get("goalDifference", 0),
                        points=api_team.get("points", 0),
                    ))

                return StandingsResponse(
                    competition_code=competition_code,
                    competition_name=COMPETITIONS.get(competition_code, competition_code),
                    standings=standings,
                    last_updated=datetime.now(),
                )
        except Exception as db_error:
            logger.warning(f"Database fallback failed for standings: {db_error}")

        # Final fallback to mock data
        logger.warning(f"Using mock data for standings {competition_code}")
        mock_standings = [
            StandingTeamResponse(
                position=i + 1,
                team_id=1000 + i,
                team_name=f"Team {i + 1}",
                team_logo_url=None,
                played=30,
                won=20 - i,
                drawn=6 - (i % 3),
                lost=4 + i,
                goals_for=70 - (i * 2),
                goals_against=30 + (i * 2),
                goal_difference=40 - (i * 4),
                points=66 - (i * 3),
            )
            for i in range(20)
        ]

        return StandingsResponse(
            competition_code=competition_code,
            competition_name=COMPETITIONS.get(competition_code, competition_code),
            standings=mock_standings,
            last_updated=datetime.now(),
        )
