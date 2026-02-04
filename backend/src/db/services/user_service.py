"""User service layer for bets, bankroll, favorites, and preferences.

Provides async service methods compatible with API route handlers.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.db.models import PushSubscription, UserBet, UserFavorite
from src.db.repositories.unit_of_work import get_uow


class BetService:
    """Service for user betting operations."""

    @staticmethod
    async def list_bets(
        user_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List user's bets."""
        async with get_uow() as uow:
            bets = await uow.user_bets.get_by_user(
                user_id=user_id,
                status=status,
                limit=limit,
                offset=offset,
            )
            return [
                {
                    "id": bet.id,
                    "match_id": bet.match_id,
                    "prediction": bet.bet_type,
                    "odds": float(bet.odds),
                    "amount": float(bet.stake),
                    "status": bet.status,
                    "potential_return": float(bet.potential_return),
                    "actual_return": float(bet.actual_return) if bet.actual_return else None,
                    "confidence": None,  # Not in ORM model
                    "created_at": bet.created_at.isoformat() if bet.created_at else None,
                }
                for bet in bets
            ]

    @staticmethod
    async def create_bet(
        user_id: str,
        match_id: int,
        prediction: str,
        odds: float,
        amount: float,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Create a new bet."""
        potential_return = amount * odds
        now = datetime.utcnow()

        async with get_uow() as uow:
            bet = UserBet(
                user_id=user_id,
                match_id=match_id,
                bet_type=prediction,
                stake=Decimal(str(amount)),
                odds=Decimal(str(odds)),
                potential_return=Decimal(str(potential_return)),
                status="pending",
                created_at=now,
                updated_at=now,
            )
            uow._session.add(bet)
            await uow.commit()
            await uow._session.refresh(bet)

            return {
                "id": bet.id,
                "match_id": bet.match_id,
                "prediction": bet.bet_type,
                "odds": float(bet.odds),
                "amount": float(bet.stake),
                "status": bet.status,
                "potential_return": float(bet.potential_return),
                "actual_return": None,
                "confidence": confidence,
                "created_at": bet.created_at.isoformat(),
            }

    @staticmethod
    async def update_bet_status(
        user_id: str,
        bet_id: int,
        status: str,
    ) -> dict[str, Any] | None:
        """Update bet status."""
        async with get_uow() as uow:
            bet = await uow.user_bets.get_by_id(bet_id)
            if not bet or bet.user_id != user_id:
                return None

            # Calculate actual return
            actual_return = None
            if status == "won":
                actual_return = bet.potential_return
            elif status == "lost":
                actual_return = Decimal("0")
            elif status == "void":
                actual_return = bet.stake  # Refund

            bet.status = status
            bet.actual_return = actual_return
            bet.settled_at = datetime.utcnow() if status in ("won", "lost", "void") else None
            bet.updated_at = datetime.utcnow()

            await uow.commit()

            return {
                "id": bet.id,
                "match_id": bet.match_id,
                "prediction": bet.bet_type,
                "odds": float(bet.odds),
                "amount": float(bet.stake),
                "status": bet.status,
                "potential_return": float(bet.potential_return),
                "actual_return": float(actual_return) if actual_return is not None else None,
                "confidence": None,
                "created_at": bet.created_at.isoformat() if bet.created_at else None,
            }

    @staticmethod
    async def delete_bet(user_id: str, bet_id: int) -> bool:
        """Delete a pending bet."""
        async with get_uow() as uow:
            deleted = await uow.user_bets.delete_pending(bet_id, user_id)
            if deleted:
                await uow.commit()
            return deleted

    @staticmethod
    async def get_bankroll_summary(user_id: str) -> dict[str, Any]:
        """Get bankroll summary for a user."""
        async with get_uow() as uow:
            # Get user preferences for initial bankroll
            prefs = await uow.user_preferences.get_by_user(user_id)
            initial_bankroll = float(prefs.bankroll) if prefs and prefs.bankroll else 0.0
            alert_threshold = 20.0  # Default

            # Get betting stats
            stats = await uow.user_bets.get_user_stats(user_id)

            total_staked = stats["total_staked"]
            total_returned = stats["total_returned"]
            profit_loss = total_returned - total_staked
            current_bankroll = initial_bankroll + profit_loss

            roi_pct = (profit_loss / total_staked * 100) if total_staked > 0 else 0.0
            won = stats["won"]
            lost = stats["lost"]
            win_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0.0

            threshold_amount = initial_bankroll * (alert_threshold / 100)
            is_below_threshold = (
                current_bankroll < threshold_amount if initial_bankroll > 0 else False
            )

            return {
                "initial_bankroll": initial_bankroll,
                "current_bankroll": round(current_bankroll, 2),
                "total_staked": round(total_staked, 2),
                "total_returned": round(total_returned, 2),
                "profit_loss": round(profit_loss, 2),
                "roi_pct": round(roi_pct, 2),
                "win_rate": round(win_rate, 1),
                "total_bets": stats["total"],
                "won_bets": won,
                "lost_bets": lost,
                "pending_bets": stats["pending"],
                "alert_threshold": alert_threshold,
                "is_below_threshold": is_below_threshold,
            }

    @staticmethod
    async def update_bankroll_settings(
        user_id: str,
        initial_bankroll: float,
        alert_threshold: float = 20.0,
        default_stake_pct: float = 2.0,
    ) -> dict[str, Any]:
        """Update bankroll settings."""
        async with get_uow() as uow:
            await uow.user_preferences.upsert(
                user_id=user_id,
                bankroll=Decimal(str(initial_bankroll)),
                default_stake=Decimal(str(initial_bankroll * default_stake_pct / 100)),
            )
            await uow.commit()

        return await BetService.get_bankroll_summary(user_id)

    @staticmethod
    async def get_kelly_suggestion(
        user_id: str,
        odds: float,
        confidence: float,
    ) -> dict[str, Any]:
        """Calculate Kelly Criterion stake suggestion.

        Kelly formula: f* = (bp - q) / b
        Where:
        - f* = fraction of bankroll to bet
        - b = decimal odds - 1
        - p = probability of winning
        - q = probability of losing (1 - p)
        """
        async with get_uow() as uow:
            # Get user preferences for initial bankroll
            prefs = await uow.user_preferences.get_by_user(user_id)
            initial_bankroll = float(prefs.bankroll) if prefs and prefs.bankroll else 0.0

            # Get betting stats for P&L
            stats = await uow.user_bets.get_user_stats(user_id)
            total_staked = stats["total_staked"]
            total_returned = stats["total_returned"]

        current_bankroll = initial_bankroll + (total_returned - total_staked)

        if current_bankroll <= 0:
            return {
                "suggested_stake": 0,
                "suggested_stake_pct": 0,
                "kelly_fraction": 0,
                "edge": 0,
                "bankroll": current_bankroll,
                "confidence_adjusted": False,
            }

        # Kelly calculation
        p = confidence / 100  # Win probability
        q = 1 - p  # Loss probability
        b = odds - 1  # Net odds

        # Kelly fraction: (bp - q) / b
        kelly_fraction = (b * p - q) / b if b > 0 else 0

        # Clamp to reasonable range (0 to 25% of bankroll)
        kelly_fraction = max(0, min(kelly_fraction, 0.25))

        # Use half-Kelly for more conservative betting
        half_kelly = kelly_fraction / 2

        suggested_stake = current_bankroll * half_kelly
        suggested_stake_pct = half_kelly * 100

        # Calculate edge (expected value per unit staked)
        edge = (p * odds) - 1

        return {
            "suggested_stake": round(suggested_stake, 2),
            "suggested_stake_pct": round(suggested_stake_pct, 2),
            "kelly_fraction": round(kelly_fraction, 4),
            "edge": round(edge, 4),
            "bankroll": round(current_bankroll, 2),
            "confidence_adjusted": True,  # Using half-Kelly
        }


class FavoriteService:
    """Service for user favorites operations."""

    @staticmethod
    async def list_favorites(user_id: str) -> list[dict[str, Any]]:
        """List user's favorites with match details."""
        async with get_uow() as uow:
            favorites = await uow.user_favorites.get_by_user(user_id)

            result = []
            for fav in favorites:
                match = await uow.matches.get_by_id(fav.match_id)
                home_team = None
                away_team = None
                competition = None
                match_date = None

                if match:
                    home = await uow.teams.get_by_id(match.home_team_id)
                    away = await uow.teams.get_by_id(match.away_team_id)
                    home_team = home.name if home else None
                    away_team = away.name if away else None
                    match_date = match.match_date.isoformat() if match.match_date else None

                result.append(
                    {
                        "id": fav.id,
                        "match_id": fav.match_id,
                        "prediction_id": fav.prediction_id,
                        "note": fav.note,
                        "notify_before_match": fav.notify_before_match,
                        "created_at": fav.created_at.isoformat() if fav.created_at else "",
                        "home_team": home_team,
                        "away_team": away_team,
                        "match_date": match_date,
                        "competition": competition,
                    }
                )

            return result

    @staticmethod
    async def add_favorite(
        user_id: str,
        match_id: int,
        prediction_id: int | None = None,
        note: str | None = None,
        notify_before_match: bool = True,
    ) -> dict[str, Any]:
        """Add a favorite."""
        async with get_uow() as uow:
            # Check if exists
            existing = await uow.user_favorites.get_by_user_and_match(user_id, match_id)
            if existing:
                raise ValueError("Already in favorites")

            now = datetime.utcnow()
            favorite = UserFavorite(
                user_id=user_id,
                match_id=match_id,
                prediction_id=prediction_id,
                note=note,
                notify_before_match=notify_before_match,
                created_at=now,
            )
            uow._session.add(favorite)
            await uow.commit()
            await uow._session.refresh(favorite)

            return {
                "id": favorite.id,
                "match_id": favorite.match_id,
                "prediction_id": favorite.prediction_id,
                "note": favorite.note,
                "notify_before_match": favorite.notify_before_match,
                "created_at": favorite.created_at.isoformat(),
            }

    @staticmethod
    async def remove_favorite(user_id: str, match_id: int) -> bool:
        """Remove a favorite."""
        async with get_uow() as uow:
            deleted = await uow.user_favorites.delete_by_user_and_match(user_id, match_id)
            if deleted:
                await uow.commit()
            return deleted


class PreferencesService:
    """Service for user preferences operations."""

    @staticmethod
    async def get_preferences(user_id: str) -> dict[str, Any]:
        """Get user preferences with defaults."""
        async with get_uow() as uow:
            prefs = await uow.user_preferences.get_by_user(user_id)

            if not prefs:
                return {
                    "language": "fr",
                    "timezone": "Europe/Paris",
                    "odds_format": "decimal",
                    "dark_mode": True,
                    "email_daily_picks": True,
                    "email_match_results": False,
                    "push_daily_picks": True,
                    "push_match_start": False,
                    "push_bet_results": True,
                    "default_stake": 10.0,
                    "risk_level": "medium",
                    "favorite_competitions": [],
                }

            fav_comps = []
            if prefs.favorite_competitions:
                try:
                    fav_comps = json.loads(prefs.favorite_competitions)
                except Exception:
                    pass

            return {
                "language": prefs.language or "fr",
                "timezone": prefs.timezone or "Europe/Paris",
                "odds_format": prefs.odds_format or "decimal",
                "dark_mode": prefs.dark_mode,
                "email_daily_picks": prefs.email_daily_picks,
                "email_match_results": prefs.email_match_results,
                "push_daily_picks": prefs.push_daily_picks,
                "push_match_start": prefs.push_match_start,
                "push_bet_results": prefs.push_bet_results,
                "default_stake": float(prefs.default_stake) if prefs.default_stake else 10.0,
                "risk_level": prefs.risk_level or "medium",
                "favorite_competitions": fav_comps,
            }

    @staticmethod
    async def update_preferences(user_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update user preferences."""
        # Handle favorite_competitions JSON encoding
        if "favorite_competitions" in kwargs and kwargs["favorite_competitions"] is not None:
            kwargs["favorite_competitions"] = json.dumps(kwargs["favorite_competitions"])

        async with get_uow() as uow:
            await uow.user_preferences.upsert(user_id, **kwargs)
            await uow.commit()

        return await PreferencesService.get_preferences(user_id)


class PushSubscriptionService:
    """Service for push subscription operations."""

    @staticmethod
    async def subscribe(
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Subscribe to push notifications."""
        async with get_uow() as uow:
            existing = await uow.push_subscriptions.get_by_endpoint(endpoint)

            if existing:
                # Update existing subscription
                existing.p256dh_key = p256dh_key
                existing.auth_key = auth_key
                existing.is_active = True
                existing.failed_count = 0
                if user_id:
                    existing.user_id = user_id
                existing.updated_at = datetime.utcnow()
                await uow.commit()
                return {"message": "Subscription updated", "id": existing.id}

            # Create new subscription
            now = datetime.utcnow()
            sub = PushSubscription(
                endpoint=endpoint,
                p256dh_key=p256dh_key,
                auth_key=auth_key,
                user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            uow._session.add(sub)
            await uow.commit()
            await uow._session.refresh(sub)

            return {"message": "Subscription created", "id": sub.id}

    @staticmethod
    async def unsubscribe(endpoint: str) -> dict[str, str]:
        """Unsubscribe from push notifications."""
        async with get_uow() as uow:
            deactivated = await uow.push_subscriptions.deactivate(endpoint)
            await uow.commit()

            if not deactivated:
                return {"message": "Subscription not found"}

            return {"message": "Subscription removed"}

    @staticmethod
    async def update_preferences(
        endpoint: str,
        daily_picks: bool,
        match_start: bool,
        result_updates: bool,
    ) -> bool:
        """Update subscription preferences."""
        async with get_uow() as uow:
            updated = await uow.push_subscriptions.update_preferences(
                endpoint=endpoint,
                daily_picks=daily_picks,
                match_start=match_start,
                result_updates=result_updates,
            )
            await uow.commit()
            return updated

    @staticmethod
    async def get_status(endpoint: str) -> dict[str, Any]:
        """Check subscription status."""
        async with get_uow() as uow:
            sub = await uow.push_subscriptions.get_active_by_endpoint(endpoint)

            if not sub:
                return {"subscribed": False}

            return {
                "subscribed": True,
                "preferences": {
                    "daily_picks": sub.daily_picks,
                    "match_start": sub.match_start,
                    "result_updates": sub.result_updates,
                },
            }
