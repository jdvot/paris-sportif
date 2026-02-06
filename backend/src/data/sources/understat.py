"""Understat client for fetching xG (expected goals) data.

Understat provides free xG data for top 5 European leagues.
Uses the 'understat' Python library.
"""

import asyncio
import logging
from typing import Any

from understat import Understat

logger = logging.getLogger(__name__)

# League mappings: our code -> Understat league name
LEAGUE_MAPPING = {
    "PL": "epl",  # English Premier League
    "PD": "La_liga",  # Spanish La Liga
    "BL1": "Bundesliga",  # German Bundesliga
    "SA": "Serie_A",  # Italian Serie A
    "FL1": "Ligue_1",  # French Ligue 1
}


class UnderstatClient:
    """Client for fetching xG data from Understat."""

    def __init__(self):
        self.understat = Understat()

    async def get_team_xg(
        self, team_name: str, league_code: str, season: str = "2025"
    ) -> dict[str, float] | None:
        """
        Get xG stats for a team.

        Args:
            team_name: Team name (e.g., "Manchester City")
            league_code: Our league code (PL, PD, BL1, SA, FL1)
            season: Season year (e.g., "2025" for 2025-26)

        Returns:
            Dict with xG stats or None if not found
        """
        league = LEAGUE_MAPPING.get(league_code)
        if not league:
            logger.warning(f"League {league_code} not supported by Understat")
            return None

        try:
            async with self.understat as understat:
                # Get league teams
                teams = await understat.get_teams(league, season)

                # Find team by name (fuzzy match)
                team_data = None
                team_name_lower = team_name.lower()
                for team in teams:
                    if (
                        team_name_lower in team["title"].lower()
                        or team["title"].lower() in team_name_lower
                    ):
                        team_data = team
                        break

                if not team_data:
                    logger.debug(f"Team {team_name} not found in Understat for {league}")
                    return None

                # Extract xG stats
                history = team_data.get("history", [])
                if not history:
                    return None

                # Calculate averages from recent matches
                recent_matches = history[-10:] if len(history) >= 10 else history
                total_xg = sum(float(m.get("xG", 0)) for m in recent_matches)
                total_xga = sum(float(m.get("xGA", 0)) for m in recent_matches)
                match_count = len(recent_matches)

                if match_count == 0:
                    return None

                return {
                    "avg_xg_for": round(total_xg / match_count, 3),
                    "avg_xg_against": round(total_xga / match_count, 3),
                    "matches_analyzed": match_count,
                }

        except Exception as e:
            logger.error(f"Error fetching xG for {team_name}: {e}")
            return None

    async def update_all_teams_xg(self, teams: list[dict[str, Any]]) -> int:
        """
        Update xG stats for all teams.

        Args:
            teams: List of team dicts with 'id', 'name', 'country'

        Returns:
            Number of teams updated
        """
        from sqlalchemy import text

        from src.db import get_db_context

        updated = 0

        # Group teams by league
        league_teams: dict[str, list[dict]] = {}
        for team in teams:
            # Map country to league code
            country = team.get("country", "").upper()
            league_code = {
                "ENGLAND": "PL",
                "SPAIN": "PD",
                "GERMANY": "BL1",
                "ITALY": "SA",
                "FRANCE": "FL1",
            }.get(country)

            if league_code:
                if league_code not in league_teams:
                    league_teams[league_code] = []
                league_teams[league_code].append(team)

        # Fetch xG for each league
        for league_code, league_team_list in league_teams.items():
            logger.info(f"Fetching xG data for {len(league_team_list)} teams in {league_code}...")

            for team in league_team_list:
                try:
                    xg_data = await self.get_team_xg(team["name"], league_code)
                    if xg_data:
                        with get_db_context() as db:
                            db.execute(
                                text(
                                    """
                                    UPDATE teams
                                    SET avg_xg_for = :xg_for,
                                        avg_xg_against = :xg_against,
                                        updated_at = NOW()
                                    WHERE id = :team_id
                                """
                                ),
                                {
                                    "xg_for": xg_data["avg_xg_for"],
                                    "xg_against": xg_data["avg_xg_against"],
                                    "team_id": team["id"],
                                },
                            )
                            db.commit()
                        updated += 1
                        logger.debug(f"Updated xG for {team['name']}: {xg_data}")

                    # Rate limit: don't hammer Understat
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Failed to update xG for {team['name']}: {e}")

        logger.info(f"Updated xG for {updated} teams")
        return updated


# Singleton
_client: UnderstatClient | None = None


def get_understat_client() -> UnderstatClient:
    """Get Understat client singleton."""
    global _client
    if _client is None:
        _client = UnderstatClient()
    return _client


async def sync_all_xg_data() -> int:
    """
    Sync xG data for all teams in the database.

    Returns number of teams updated.
    """
    from sqlalchemy import text

    from src.db import get_db_context

    # Get all teams
    with get_db_context() as db:
        result = db.execute(text("SELECT id, name, country FROM teams"))
        teams = [{"id": r[0], "name": r[1], "country": r[2]} for r in result.fetchall()]

    if not teams:
        logger.warning("No teams found in database")
        return 0

    client = get_understat_client()
    return await client.update_all_teams_xg(teams)
