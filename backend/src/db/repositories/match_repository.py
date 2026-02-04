"""Match repository with domain-specific operations."""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.db.models import Match, Prediction
from src.db.repositories.base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    """Repository for Match operations with domain-specific methods."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Match, session)

    async def get_by_external_id(self, external_id: str) -> Match | None:
        """Get match by external API ID."""
        return await self.get_by_field("external_id", external_id)

    async def get_with_teams(self, match_id: int) -> Match | None:
        """Get match with home and away teams loaded."""
        stmt = (
            select(Match)
            .options(joinedload(Match.home_team), joinedload(Match.away_team))
            .where(Match.id == match_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_prediction(self, match_id: int) -> Match | None:
        """Get match with prediction loaded."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.prediction),
            )
            .where(Match.id == match_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self,
        date_from: date,
        date_to: date,
        *,
        competition_id: int | None = None,
        status: str | None = None,
    ) -> Sequence[Match]:
        """Get matches within a date range with optional filters."""
        stmt = select(Match).where(
            and_(
                Match.match_date >= datetime.combine(date_from, datetime.min.time()),
                Match.match_date <= datetime.combine(date_to, datetime.max.time()),
            )
        )
        if competition_id:
            stmt = stmt.where(Match.competition_id == competition_id)
        if status:
            stmt = stmt.where(Match.status == status)
        stmt = stmt.order_by(Match.match_date.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_scheduled(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        competition_id: int | None = None,
    ) -> Sequence[Match]:
        """Get scheduled (upcoming) matches."""
        statuses = ["scheduled", "timed", "SCHEDULED", "TIMED"]
        stmt = select(Match).where(Match.status.in_(statuses))
        if date_from:
            stmt = stmt.where(Match.match_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            stmt = stmt.where(Match.match_date <= datetime.combine(date_to, datetime.max.time()))
        if competition_id:
            stmt = stmt.where(Match.competition_id == competition_id)
        stmt = stmt.order_by(Match.match_date.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_finished_unverified(self) -> Sequence[Match]:
        """Get finished matches that have predictions but not verified yet."""
        stmt = (
            select(Match)
            .join(Prediction, Prediction.match_id == Match.id)
            .where(
                and_(
                    Match.status.in_(["FINISHED", "finished"]),
                    Match.home_score.isnot(None),
                    Match.away_score.isnot(None),
                )
            )
            .options(joinedload(Match.prediction))
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get_by_competition(
        self,
        competition_id: int,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> Sequence[Match]:
        """Get matches for a competition."""
        stmt = select(Match).where(Match.competition_id == competition_id)
        if status:
            stmt = stmt.where(Match.status == status)
        stmt = stmt.order_by(Match.match_date.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_head_to_head(
        self,
        team1_id: int,
        team2_id: int,
        *,
        limit: int = 10,
    ) -> Sequence[Match]:
        """Get head-to-head matches between two teams."""
        stmt = (
            select(Match)
            .where(
                ((Match.home_team_id == team1_id) & (Match.away_team_id == team2_id))
                | ((Match.home_team_id == team2_id) & (Match.away_team_id == team1_id))
            )
            .where(Match.status.in_(["FINISHED", "finished"]))
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_team_recent_matches(
        self,
        team_id: int,
        *,
        limit: int = 10,
        home_only: bool = False,
        away_only: bool = False,
    ) -> Sequence[Match]:
        """Get recent finished matches for a team."""
        stmt = select(Match).where(Match.status.in_(["FINISHED", "finished"]))
        if home_only:
            stmt = stmt.where(Match.home_team_id == team_id)
        elif away_only:
            stmt = stmt.where(Match.away_team_id == team_id)
        else:
            stmt = stmt.where((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
        stmt = stmt.order_by(Match.match_date.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_result(
        self,
        match_id: int,
        home_score: int,
        away_score: int,
        *,
        home_score_ht: int | None = None,
        away_score_ht: int | None = None,
    ) -> Match | None:
        """Update match result."""
        return await self.update(
            match_id,
            home_score=home_score,
            away_score=away_score,
            home_score_ht=home_score_ht,
            away_score_ht=away_score_ht,
            status="FINISHED",
        )

    async def bulk_upsert(self, matches_data: list[dict]) -> int:
        """Bulk upsert matches from API data."""
        count = 0
        for data in matches_data:
            external_id = data.get("external_id")
            if not external_id:
                continue
            await self.upsert("external_id", external_id, **data)
            count += 1
        return count
