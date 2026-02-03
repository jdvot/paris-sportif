"""Push notification service using Web Push protocol."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

from pywebpush import WebPushException, webpush

from src.data.database import db_session, get_placeholder

logger = logging.getLogger(__name__)


@dataclass
class PushNotification:
    """Push notification payload."""

    title: str
    body: str
    url: str = "/picks"
    icon: str = "/icons/icon-192x192.png"
    badge: str = "/icons/badge-72x72.png"
    tag: str | None = None


class PushNotificationService:
    """Service for sending push notifications."""

    def __init__(self):
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY", "")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
        self.vapid_claims = {
            "sub": os.getenv("VAPID_SUBJECT", "mailto:admin@paris-sportif.app")
        }

    def _send_single(self, endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
        """
        Send notification to a single subscription.

        Returns True if successful, False otherwise.
        """
        if not self.vapid_private_key:
            logger.warning("VAPID_PRIVATE_KEY not configured, skipping push")
            return False

        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": p256dh,
                "auth": auth,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
            )
            logger.debug(f"Push sent to {endpoint[:50]}...")
            return True
        except WebPushException as e:
            logger.error(f"Push failed: {e}")
            # Check if subscription is expired/invalid
            if e.response and e.response.status_code in (404, 410):
                return False  # Subscription invalid
            return False

    def send_notification(
        self,
        notification: PushNotification,
        notification_type: Literal["daily_picks", "match_start", "result_updates"] = "daily_picks",
        user_id: str | None = None,
    ) -> tuple[int, int]:
        """
        Send notification to all matching subscriptions.

        Args:
            notification: Notification payload
            notification_type: Type to filter subscriptions by preferences
            user_id: Optional user ID to filter subscriptions

        Returns:
            Tuple of (sent_count, failed_count)
        """
        ph = get_placeholder()

        # Build query for active subscriptions
        conditions = ["is_active = 1"]
        params: list[Any] = []

        # Filter by notification type preference
        if notification_type == "daily_picks":
            conditions.append("daily_picks = 1")
        elif notification_type == "match_start":
            conditions.append("match_start = 1")
        elif notification_type == "result_updates":
            conditions.append("result_updates = 1")

        # Filter by user if specified
        if user_id:
            conditions.append(f"user_id = {ph}")
            params.append(user_id)

        query = f"""
            SELECT endpoint, p256dh_key, auth_key
            FROM push_subscriptions
            WHERE {' AND '.join(conditions)}
        """

        payload = {
            "title": notification.title,
            "body": notification.body,
            "url": notification.url,
            "icon": notification.icon,
            "badge": notification.badge,
        }
        if notification.tag:
            payload["tag"] = notification.tag

        sent_count = 0
        failed_count = 0
        invalid_endpoints: list[str] = []

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            subscriptions = cursor.fetchall()

            for row in subscriptions:
                endpoint, p256dh, auth = row[0], row[1], row[2]
                success = self._send_single(endpoint, p256dh, auth, payload)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    # Track failed endpoints
                    cursor.execute(
                        f"""
                        UPDATE push_subscriptions
                        SET failed_count = failed_count + 1
                        WHERE endpoint = {ph}
                        """,
                        (endpoint,),
                    )
                    # Check if we should deactivate
                    cursor.execute(
                        f"SELECT failed_count FROM push_subscriptions WHERE endpoint = {ph}",
                        (endpoint,),
                    )
                    fail_row = cursor.fetchone()
                    if fail_row and fail_row[0] >= 3:
                        invalid_endpoints.append(endpoint)

            # Deactivate invalid subscriptions
            for endpoint in invalid_endpoints:
                cursor.execute(
                    f"UPDATE push_subscriptions SET is_active = 0 WHERE endpoint = {ph}",
                    (endpoint,),
                )

            logger.info(
                f"Deactivated {len(invalid_endpoints)} invalid subscriptions"
            ) if invalid_endpoints else None

        logger.info(
            f"Push notification sent: {sent_count} success, {failed_count} failed"
        )
        return sent_count, failed_count

    def send_daily_picks_notification(self, picks_count: int = 5) -> tuple[int, int]:
        """
        Send notification about new daily picks.
        """
        notification = PushNotification(
            title="Nouveaux picks disponibles",
            body=f"Vos {picks_count} picks du jour sont prets !",
            url="/picks",
            tag="daily-picks",
        )
        return self.send_notification(notification, "daily_picks")


# Singleton instance
push_service = PushNotificationService()
