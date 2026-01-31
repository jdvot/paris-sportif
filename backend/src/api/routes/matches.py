"""Match endpoints."""

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query, HTTPException
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


# Mock data for teams
TEAMS = {
    # Premier League
    1: TeamInfo(id=1, name="Manchester City", short_name="MCI", elo_rating=2180),
    2: TeamInfo(id=2, name="Liverpool", short_name="LIV", elo_rating=2150),
    3: TeamInfo(id=3, name="Arsenal", short_name="ARS", elo_rating=2120),
    4: TeamInfo(id=4, name="Manchester United", short_name="MNU", elo_rating=2080),
    5: TeamInfo(id=5, name="Tottenham Hotspur", short_name="TOT", elo_rating=2050),
    6: TeamInfo(id=6, name="Chelsea", short_name="CHE", elo_rating=2000),
    7: TeamInfo(id=7, name="Aston Villa", short_name="AVL", elo_rating=1950),
    8: TeamInfo(id=8, name="Newcastle United", short_name="NEW", elo_rating=1920),
    # La Liga
    10: TeamInfo(id=10, name="Real Madrid", short_name="RMA", elo_rating=2200),
    11: TeamInfo(id=11, name="Barcelona", short_name="BAR", elo_rating=2100),
    12: TeamInfo(id=12, name="Atlético Madrid", short_name="ATM", elo_rating=2050),
    13: TeamInfo(id=13, name="Sevilla", short_name="SEV", elo_rating=1950),
    14: TeamInfo(id=14, name="Real Sociedad", short_name="RSO", elo_rating=1900),
    # Serie A
    20: TeamInfo(id=20, name="Napoli", short_name="NAP", elo_rating=2100),
    21: TeamInfo(id=21, name="Inter Milano", short_name="INT", elo_rating=2080),
    22: TeamInfo(id=22, name="AC Milan", short_name="MIL", elo_rating=2050),
    23: TeamInfo(id=23, name="Juventus", short_name="JUV", elo_rating=2000),
    24: TeamInfo(id=24, name="Lazio", short_name="LAZ", elo_rating=1900),
    # Bundesliga
    30: TeamInfo(id=30, name="Bayern Munich", short_name="BAY", elo_rating=2150),
    31: TeamInfo(id=31, name="Borussia Dortmund", short_name="BVB", elo_rating=2000),
    32: TeamInfo(id=32, name="RB Leipzig", short_name="RBL", elo_rating=1950),
    33: TeamInfo(id=33, name="Bayer Leverkusen", short_name="B04", elo_rating=1900),
    # Ligue 1
    40: TeamInfo(id=40, name="Paris Saint-Germain", short_name="PSG", elo_rating=2150),
    41: TeamInfo(id=41, name="Marseille", short_name="OM", elo_rating=1950),
    42: TeamInfo(id=42, name="Lens", short_name="RCL", elo_rating=1900),
    43: TeamInfo(id=43, name="Monaco", short_name="ASM", elo_rating=1900),
}


def generate_mock_matches() -> list[MatchResponse]:
    """Generate realistic mock matches for the next 7 days."""
    matches = []
    match_id = 1000
    now = datetime.now()

    # Premier League matches
    pl_matchups = [
        (1, 6, "Manchester City vs Chelsea"),  # MCI vs CHE
        (2, 3, "Liverpool vs Arsenal"),  # LIV vs ARS
        (4, 5, "Manchester United vs Tottenham"),  # MNU vs TOT
        (7, 8, "Aston Villa vs Newcastle"),  # AVL vs NEW
    ]

    # La Liga matches
    la_liga_matchups = [
        (10, 11, "Real Madrid vs Barcelona"),  # RMA vs BAR
        (12, 13, "Atlético Madrid vs Sevilla"),  # ATM vs SEV
        (14, 10, "Real Sociedad vs Real Madrid"),  # RSO vs RMA
    ]

    # Serie A matches
    serie_a_matchups = [
        (20, 21, "Napoli vs Inter Milano"),  # NAP vs INT
        (22, 23, "AC Milan vs Juventus"),  # MIL vs JUV
        (24, 20, "Lazio vs Napoli"),  # LAZ vs NAP
    ]

    # Bundesliga matches
    bundesliga_matchups = [
        (30, 31, "Bayern Munich vs Borussia Dortmund"),  # BAY vs BVB
        (32, 33, "RB Leipzig vs Bayer Leverkusen"),  # RBL vs B04
    ]

    # Ligue 1 matches
    ligue1_matchups = [
        (40, 41, "PSG vs Marseille"),  # PSG vs OM
        (42, 43, "Lens vs Monaco"),  # RCL vs ASM
    ]

    all_matchups = [
        (pl_matchups, "Premier League", "PL", 1),
        (la_liga_matchups, "La Liga", "PD", 2),
        (serie_a_matchups, "Serie A", "SA", 3),
        (bundesliga_matchups, "Bundesliga", "BL1", 4),
        (ligue1_matchups, "Ligue 1", "FL1", 5),
    ]

    matchday = 1
    for day_offset in range(7):
        match_date = now + timedelta(days=day_offset, hours=15)

        for league_matchups, league_name, league_code, league_id in all_matchups:
            for idx, (home_id, away_id, _) in enumerate(league_matchups):
                if (day_offset + idx) % 3 == 0:  # Spread matches across days
                    matches.append(
                        MatchResponse(
                            id=match_id,
                            external_id=f"{league_code}_{match_id}",
                            home_team=TEAMS[home_id],
                            away_team=TEAMS[away_id],
                            competition=league_name,
                            competition_code=league_code,
                            match_date=match_date + timedelta(hours=idx),
                            status="scheduled",
                            matchday=matchday,
                        )
                    )
                    match_id += 1

        matchday += 1

    return matches


# Store mock matches in memory
_mock_matches = generate_mock_matches()


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
    # Filter matches based on criteria
    filtered_matches = _mock_matches

    if competition:
        filtered_matches = [m for m in filtered_matches if m.competition_code == competition]

    if date_from:
        filtered_matches = [m for m in filtered_matches if m.match_date.date() >= date_from]

    if date_to:
        filtered_matches = [m for m in filtered_matches if m.match_date.date() <= date_to]

    if status:
        filtered_matches = [m for m in filtered_matches if m.status == status]

    # Sort by match date
    filtered_matches = sorted(filtered_matches, key=lambda m: m.match_date)

    # Pagination
    total = len(filtered_matches)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_matches = filtered_matches[start_idx:end_idx]

    return MatchListResponse(
        matches=paginated_matches,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/upcoming")
async def get_upcoming_matches(
    days: int = Query(2, ge=1, le=7, description="Number of days ahead"),
    competition: str | None = Query(None),
) -> MatchListResponse:
    """Get upcoming matches for the next N days."""
    now = datetime.now()
    cutoff_date = now + timedelta(days=days)

    # Filter for scheduled matches within the next N days
    filtered_matches = [
        m for m in _mock_matches
        if m.status == "scheduled" and now <= m.match_date <= cutoff_date
    ]

    if competition:
        filtered_matches = [m for m in filtered_matches if m.competition_code == competition]

    # Sort by match date
    filtered_matches = sorted(filtered_matches, key=lambda m: m.match_date)

    return MatchListResponse(
        matches=filtered_matches,
        total=len(filtered_matches),
        page=1,
        per_page=len(filtered_matches),
    )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int) -> MatchResponse:
    """Get details for a specific match."""
    match = next((m for m in _mock_matches if m.id == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return match


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
