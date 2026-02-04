"""Push notification routes."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.auth.supabase_auth import get_optional_user
from src.data.database import db_session, get_placeholder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushKeys(BaseModel):
    """Push subscription keys."""

    p256dh: str
    auth: str


class SubscriptionRequest(BaseModel):
    """Push subscription request from browser."""

    endpoint: str
    expirationTime: int | None = None
    keys: PushKeys


class SubscriptionPreferences(BaseModel):
    """Notification preferences."""

    daily_picks: bool = True
    match_start: bool = False
    result_updates: bool = False


class UnsubscribeRequest(BaseModel):
    """Unsubscribe request."""

    endpoint: str


def _init_push_table():
    """Initialize push_subscriptions table if it doesn't exist."""
    with db_session() as conn:
        cursor = conn.cursor()
        # Use TEXT for endpoint to handle long URLs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE NOT NULL,
                p256dh_key TEXT NOT NULL,
                auth_key TEXT NOT NULL,
                user_id TEXT,
                daily_picks INTEGER DEFAULT 1,
                match_start INTEGER DEFAULT 0,
                result_updates INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                failed_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


# Initialize table on module load
try:
    _init_push_table()
except Exception as e:
    logger.warning(f"Could not initialize push_subscriptions table: {e}")


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push(
    subscription: SubscriptionRequest,
    user: dict | None = Depends(get_optional_user),
):
    """
    Subscribe to push notifications.

    Stores the push subscription for sending notifications later.
    """
    user_id = str(user.get("sub", "")) if user else None
    ph = get_placeholder()

    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Check if subscription already exists
            cursor.execute(
                f"SELECT id FROM push_subscriptions WHERE endpoint = {ph}",
                (subscription.endpoint,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing subscription
                cursor.execute(
                    f"""
                    UPDATE push_subscriptions
                    SET p256dh_key = {ph},
                        auth_key = {ph},
                        is_active = 1,
                        failed_count = 0,
                        user_id = COALESCE({ph}, user_id),
                        updated_at = {ph}
                    WHERE endpoint = {ph}
                    """,
                    (
                        subscription.keys.p256dh,
                        subscription.keys.auth,
                        user_id,
                        datetime.now(UTC).isoformat(),
                        subscription.endpoint,
                    ),
                )
                logger.info(f"Updated push subscription: {subscription.endpoint[:50]}...")
                return {"message": "Subscription updated", "id": existing[0]}

            # Create new subscription
            cursor.execute(
                f"""
                INSERT INTO push_subscriptions
                (endpoint, p256dh_key, auth_key, user_id, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    subscription.endpoint,
                    subscription.keys.p256dh,
                    subscription.keys.auth,
                    user_id,
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
            new_id = cursor.lastrowid

            logger.info(f"New push subscription created: {subscription.endpoint[:50]}...")
            return {"message": "Subscription created", "id": new_id}

    except Exception as e:
        logger.error(f"Failed to save push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save subscription",
        )


@router.post("/unsubscribe")
async def unsubscribe_push(request: UnsubscribeRequest):
    """
    Unsubscribe from push notifications.
    """
    ph = get_placeholder()

    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Soft delete - mark as inactive
            cursor.execute(
                f"""
                UPDATE push_subscriptions
                SET is_active = 0, updated_at = {ph}
                WHERE endpoint = {ph}
                """,
                (datetime.now(UTC).isoformat(), request.endpoint),
            )

            if cursor.rowcount == 0:
                return {"message": "Subscription not found"}

            logger.info(f"Push subscription deactivated: {request.endpoint[:50]}...")
            return {"message": "Subscription removed"}

    except Exception as e:
        logger.error(f"Failed to remove push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove subscription",
        )


@router.put("/preferences")
async def update_preferences(
    preferences: SubscriptionPreferences,
    endpoint: str,
):
    """
    Update notification preferences for a subscription.
    """
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            UPDATE push_subscriptions
            SET daily_picks = {ph},
                match_start = {ph},
                result_updates = {ph},
                updated_at = {ph}
            WHERE endpoint = {ph} AND is_active = 1
            """,
            (
                1 if preferences.daily_picks else 0,
                1 if preferences.match_start else 0,
                1 if preferences.result_updates else 0,
                datetime.now(UTC).isoformat(),
                endpoint,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

    return {"message": "Preferences updated"}


@router.get("/status")
async def get_subscription_status(endpoint: str):
    """
    Check if an endpoint is subscribed.
    """
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT daily_picks, match_start, result_updates
            FROM push_subscriptions
            WHERE endpoint = {ph} AND is_active = 1
            """,
            (endpoint,),
        )
        row = cursor.fetchone()

        if not row:
            return {"subscribed": False}

        return {
            "subscribed": True,
            "preferences": {
                "daily_picks": bool(row[0]),
                "match_start": bool(row[1]),
                "result_updates": bool(row[2]),
            },
        }
