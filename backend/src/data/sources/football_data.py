"""Client for football-data.org API.

Free tier: 10 requests/minute
Documentation: https://www.football-data.org/documentation/api
"""

from datetime import date, datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import FootballDataAPIError, RateLimitError


class TeamData(BaseModel):
    """Team data from API."""

    id: int
    name: str
    shortName: str | None = None
    tla: str | None = None
    crest: str | None = None


class CompetitionData(BaseModel):
    """Competition data from API."""

    id: int
    name: str
    code: str
    emblem: str | None = None


class ScoreData(BaseModel):
    """Score data from API."""

    home: int | None = None
    away: int | None = None


class MatchData(BaseModel):
    """Match data from API."""

    id: int
    competition: CompetitionData
    homeTeam: TeamData
    awayTeam: TeamData
    utcDate: str
    status: str
    matchday: int | None = None
    score: dict[str, ScoreData | None] = {}


class StandingTeam(BaseModel):
    """Team in standings."""

    position: int
    team: TeamData
    playedGames: int
    won: int
    draw: int
    lost: int
    points: int
    goalsFor: int
    goalsAgainst: int
    goalDifference: int


# Supported competitions
COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "EL": "Europa League",
}


class FootballDataClient:
    """Client for football-data.org API."""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.football_data_api_key
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                timeout=30.0,
            )

            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded for football-data.org",
                    details={"retry_after": response.headers.get("Retry-After")},
                )

            if response.status_code != 200:
                raise FootballDataAPIError(
                    f"API error: {response.status_code}",
                    details={"response": response.text},
                )

            return response.json()

    async def get_competitions(self) -> list[dict[str, Any]]:
        """Get list of available competitions."""
        data = await self._request("GET", "/competitions")
        return data.get("competitions", [])

    async def get_competition(self, code: str) -> dict[str, Any]:
        """Get competition details."""
        data = await self._request("GET", f"/competitions/{code}")
        return data

    async def get_matches(
        self,
        competition: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: Literal["SCHEDULED", "LIVE", "FINISHED"] | None = None,
        matchday: int | None = None,
    ) -> list[MatchData]:
        """
        Get matches with optional filters.

        Args:
            competition: Competition code (PL, PD, BL1, SA, FL1, CL, EL)
            date_from: Start date
            date_to: End date
            status: Match status filter
            matchday: Matchday number
        """
        params: dict[str, Any] = {}

        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()
        if status:
            params["status"] = status
        if matchday:
            params["matchday"] = matchday

        if competition:
            endpoint = f"/competitions/{competition}/matches"
        else:
            # Get matches across all competitions
            endpoint = "/matches"
            if not competition:
                # Filter to our supported competitions
                params["competitions"] = ",".join(COMPETITIONS.keys())

        data = await self._request("GET", endpoint, params)
        matches = data.get("matches", [])

        return [MatchData(**m) for m in matches]

    async def get_match(self, match_id: int) -> MatchData:
        """Get single match details."""
        data = await self._request("GET", f"/matches/{match_id}")
        return MatchData(**data)

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """Get team details."""
        data = await self._request("GET", f"/teams/{team_id}")
        return data

    async def get_team_matches(
        self,
        team_id: int,
        status: Literal["SCHEDULED", "LIVE", "FINISHED"] | None = None,
        limit: int = 10,
    ) -> list[MatchData]:
        """Get matches for a specific team."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status

        data = await self._request("GET", f"/teams/{team_id}/matches", params)
        matches = data.get("matches", [])

        return [MatchData(**m) for m in matches]

    async def get_standings(self, competition: str) -> list[StandingTeam]:
        """Get current standings for a competition."""
        data = await self._request("GET", f"/competitions/{competition}/standings")

        standings = []
        for standing_group in data.get("standings", []):
            if standing_group.get("type") == "TOTAL":
                for team_standing in standing_group.get("table", []):
                    standings.append(StandingTeam(**team_standing))
                break

        return standings

    async def get_head_to_head(
        self,
        match_id: int,
        limit: int = 10,
    ) -> list[MatchData]:
        """Get head-to-head history for teams in a match."""
        data = await self._request(
            "GET",
            f"/matches/{match_id}/head2head",
            params={"limit": limit},
        )

        matches = data.get("matches", [])
        return [MatchData(**m) for m in matches]

    async def get_upcoming_matches(
        self,
        days: int = 2,
        competition: str | None = None,
    ) -> list[MatchData]:
        """Get upcoming matches for the next N days."""
        from datetime import timedelta

        today = date.today()
        date_to = today + timedelta(days=days)

        return await self.get_matches(
            competition=competition,
            date_from=today,
            date_to=date_to,
            status="SCHEDULED",
        )


def get_football_data_client() -> FootballDataClient:
    """
    Get FootballDataClient instance with current settings.

    Creates a fresh instance each call to ensure the API key is always
    loaded from current environment variables. This solves the issue where
    a module-level singleton would be initialized before environment
    variables are properly loaded during application startup.

    Returns:
        FootballDataClient: New client instance with current API key
    """
    return FootballDataClient()
