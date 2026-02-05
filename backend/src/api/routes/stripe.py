"""Stripe payment routes for subscription management."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from src.auth.dependencies import AuthenticatedUser
from src.auth.supabase_auth import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    sync_role_to_app_metadata,
)
from src.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])


class CreateCheckoutRequest(BaseModel):
    """Request body for creating a checkout session."""

    plan: str  # "premium" or "elite"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Response from checkout session creation."""

    session_id: str
    checkout_url: str


class PortalRequest(BaseModel):
    """Request body for creating a portal session."""

    return_url: str


class PortalResponse(BaseModel):
    """Response from portal session creation."""

    portal_url: str


class SubscriptionResponse(BaseModel):
    """Subscription details response."""

    id: str
    status: str
    plan: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool


class CancelRequest(BaseModel):
    """Request body for cancelling subscription."""

    immediate: bool = False


@router.post("/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: AuthenticatedUser,
):
    """
    Create a Stripe Checkout session for subscription purchase.

    Requires authentication. Creates a checkout session for the specified plan
    with a 7-day free trial.
    """
    user_id = current_user.get("sub")
    user_email = current_user.get("email")

    if not user_id or not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID and email required",
        )

    try:
        result = await stripe_service.create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            plan=request.plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/create-portal-session", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    current_user: AuthenticatedUser,
):
    """
    Create a Stripe Customer Portal session for subscription management.

    Allows users to manage their subscription, update payment methods,
    view invoices, and cancel.
    """
    # Get customer ID from user metadata (stored after first subscription)
    customer_id = current_user.get("stripe_customer_id")

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    try:
        result = await stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=request.return_url,
        )
        return PortalResponse(**result)
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    current_user: AuthenticatedUser,
):
    """
    Get the current user's subscription details.

    Returns None if no active subscription exists.
    """
    subscription_id = current_user.get("stripe_subscription_id")

    if not subscription_id:
        return None

    try:
        result = await stripe_service.get_subscription(subscription_id)
        if result:
            return SubscriptionResponse(**result)
        return None
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription",
        )


@router.post("/cancel-subscription")
async def cancel_subscription(
    request: CancelRequest,
    current_user: AuthenticatedUser,
):
    """
    Cancel the current user's subscription.

    By default, cancels at the end of the billing period.
    Set immediate=True to cancel immediately.
    """
    subscription_id = current_user.get("stripe_subscription_id")

    if not subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    try:
        result = await stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            immediate=request.immediate,
        )
        return result
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")],
):
    """
    Handle Stripe webhook events.

    Events handled:
    - checkout.session.completed: User completed checkout
    - customer.subscription.created: Subscription started
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.paid: Payment successful
    - invoice.payment_failed: Payment failed
    """
    payload = await request.body()

    try:
        event = stripe_service.construct_webhook_event(payload, stripe_signature)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(data)
        elif event_type == "customer.subscription.created":
            await handle_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(data)
        elif event_type == "invoice.paid":
            await handle_invoice_paid(data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(data)
        else:
            logger.debug(f"Unhandled webhook event: {event_type}")

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error handling webhook {event_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook handler failed",
        )


async def update_user_stripe_metadata(
    user_id: str,
    customer_id: str | None = None,
    subscription_id: str | None = None,
) -> bool:
    """
    Update user's Stripe-related metadata in Supabase Auth.

    Args:
        user_id: The Supabase user ID
        customer_id: Stripe customer ID
        subscription_id: Stripe subscription ID

    Returns:
        True if successful, False otherwise
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase admin credentials not configured")
        return False

    base_url = SUPABASE_URL.rstrip("/")
    auth_url = f"{base_url}/auth/v1/admin/users/{user_id}"

    # Build app_metadata update
    app_metadata: dict[str, str] = {}
    if customer_id:
        app_metadata["stripe_customer_id"] = customer_id
    if subscription_id:
        app_metadata["stripe_subscription_id"] = subscription_id

    if not app_metadata:
        return True  # Nothing to update

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                auth_url,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Content-Type": "application/json",
                },
                json={"app_metadata": app_metadata},
            )
            response.raise_for_status()
            logger.info(f"Updated Stripe metadata for user {user_id}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to update Stripe metadata: {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Error updating Stripe metadata: {e}")
        return False


async def update_user_role_in_profiles(user_id: str, role: str) -> bool:
    """
    Update user's role in the user_profiles table.

    Args:
        user_id: The Supabase user ID
        role: The new role (free, premium, elite, admin)

    Returns:
        True if successful, False otherwise
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase admin credentials not configured")
        return False

    base_url = SUPABASE_URL.rstrip("/")
    profiles_url = f"{base_url}/rest/v1/user_profiles?id=eq.{user_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                profiles_url,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={"role": role},
            )
            response.raise_for_status()
            logger.info(f"Updated role to '{role}' in user_profiles for {user_id}")
            return True
    except Exception as e:
        logger.warning(f"Failed to update user_profiles role: {e}")
        return False


async def get_user_id_from_customer(customer_id: str) -> str | None:
    """
    Get user_id from Stripe customer metadata or user_profiles table.

    Args:
        customer_id: Stripe customer ID

    Returns:
        User ID if found, None otherwise
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None

    base_url = SUPABASE_URL.rstrip("/")
    # Search user_profiles for stripe_customer_id
    profiles_url = f"{base_url}/rest/v1/user_profiles?stripe_customer_id=eq.{customer_id}&select=id"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                profiles_url,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return data[0].get("id")
    except Exception as e:
        logger.debug(f"Failed to get user_id from customer: {e}")

    return None


async def handle_checkout_completed(data: dict):
    """Handle checkout.session.completed event."""
    user_id = data.get("client_reference_id")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    plan = data.get("metadata", {}).get("plan", "premium")

    logger.info(
        f"Checkout completed for user {user_id}: "
        f"customer={customer_id}, subscription={subscription_id}, plan={plan}"
    )

    if not user_id:
        logger.error("No user_id in checkout session client_reference_id")
        return

    # Determine role based on plan
    role = "premium" if plan == "premium" else "premium"  # Both premium and elite get premium role

    # Update user's Stripe metadata in Supabase Auth
    await update_user_stripe_metadata(user_id, customer_id, subscription_id)

    # Update user's role in app_metadata
    await sync_role_to_app_metadata(user_id, role)

    # Also update role in user_profiles table
    await update_user_role_in_profiles(user_id, role)

    logger.info(f"User {user_id} upgraded to {role}")


async def handle_subscription_created(data: dict):
    """Handle customer.subscription.created event."""
    subscription_id = data.get("id")
    data.get("customer")
    status = data.get("status")
    plan = data.get("metadata", {}).get("plan", "premium")

    logger.info(f"Subscription created: {subscription_id}, status={status}, plan={plan}")


async def handle_subscription_updated(data: dict):
    """Handle customer.subscription.updated event."""
    subscription_id = data.get("id")
    sub_status = data.get("status")
    cancel_at_period_end = data.get("cancel_at_period_end")
    customer_id = data.get("customer")
    user_id = data.get("metadata", {}).get("user_id")
    plan = data.get("metadata", {}).get("plan", "premium")

    logger.info(
        f"Subscription updated: {subscription_id}, "
        f"status={sub_status}, cancel_at_period_end={cancel_at_period_end}"
    )

    # Try to get user_id from metadata or from customer lookup
    if not user_id and customer_id:
        user_id = await get_user_id_from_customer(customer_id)

    if not user_id:
        logger.warning(f"Cannot update user role: no user_id for subscription {subscription_id}")
        return

    # Determine role based on subscription status
    if sub_status in ("active", "trialing"):
        role = "premium"
    elif sub_status == "past_due":
        # Keep premium for past_due to give user time to fix payment
        role = "premium"
        logger.warning(f"Subscription {subscription_id} is past_due for user {user_id}")
    else:
        # For cancelled, incomplete, incomplete_expired, unpaid, etc.
        role = "free"

    # Update user's role
    await sync_role_to_app_metadata(user_id, role)
    await update_user_role_in_profiles(user_id, role)

    logger.info(f"User {user_id} role updated to {role} (subscription status: {sub_status})")


async def handle_subscription_deleted(data: dict):
    """Handle customer.subscription.deleted event."""
    subscription_id = data.get("id")
    user_id = data.get("metadata", {}).get("user_id")
    customer_id = data.get("customer")

    logger.info(f"Subscription deleted: {subscription_id}, user={user_id}")

    # Try to get user_id from metadata or from customer lookup
    if not user_id and customer_id:
        user_id = await get_user_id_from_customer(customer_id)

    if not user_id:
        logger.warning(f"Cannot downgrade user: no user_id for subscription {subscription_id}")
        return

    # Downgrade user to free plan
    await sync_role_to_app_metadata(user_id, "free")
    await update_user_role_in_profiles(user_id, "free")

    logger.info(f"User {user_id} downgraded to free (subscription deleted)")


async def handle_invoice_paid(data: dict):
    """Handle invoice.paid event."""
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    amount_paid = data.get("amount_paid", 0) / 100  # Convert from cents

    logger.info(f"Invoice paid: {invoice_id}, customer={customer_id}, amount={amount_paid}€")


async def handle_payment_failed(data: dict):
    """Handle invoice.payment_failed event."""
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    customer_email = data.get("customer_email")
    attempt_count = data.get("attempt_count", 1)
    next_payment_attempt = data.get("next_payment_attempt")

    logger.warning(
        f"Payment failed: {invoice_id}, customer={customer_id}, "
        f"email={customer_email}, attempt={attempt_count}"
    )

    # Get user_id to log the failure
    user_id = None
    if customer_id:
        user_id = await get_user_id_from_customer(customer_id)

    if user_id:
        logger.warning(
            f"Payment failed for user {user_id}. "
            f"Attempt {attempt_count}, next attempt: {next_payment_attempt}"
        )

    # Note: To send email notifications, integrate with an email service like:
    # - Resend (resend.com)
    # - SendGrid
    # - AWS SES
    # Example:
    # if customer_email:
    #     await email_service.send_payment_failed_notification(
    #         email=customer_email,
    #         attempt_count=attempt_count,
    #         next_attempt=next_payment_attempt,
    #     )
