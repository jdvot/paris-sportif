"""Database services layer.

Provides high-level service functions that use the repository pattern
internally. These can be used as drop-in replacements for legacy
database functions during migration.
"""

from src.db.services.match_service import MatchService, StandingService, SyncService
from src.db.services.prediction_service import PredictionService
from src.db.services.stats_service import StatsService, SyncServiceAsync
from src.db.services.user_service import (
    BetService,
    FavoriteService,
    PreferencesService,
    PushSubscriptionService,
)

__all__ = [
    # Match services
    "MatchService",
    "StandingService",
    "SyncService",
    # Prediction services
    "PredictionService",
    # Stats services
    "StatsService",
    "SyncServiceAsync",
    # User services
    "BetService",
    "FavoriteService",
    "PreferencesService",
    "PushSubscriptionService",
]
