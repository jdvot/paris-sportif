"""Repository layer for database operations.

This module implements the Repository Pattern with Unit of Work for
clean separation of data access logic from business logic.

Usage:
    from src.db.repositories import get_uow

    async with get_uow() as uow:
        # Access repositories via UoW
        team = await uow.teams.get_by_id(1)
        matches = await uow.matches.get_by_date_range(date_from, date_to)

        # Create new records
        prediction = await uow.predictions.create(match_id=1, ...)

        # Commit transaction
        await uow.commit()
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.match_repository import MatchRepository
from src.db.repositories.ml_model_repository import MLModelRepository
from src.db.repositories.prediction_repository import (
    PredictionRepository,
    PredictionResultRepository,
)
from src.db.repositories.standing_repository import StandingRepository
from src.db.repositories.sync_repository import SyncLogRepository
from src.db.repositories.team_repository import TeamRepository
from src.db.repositories.unit_of_work import UnitOfWork, get_uow
from src.db.repositories.user_repository import (
    PushSubscriptionRepository,
    UserBetRepository,
    UserFavoriteRepository,
    UserPreferencesRepository,
    UserStatsRepository,
)

__all__ = [
    # Base
    "BaseRepository",
    # Repositories
    "MatchRepository",
    "MLModelRepository",
    "PredictionRepository",
    "PredictionResultRepository",
    "StandingRepository",
    "SyncLogRepository",
    "TeamRepository",
    "PushSubscriptionRepository",
    "UserBetRepository",
    "UserFavoriteRepository",
    "UserPreferencesRepository",
    "UserStatsRepository",
    # Unit of Work
    "UnitOfWork",
    "get_uow",
]
