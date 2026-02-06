"""Standing repository with domain-specific operations."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Standing
from src.db.repositories.base import BaseRepository


class StandingRepository(BaseRepository[Standing]):
    """Repository for Standing operations with domain-specific methods."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Standing, session)

    async def get_by_competition(
        self,
        competition_code: str,
        *,
        season: str | None = None,
    ) -> Sequence[Standing]:
        """Get standings for a competition ordered by position."""
        stmt = select(Standing).where(Standing.competition_code == competition_code)
        if season:
            stmt = stmt.where(Standing.season == season)
        stmt = stmt.order_by(Standing.position.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_team_standing(
        self,
        team_id: int,
        competition_code: str | None = None,
    ) -> Standing | None:
        """Get standing for a specific team, optionally filtered by competition."""
        stmt = select(Standing).where(Standing.team_id == team_id)
        if competition_code:
            stmt = stmt.where(Standing.competition_code == competition_code)
        # Order by most recent sync
        stmt = stmt.order_by(Standing.synced_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_team_name(
        self,
        team_name: str,
        competition_code: str | None = None,
    ) -> Standing | None:
        """Get standing by team name (fallback for ID mismatches)."""
        stmt = select(Standing).where(Standing.team_name.ilike(f"%{team_name}%"))
        if competition_code:
            stmt = stmt.where(Standing.competition_code == competition_code)
        stmt = stmt.order_by(Standing.synced_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_top_n(
        self,
        competition_code: str,
        n: int = 4,
    ) -> Sequence[Standing]:
        """Get top N teams in a competition."""
        stmt = (
            select(Standing)
            .where(Standing.competition_code == competition_code)
            .order_by(Standing.position.asc())
            .limit(n)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_relegation_zone(
        self,
        competition_code: str,
        relegation_spots: int = 3,
    ) -> Sequence[Standing]:
        """Get teams in relegation zone."""
        stmt = (
            select(Standing)
            .where(Standing.competition_code == competition_code)
            .order_by(Standing.position.desc())
            .limit(relegation_spots)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def replace_competition_standings(
        self,
        competition_code: str,
        standings_data: list[dict],
        *,
        season: str | None = None,
    ) -> int:
        """Replace all standings for a competition with new data."""
        # Delete existing standings
        del_stmt = delete(Standing).where(Standing.competition_code == competition_code)
        if season:
            del_stmt = del_stmt.where(Standing.season == season)
        await self.session.execute(del_stmt)

        # Insert new standings
        synced_at = datetime.now()
        count = 0
        for data in standings_data:
            standing = Standing(
                competition_code=competition_code,
                season=season,
                position=data.get("position"),
                team_id=data.get("team_id"),
                team_name=data.get("team_name"),
                team_logo=data.get("team_logo"),
                played_games=data.get("played_games", 0),
                won=data.get("won", 0),
                drawn=data.get("drawn", 0),
                lost=data.get("lost", 0),
                goals_for=data.get("goals_for", 0),
                goals_against=data.get("goals_against", 0),
                goal_difference=data.get("goal_difference", 0),
                points=data.get("points", 0),
                form=data.get("form"),
                synced_at=synced_at,
            )
            self.session.add(standing)
            count += 1

        await self.session.flush()
        return count

    async def upsert_standing(
        self,
        competition_code: str,
        team_id: int,
        **data,
    ) -> Standing:
        """Insert or update a standing entry."""
        existing = await self.get_team_standing(team_id, competition_code)
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.synced_at = datetime.now()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        standing = Standing(
            competition_code=competition_code,
            team_id=team_id,
            synced_at=datetime.now(),
            **data,
        )
        self.session.add(standing)
        await self.session.flush()
        await self.session.refresh(standing)
        return standing

    async def get_all_competitions(self) -> list[str]:
        """Get list of all competition codes with standings."""
        stmt = select(Standing.competition_code).distinct()
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
