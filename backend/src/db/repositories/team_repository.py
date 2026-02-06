"""Team repository with domain-specific operations."""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Match, Team
from src.db.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for Team operations with domain-specific methods."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Team, session)

    async def get_by_external_id(self, external_id: str) -> Team | None:
        """Get team by external API ID."""
        return await self.get_by_field("external_id", external_id)

    async def get_by_name(self, name: str) -> Team | None:
        """Get team by name (case-insensitive search)."""
        stmt = select(Team).where(func.lower(Team.name) == func.lower(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_name(self, query: str, *, limit: int = 10) -> Sequence[Team]:
        """Search teams by partial name match."""
        stmt = (
            select(Team)
            .where(func.lower(Team.name).contains(func.lower(query)))
            .order_by(Team.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name_fuzzy(self, name: str) -> Team | None:
        """Get team by fuzzy name match (handles variations like FC, 1., etc.)."""
        # Try exact match first
        team = await self.get_by_name(name)
        if team:
            return team

        # Try without common prefixes/suffixes
        clean_name = name
        for prefix in [
            "FC ",
            "1. FC ",
            "1. ",
            "AC ",
            "AS ",
            "SS ",
            "SC ",
            "SV ",
            "VfB ",
            "VfL ",
            "TSG ",
            "RB ",
        ]:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix) :]
                break

        if clean_name != name:
            team = await self.get_by_name(clean_name)
            if team:
                return team

        # Try partial match (contains)
        teams = await self.search_by_name(name, limit=1)
        if teams:
            return teams[0]

        # Try with core name (first significant word)
        words = name.split()
        for word in words:
            if len(word) > 3 and word.lower() not in ["the", "club", "football"]:
                teams = await self.search_by_name(word, limit=1)
                if teams:
                    return teams[0]

        return None

    async def get_by_country(self, country: str) -> Sequence[Team]:
        """Get all teams from a country."""
        return await self.get_many_by_field("country", country)

    async def get_by_tla(self, tla: str) -> Team | None:
        """Get team by TLA (three-letter abbreviation)."""
        return await self.get_by_field("tla", tla.upper())

    async def update_elo(self, team_id: int, new_elo: Decimal) -> Team | None:
        """Update team's ELO rating."""
        return await self.update(team_id, elo_rating=new_elo)

    async def update_stats_cache(
        self,
        team_id: int,
        *,
        avg_goals_scored_home: Decimal | None = None,
        avg_goals_scored_away: Decimal | None = None,
        avg_goals_conceded_home: Decimal | None = None,
        avg_goals_conceded_away: Decimal | None = None,
        avg_xg_for: Decimal | None = None,
        avg_xg_against: Decimal | None = None,
    ) -> Team | None:
        """Update team's stats cache."""
        update_data = {}
        if avg_goals_scored_home is not None:
            update_data["avg_goals_scored_home"] = avg_goals_scored_home
        if avg_goals_scored_away is not None:
            update_data["avg_goals_scored_away"] = avg_goals_scored_away
        if avg_goals_conceded_home is not None:
            update_data["avg_goals_conceded_home"] = avg_goals_conceded_home
        if avg_goals_conceded_away is not None:
            update_data["avg_goals_conceded_away"] = avg_goals_conceded_away
        if avg_xg_for is not None:
            update_data["avg_xg_for"] = avg_xg_for
        if avg_xg_against is not None:
            update_data["avg_xg_against"] = avg_xg_against

        if not update_data:
            return await self.get_by_id(team_id)

        return await self.update(team_id, **update_data)

    async def get_top_by_elo(self, *, limit: int = 20) -> Sequence[Team]:
        """Get teams with highest ELO ratings."""
        stmt = select(Team).order_by(Team.elo_rating.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def calculate_team_stats(self, team_id: int, *, last_n_matches: int = 10) -> dict:
        """Calculate team statistics from recent matches."""
        # Get home matches
        home_stmt = (
            select(
                func.count(Match.id).label("matches"),
                func.avg(Match.home_score).label("avg_scored"),
                func.avg(Match.away_score).label("avg_conceded"),
            )
            .where(Match.home_team_id == team_id)
            .where(Match.status.in_(["FINISHED", "finished"]))
            .where(Match.home_score.isnot(None))
            .limit(last_n_matches)
        )
        home_result = await self.session.execute(home_stmt)
        home_stats = home_result.one()

        # Get away matches
        away_stmt = (
            select(
                func.count(Match.id).label("matches"),
                func.avg(Match.away_score).label("avg_scored"),
                func.avg(Match.home_score).label("avg_conceded"),
            )
            .where(Match.away_team_id == team_id)
            .where(Match.status.in_(["FINISHED", "finished"]))
            .where(Match.away_score.isnot(None))
            .limit(last_n_matches)
        )
        away_result = await self.session.execute(away_stmt)
        away_stats = away_result.one()

        return {
            "home_matches": home_stats.matches or 0,
            "home_avg_scored": float(home_stats.avg_scored or 0),
            "home_avg_conceded": float(home_stats.avg_conceded or 0),
            "away_matches": away_stats.matches or 0,
            "away_avg_scored": float(away_stats.avg_scored or 0),
            "away_avg_conceded": float(away_stats.avg_conceded or 0),
        }

    async def bulk_upsert(self, teams_data: list[dict]) -> int:
        """Bulk upsert teams from API data."""
        count = 0
        for data in teams_data:
            external_id = data.get("external_id")
            if not external_id:
                continue
            await self.upsert("external_id", external_id, **data)
            count += 1
        return count
