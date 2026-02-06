"""Push notification routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.auth.supabase_auth import get_optional_user
from src.db.services.user_service import PushSubscriptionService

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


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push(
    subscription: SubscriptionRequest,
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """
    Subscribe to push notifications.

    Stores the push subscription for sending notifications later.
    """
    user_id = str(user.get("sub", "")) if user else None

    try:
        result = await PushSubscriptionService.subscribe(
            endpoint=subscription.endpoint,
            p256dh_key=subscription.keys.p256dh,
            auth_key=subscription.keys.auth,
            user_id=user_id,
        )
        logger.info(f"Push subscription: {subscription.endpoint[:50]}...")
        return result

    except Exception as e:
        logger.error(f"Failed to save push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save subscription",
        )


@router.post("/unsubscribe")
async def unsubscribe_push(request: UnsubscribeRequest) -> dict[str, Any]:
    """
    Unsubscribe from push notifications.
    """
    try:
        result = await PushSubscriptionService.unsubscribe(request.endpoint)
        logger.info(f"Push subscription deactivated: {request.endpoint[:50]}...")
        return result

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
) -> dict[str, str]:
    """
    Update notification preferences for a subscription.
    """
    updated = await PushSubscriptionService.update_preferences(
        endpoint=endpoint,
        daily_picks=preferences.daily_picks,
        match_start=preferences.match_start,
        result_updates=preferences.result_updates,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return {"message": "Preferences updated"}


@router.get("/status")
async def get_subscription_status(endpoint: str) -> dict[str, Any]:
    """
    Check if an endpoint is subscribed.
    """
    return await PushSubscriptionService.get_status(endpoint)
