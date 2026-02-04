"""Unit of Work pattern for transaction management.

Provides a single entry point for all repository operations with
automatic transaction handling.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.match_repository import MatchRepository
from src.db.repositories.ml_model_repository import MLModelRepository
from src.db.repositories.prediction_repository import (
    PredictionRepository,
    PredictionResultRepository,
)
from src.db.repositories.standing_repository import StandingRepository
from src.db.repositories.sync_repository import SyncLogRepository
from src.db.repositories.team_repository import TeamRepository
from src.db.repositories.user_repository import (
    PushSubscriptionRepository,
    UserBetRepository,
    UserFavoriteRepository,
    UserPreferencesRepository,
    UserStatsRepository,
)


class UnitOfWork:
    """Unit of Work for managing database transactions.

    Usage:
        async with UnitOfWork(session) as uow:
            team = await uow.teams.get_by_id(1)
            match = await uow.matches.create(home_team_id=1, ...)
            await uow.commit()

    The UoW provides access to all repositories and handles commit/rollback.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._teams: TeamRepository | None = None
        self._matches: MatchRepository | None = None
        self._predictions: PredictionRepository | None = None
        self._prediction_results: PredictionResultRepository | None = None
        self._standings: StandingRepository | None = None
        self._sync_logs: SyncLogRepository | None = None
        self._ml_models: MLModelRepository | None = None
        self._user_bets: UserBetRepository | None = None
        self._user_favorites: UserFavoriteRepository | None = None
        self._user_preferences: UserPreferencesRepository | None = None
        self._user_stats: UserStatsRepository | None = None
        self._push_subscriptions: PushSubscriptionRepository | None = None

    @property
    def session(self) -> AsyncSession:
        """Direct access to the session for custom queries."""
        return self._session

    @property
    def teams(self) -> TeamRepository:
        """Team repository."""
        if self._teams is None:
            self._teams = TeamRepository(self._session)
        return self._teams

    @property
    def matches(self) -> MatchRepository:
        """Match repository."""
        if self._matches is None:
            self._matches = MatchRepository(self._session)
        return self._matches

    @property
    def predictions(self) -> PredictionRepository:
        """Prediction repository."""
        if self._predictions is None:
            self._predictions = PredictionRepository(self._session)
        return self._predictions

    @property
    def prediction_results(self) -> PredictionResultRepository:
        """Prediction result repository."""
        if self._prediction_results is None:
            self._prediction_results = PredictionResultRepository(self._session)
        return self._prediction_results

    @property
    def standings(self) -> StandingRepository:
        """Standing repository."""
        if self._standings is None:
            self._standings = StandingRepository(self._session)
        return self._standings

    @property
    def sync_logs(self) -> SyncLogRepository:
        """Sync log repository."""
        if self._sync_logs is None:
            self._sync_logs = SyncLogRepository(self._session)
        return self._sync_logs

    @property
    def ml_models(self) -> MLModelRepository:
        """ML model repository."""
        if self._ml_models is None:
            self._ml_models = MLModelRepository(self._session)
        return self._ml_models

    @property
    def user_bets(self) -> UserBetRepository:
        """User bet repository."""
        if self._user_bets is None:
            self._user_bets = UserBetRepository(self._session)
        return self._user_bets

    @property
    def user_favorites(self) -> UserFavoriteRepository:
        """User favorites repository."""
        if self._user_favorites is None:
            self._user_favorites = UserFavoriteRepository(self._session)
        return self._user_favorites

    @property
    def user_preferences(self) -> UserPreferencesRepository:
        """User preferences repository."""
        if self._user_preferences is None:
            self._user_preferences = UserPreferencesRepository(self._session)
        return self._user_preferences

    @property
    def user_stats(self) -> UserStatsRepository:
        """User stats repository."""
        if self._user_stats is None:
            self._user_stats = UserStatsRepository(self._session)
        return self._user_stats

    @property
    def push_subscriptions(self) -> PushSubscriptionRepository:
        """Push subscriptions repository."""
        if self._push_subscriptions is None:
            self._push_subscriptions = PushSubscriptionRepository(self._session)
        return self._push_subscriptions

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        await self._session.flush()

    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager, rolling back on exception."""
        if exc_type is not None:
            await self.rollback()
        await self._session.close()


@asynccontextmanager
async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Get a Unit of Work instance with a new session.

    Usage:
        async with get_uow() as uow:
            team = await uow.teams.get_by_id(1)
            await uow.commit()
    """
    from src.db.database import async_session_factory

    async with async_session_factory() as session:
        async with UnitOfWork(session) as uow:
            yield uow
