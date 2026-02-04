"""Stripe payment routes for subscription management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from src.auth.dependencies import AuthenticatedUser
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

    # TODO: Update user in Supabase with:
    # - stripe_customer_id
    # - stripe_subscription_id
    # - role = "premium" or "elite"


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
    status = data.get("status")
    cancel_at_period_end = data.get("cancel_at_period_end")

    logger.info(
        f"Subscription updated: {subscription_id}, "
        f"status={status}, cancel_at_period_end={cancel_at_period_end}"
    )

    # TODO: Update user role based on subscription status


async def handle_subscription_deleted(data: dict):
    """Handle customer.subscription.deleted event."""
    subscription_id = data.get("id")
    user_id = data.get("metadata", {}).get("user_id")

    logger.info(f"Subscription deleted: {subscription_id}, user={user_id}")

    # TODO: Downgrade user to free plan in Supabase


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

    logger.warning(f"Payment failed: {invoice_id}, customer={customer_id}")

    # TODO: Send notification to user about failed payment
