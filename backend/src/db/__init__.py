"""Database module with SQLAlchemy 2.0 async ORM.

This module provides:
- Models: SQLAlchemy ORM models for all database tables
- Repositories: Repository pattern for data access
- Unit of Work: Transaction management pattern
- Database utilities: Session management and initialization

Usage:
    from src.db import get_uow, Team, Match

    async with get_uow() as uow:
        teams = await uow.teams.get_all()
        await uow.commit()
"""

from src.db.database import async_session_factory, get_db, get_session, init_db
from src.db.models import (
    Base,
    CachedData,
    Competition,
    Match,
    MLModel,
    NewsItem,
    NotificationLog,
    Prediction,
    PredictionResult,
    PushSubscription,
    Standing,
    SyncLog,
    Team,
    UserBankroll,
    UserBet,
    UserFavorite,
    UserPreferences,
    UserStats,
)
from src.db.repositories import (
    MatchRepository,
    MLModelRepository,
    PredictionRepository,
    PredictionResultRepository,
    StandingRepository,
    SyncLogRepository,
    TeamRepository,
    UnitOfWork,
    get_uow,
)

__all__ = [
    # Database utilities
    "async_session_factory",
    "get_db",
    "get_session",
    "init_db",
    # Base
    "Base",
    # Models
    "CachedData",
    "Competition",
    "Match",
    "MLModel",
    "NewsItem",
    "NotificationLog",
    "Prediction",
    "PredictionResult",
    "PushSubscription",
    "Standing",
    "SyncLog",
    "Team",
    "UserBankroll",
    "UserBet",
    "UserFavorite",
    "UserPreferences",
    "UserStats",
    # Repositories
    "MatchRepository",
    "MLModelRepository",
    "PredictionRepository",
    "PredictionResultRepository",
    "StandingRepository",
    "SyncLogRepository",
    "TeamRepository",
    # Unit of Work
    "UnitOfWork",
    "get_uow",
]
