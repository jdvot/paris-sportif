"""Fatigue data service for fetching and calculating team fatigue metrics.

This service bridges the football-data.org API with the feature engineering module
to provide fatigue metrics (rest days, fixture congestion) for predictions.

Part of ML-007: Integrate fatigue data from API.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.data.sources.football_data import FootballDataClient, MatchData, get_football_data_client
from src.prediction_engine.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


@dataclass
class TeamFatigueData:
    """Fatigue data for a single team."""

    team_id: int
    team_name: str
    last_match_date: datetime | None = None
    recent_match_dates: list[datetime] | None = None
    # Normalized fatigue scores (0 = fatigued, 1 = well-rested)
    rest_days_score: float = 0.5
    fixture_congestion_score: float = 0.5

    @property
    def combined_fatigue_score(self) -> float:
        """Combined fatigue score (average of rest and congestion)."""
        return (self.rest_days_score + self.fixture_congestion_score) / 2


@dataclass
class MatchFatigueData:
    """Fatigue data for both teams in a match."""

    home_team: TeamFatigueData
    away_team: TeamFatigueData
    match_date: datetime

    @property
    def fatigue_advantage(self) -> float:
        """
        Home team's fatigue advantage.

        Positive = home team is more rested.
        Range: -1.0 to 1.0
        """
        return self.home_team.combined_fatigue_score - self.away_team.combined_fatigue_score


class FatigueService:
    """
    Service for fetching and calculating team fatigue data.

    Uses football-data.org API to get recent match schedules
    and calculates fatigue metrics using FeatureEngineer.
    """

    # Number of days to look back for fixture congestion
    CONGESTION_WINDOW_DAYS = 14

    # Number of recent matches to fetch per team
    RECENT_MATCHES_LIMIT = 10

    def __init__(self, client: FootballDataClient | None = None):
        """
        Initialize the fatigue service.

        Args:
            client: Optional FootballDataClient instance.
                   Uses default client if not provided.
        """
        self._client = client

    def _get_client(self) -> FootballDataClient:
        """Get or create the football data client."""
        if self._client is None:
            self._client = get_football_data_client()
        return self._client

    async def get_team_fatigue(
        self,
        team_id: int,
        team_name: str,
        match_date: datetime | str | None = None,
    ) -> TeamFatigueData:
        """
        Get fatigue data for a single team.

        Args:
            team_id: Football-data.org team ID
            team_name: Team name (for logging)
            match_date: Date of the upcoming match (for calculating rest)

        Returns:
            TeamFatigueData with calculated fatigue metrics
        """
        if match_date is None:
            match_date = datetime.now()
        elif isinstance(match_date, str):
            try:
                match_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                # Make timezone-naive for comparison
                match_date = match_date.replace(tzinfo=None)
            except ValueError:
                match_date = datetime.now()

        try:
            client = self._get_client()

            # Fetch recent finished matches for the team
            matches = await client.get_team_matches(
                team_id=team_id,
                status="FINISHED",
                limit=self.RECENT_MATCHES_LIMIT,
            )

            if not matches:
                logger.warning(f"No recent matches found for team {team_name} (ID: {team_id})")
                return TeamFatigueData(
                    team_id=team_id,
                    team_name=team_name,
                )

            # Extract match dates
            match_dates = self._extract_match_dates(matches)

            if not match_dates:
                return TeamFatigueData(
                    team_id=team_id,
                    team_name=team_name,
                )

            # Sort by most recent first
            match_dates.sort(reverse=True)
            last_match_date = match_dates[0]

            # Calculate fatigue scores
            rest_days_score = FeatureEngineer.calculate_rest_days(
                last_match_date=last_match_date,
                current_match_date=match_date,
            )

            fixture_congestion_score = FeatureEngineer.calculate_fixture_congestion(
                recent_match_dates=match_dates,
                current_match_date=match_date,
                window_days=self.CONGESTION_WINDOW_DAYS,
            )

            logger.debug(
                f"Fatigue for {team_name}: rest={rest_days_score:.2f}, "
                f"congestion={fixture_congestion_score:.2f}"
            )

            return TeamFatigueData(
                team_id=team_id,
                team_name=team_name,
                last_match_date=last_match_date,
                recent_match_dates=match_dates,
                rest_days_score=rest_days_score,
                fixture_congestion_score=fixture_congestion_score,
            )

        except Exception as e:
            logger.error(f"Error fetching fatigue data for {team_name}: {e}")
            return TeamFatigueData(
                team_id=team_id,
                team_name=team_name,
            )

    async def get_match_fatigue(
        self,
        home_team_id: int,
        home_team_name: str,
        away_team_id: int,
        away_team_name: str,
        match_date: datetime | str | None = None,
    ) -> MatchFatigueData:
        """
        Get fatigue data for both teams in a match.

        Args:
            home_team_id: Football-data.org ID for home team
            home_team_name: Home team name
            away_team_id: Football-data.org ID for away team
            away_team_name: Away team name
            match_date: Date of the upcoming match

        Returns:
            MatchFatigueData with fatigue metrics for both teams
        """
        if match_date is None:
            match_date = datetime.now()
        elif isinstance(match_date, str):
            try:
                match_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                match_date = match_date.replace(tzinfo=None)
            except ValueError:
                match_date = datetime.now()

        # Fetch fatigue data for both teams concurrently
        import asyncio

        home_fatigue_task = self.get_team_fatigue(
            team_id=home_team_id,
            team_name=home_team_name,
            match_date=match_date,
        )
        away_fatigue_task = self.get_team_fatigue(
            team_id=away_team_id,
            team_name=away_team_name,
            match_date=match_date,
        )

        home_fatigue, away_fatigue = await asyncio.gather(
            home_fatigue_task,
            away_fatigue_task,
        )

        return MatchFatigueData(
            home_team=home_fatigue,
            away_team=away_fatigue,
            match_date=match_date,
        )

    def _extract_match_dates(self, matches: list[MatchData]) -> list[datetime]:
        """
        Extract datetime objects from match data.

        Args:
            matches: List of MatchData from the API

        Returns:
            List of datetime objects for each match
        """
        dates = []
        for match in matches:
            try:
                # Parse ISO format date string
                match_date = datetime.fromisoformat(match.utcDate.replace("Z", "+00:00"))
                # Make timezone-naive for comparison
                match_date = match_date.replace(tzinfo=None)
                dates.append(match_date)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse match date: {match.utcDate} - {e}")
                continue
        return dates


# Singleton instance for convenience
_fatigue_service: FatigueService | None = None


def get_fatigue_service() -> FatigueService:
    """Get the singleton FatigueService instance."""
    global _fatigue_service
    if _fatigue_service is None:
        _fatigue_service = FatigueService()
    return _fatigue_service
