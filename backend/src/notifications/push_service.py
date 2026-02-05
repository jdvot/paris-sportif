"""Push notification service for sending web push notifications."""

import json
import logging
from dataclasses import dataclass
from datetime import timezone,  datetime

from src.core.config import settings
from src.db.repositories import get_uow

logger = logging.getLogger(__name__)


@dataclass
class PushPayload:
    """Push notification payload."""

    title: str
    body: str
    icon: str = "/icons/icon-192x192.png"
    badge: str = "/icons/badge-72x72.png"
    url: str = "/"
    tag: str | None = None
    data: dict | None = None


class PushNotificationService:
    """Service for sending web push notifications."""

    def __init__(self):
        """Initialize the push notification service."""
        self.vapid_private_key = getattr(settings, "vapid_private_key", None)
        self.vapid_public_key = getattr(settings, "vapid_public_key", None)
        self.vapid_claims = {
            "sub": f"mailto:{getattr(settings, 'vapid_email', 'admin@paris-sportif.fr')}"
        }

    async def _get_active_subscriptions(
        self,
        preference: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """
        Get active push subscriptions from database using async repository.

        Args:
            preference: Optional preference filter (daily_picks, match_start, result_updates)
            user_id: Optional user ID filter

        Returns:
            List of subscription dictionaries
        """
        async with get_uow() as uow:
            subscriptions = await uow.push_subscriptions.get_active_subscriptions(
                preference=preference,
                user_id=user_id,
            )

            return [
                {
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
                    "user_id": sub.user_id,
                    "subscription_id": sub.id,
                }
                for sub in subscriptions
            ]

    async def _mark_subscription_failed(self, subscription_id: int, increment: bool = True):
        """Mark a subscription as failed or inactive using async repository."""
        async with get_uow() as uow:
            sub = await uow.push_subscriptions.get_by_id(subscription_id)
            if sub:
                if increment:
                    sub.failed_count = (sub.failed_count or 0) + 1
                    if sub.failed_count >= 3:
                        sub.is_active = False
                else:
                    sub.is_active = False
                sub.updated_at = datetime.now(timezone.utc)
                await uow.commit()

    async def send_notification(
        self,
        subscription: dict,
        payload: PushPayload,
    ) -> bool:
        """
        Send a push notification to a single subscription.

        Args:
            subscription: Subscription dictionary with endpoint and keys
            payload: PushPayload object

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.vapid_private_key:
            logger.warning("VAPID private key not configured, skipping push notification")
            return False

        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            logger.warning("pywebpush not installed, skipping push notification")
            return False

        notification_data = {
            "title": payload.title,
            "body": payload.body,
            "icon": payload.icon,
            "badge": payload.badge,
            "data": {
                "url": payload.url,
                **(payload.data or {}),
            },
        }

        if payload.tag:
            notification_data["tag"] = payload.tag

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription["endpoint"],
                    "keys": subscription["keys"],
                },
                data=json.dumps(notification_data),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
            )
            logger.debug(f"Push notification sent to {subscription['endpoint'][:50]}...")
            return True

        except WebPushException as e:
            logger.error(f"WebPush error: {e}")
            if e.response and e.response.status_code in (404, 410):
                await self._mark_subscription_failed(
                    subscription["subscription_id"],
                    increment=False,
                )
            else:
                await self._mark_subscription_failed(subscription["subscription_id"])
            return False

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

    async def broadcast_notification(
        self,
        payload: PushPayload,
        preference: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """
        Broadcast a notification to multiple subscriptions.

        Args:
            payload: PushPayload object
            preference: Optional preference filter
            user_id: Optional user ID filter

        Returns:
            Dictionary with sent/failed counts
        """
        subscriptions = await self._get_active_subscriptions(
            preference=preference,
            user_id=user_id,
        )

        if not subscriptions:
            logger.info("No active subscriptions found for broadcast")
            return {"sent": 0, "failed": 0, "total": 0}

        sent = 0
        failed = 0

        for subscription in subscriptions:
            success = await self.send_notification(subscription, payload)
            if success:
                sent += 1
            else:
                failed += 1

        logger.info(f"Broadcast complete: {sent} sent, {failed} failed out of {len(subscriptions)}")
        return {"sent": sent, "failed": failed, "total": len(subscriptions)}

    async def send_match_start_alert(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        competition: str,
        kickoff_time: str,
        prediction: str | None = None,
    ) -> dict:
        """Send match start alert to subscribed users."""
        body = f"{home_team} vs {away_team}"
        if prediction:
            body += f"\nNotre prediction: {prediction}"

        payload = PushPayload(
            title=f"Match dans 1h - {competition}",
            body=body,
            url=f"/match/{match_id}",
            tag=f"match-start-{match_id}",
            data={"type": "match_start", "match_id": match_id},
        )

        return await self.broadcast_notification(payload, preference="match_start")

    async def send_odds_change_alert(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        old_odds: float,
        new_odds: float,
        market: str,
    ) -> dict:
        """Send odds change alert when odds shift significantly."""
        change_pct = abs((new_odds - old_odds) / old_odds * 100)
        direction = "hausse" if new_odds > old_odds else "baisse"

        payload = PushPayload(
            title=f"Cotes en {direction}!",
            body=f"{home_team} vs {away_team}: {market} {old_odds:.2f} -> {new_odds:.2f} ({change_pct:.1f}%)",
            url=f"/match/{match_id}",
            tag=f"odds-change-{match_id}",
            data={"type": "odds_change", "match_id": match_id, "change_pct": change_pct},
        )

        return await self.broadcast_notification(payload, preference="match_start")

    async def send_injury_alert(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        player_name: str,
        team: str,
        injury_type: str,
    ) -> dict:
        """Send last-minute injury alert."""
        payload = PushPayload(
            title="Blessure derniere minute!",
            body=f"{player_name} ({team}) - {injury_type}. Match: {home_team} vs {away_team}",
            url=f"/match/{match_id}",
            tag=f"injury-{match_id}-{player_name.replace(' ', '-')}",
            data={"type": "injury_alert", "match_id": match_id, "player": player_name},
        )

        return await self.broadcast_notification(payload, preference="match_start")

    async def send_daily_picks_notification(
        self,
        picks_count: int = 5,
        top_pick_match: str | None = None,
    ) -> dict:
        """Send daily picks notification."""
        body = f"{picks_count} picks premium disponibles"
        if top_pick_match:
            body += f"\nTop pick: {top_pick_match}"

        payload = PushPayload(
            title="Picks du jour disponibles!",
            body=body,
            url="/picks",
            tag="daily-picks",
            data={"type": "daily_picks"},
        )

        return await self.broadcast_notification(payload, preference="daily_picks")


# Singleton instance
_push_service: PushNotificationService | None = None


def get_push_service() -> PushNotificationService:
    """Get the singleton PushNotificationService instance."""
    global _push_service
    if _push_service is None:
        _push_service = PushNotificationService()
    return _push_service
