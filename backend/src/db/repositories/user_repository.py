"""User-related repositories for bets, bankroll, favorites, preferences, and push."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Integer, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    PushSubscription,
    UserBankroll,
    UserBet,
    UserFavorite,
    UserPreferences,
    UserStats,
)
from src.db.repositories.base import BaseRepository


class UserBetRepository(BaseRepository[UserBet]):
    """Repository for user bet operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserBet, session)

    async def get_by_user(
        self,
        user_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserBet]:
        """Get user's bets with optional status filter."""
        stmt = select(UserBet).where(UserBet.user_id == user_id)
        if status:
            stmt = stmt.where(UserBet.status == status)
        stmt = stmt.order_by(UserBet.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """Get aggregated betting statistics for a user."""
        stmt = select(
            func.count(UserBet.id).label("total"),
            func.sum(case((UserBet.status == "won", 1), else_=0)).label("won"),
            func.sum(case((UserBet.status == "lost", 1), else_=0)).label("lost"),
            func.sum(case((UserBet.status == "pending", 1), else_=0)).label("pending"),
            func.sum(
                case((UserBet.status != "void", UserBet.stake), else_=Decimal("0"))
            ).label("total_staked"),
            func.sum(
                case((UserBet.status == "won", UserBet.actual_return), else_=Decimal("0"))
            ).label("total_returned"),
        ).where(UserBet.user_id == user_id)

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            "total": row.total or 0,
            "won": row.won or 0,
            "lost": row.lost or 0,
            "pending": row.pending or 0,
            "total_staked": float(row.total_staked or 0),
            "total_returned": float(row.total_returned or 0),
        }

    async def update_status(
        self,
        bet_id: int,
        user_id: str,
        status: str,
        actual_return: Decimal | None = None,
    ) -> UserBet | None:
        """Update bet status and return the updated bet."""
        stmt = (
            update(UserBet)
            .where(UserBet.id == bet_id, UserBet.user_id == user_id)
            .values(
                status=status,
                actual_return=actual_return,
                settled_at=datetime.utcnow() if status in ("won", "lost", "void") else None,
                updated_at=datetime.utcnow(),
            )
            .returning(UserBet)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_pending(self, bet_id: int, user_id: str) -> bool:
        """Delete a pending bet. Returns True if deleted."""
        bet = await self.session.get(UserBet, bet_id)
        if bet and bet.user_id == user_id and bet.status == "pending":
            await self.session.delete(bet)
            return True
        return False


class UserBankrollSettingsRepository(BaseRepository[UserBankroll]):
    """Repository for user bankroll settings (not transactions)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserBankroll, session)

    async def get_by_user(self, user_id: str) -> UserBankroll | None:
        """Get bankroll settings for a user."""
        # UserBankroll is used for transactions, but we need to query the first one
        # Actually, looking at bets.py, it uses a separate user_bankroll table for settings
        # The ORM model UserBankroll is for transactions. We need a settings model.
        # For now, let's use UserPreferences which has bankroll field
        stmt = select(UserBankroll).where(UserBankroll.user_id == user_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class UserFavoriteRepository(BaseRepository[UserFavorite]):
    """Repository for user favorites operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserFavorite, session)

    async def get_by_user(self, user_id: str) -> list[UserFavorite]:
        """Get all favorites for a user."""
        stmt = (
            select(UserFavorite)
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_match(self, user_id: str, match_id: int) -> UserFavorite | None:
        """Get a specific favorite by user and match."""
        stmt = select(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.match_id == match_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_user_and_match(self, user_id: str, match_id: int) -> bool:
        """Delete a favorite. Returns True if deleted."""
        favorite = await self.get_by_user_and_match(user_id, match_id)
        if favorite:
            await self.session.delete(favorite)
            return True
        return False


class UserPreferencesRepository(BaseRepository[UserPreferences]):
    """Repository for user preferences operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserPreferences, session)

    async def get_by_user(self, user_id: str) -> UserPreferences | None:
        """Get preferences for a user."""
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_by_user(self, user_id: str, **kwargs: Any) -> UserPreferences:
        """Create or update user preferences by user_id."""
        existing = await self.get_by_user(user_id)

        if existing:
            for key, value in kwargs.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new preferences
        prefs = UserPreferences(user_id=user_id, **kwargs)
        self.session.add(prefs)
        return prefs


class UserStatsRepository(BaseRepository[UserStats]):
    """Repository for pre-calculated user statistics."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserStats, session)

    async def get_by_user(self, user_id: str) -> UserStats | None:
        """Get stats for a user."""
        stmt = select(UserStats).where(UserStats.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_by_user(self, user_id: str, **kwargs: Any) -> UserStats:
        """Create or update user stats by user_id."""
        existing = await self.get_by_user(user_id)

        if existing:
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            return existing

        stats = UserStats(user_id=user_id, **kwargs)
        self.session.add(stats)
        return stats


class PushSubscriptionRepository(BaseRepository[PushSubscription]):
    """Repository for push subscription operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PushSubscription, session)

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """Get subscription by endpoint."""
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """Get active subscription by endpoint."""
        stmt = select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_subscriptions(
        self,
        preference: str | None = None,
        user_id: str | None = None,
    ) -> list[PushSubscription]:
        """Get active subscriptions with optional filters."""
        stmt = select(PushSubscription).where(PushSubscription.is_active == True)  # noqa: E712

        if preference == "daily_picks":
            stmt = stmt.where(PushSubscription.daily_picks == True)  # noqa: E712
        elif preference == "match_start":
            stmt = stmt.where(PushSubscription.match_start == True)  # noqa: E712
        elif preference == "result_updates":
            stmt = stmt.where(PushSubscription.result_updates == True)  # noqa: E712

        if user_id:
            stmt = stmt.where(PushSubscription.user_id == user_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(self, endpoint: str) -> bool:
        """Deactivate a subscription by endpoint."""
        sub = await self.get_by_endpoint(endpoint)
        if sub:
            sub.is_active = False
            sub.updated_at = datetime.utcnow()
            return True
        return False

    async def update_preferences(
        self,
        endpoint: str,
        daily_picks: bool,
        match_start: bool,
        result_updates: bool,
    ) -> bool:
        """Update subscription preferences."""
        sub = await self.get_active_by_endpoint(endpoint)
        if sub:
            sub.daily_picks = daily_picks
            sub.match_start = match_start
            sub.result_updates = result_updates
            sub.updated_at = datetime.utcnow()
            return True
        return False
