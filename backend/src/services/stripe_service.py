"""Stripe payment service for subscription management."""

import logging
from datetime import datetime
from typing import Any

import stripe
from stripe import Webhook

from src.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_api_key


class StripeService:
    """Service for handling Stripe subscriptions."""

    PLAN_PRICES = {
        "premium": settings.stripe_price_premium,
        "elite": settings.stripe_price_elite,
    }

    @staticmethod
    async def create_checkout_session(
        user_id: str,
        user_email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            user_id: Supabase user ID
            user_email: User's email
            plan: Plan name (premium, elite)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled

        Returns:
            dict with session_id and checkout_url
        """
        if plan not in StripeService.PLAN_PRICES:
            raise ValueError(
                f"Invalid plan: {plan}. Must be one of {list(StripeService.PLAN_PRICES.keys())}"
            )

        price_id = StripeService.PLAN_PRICES[plan]

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                customer_email=user_email,
                client_reference_id=user_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                    "plan": plan,
                },
                subscription_data={
                    "metadata": {
                        "user_id": user_id,
                        "plan": plan,
                    },
                    "trial_period_days": 7,  # 7-day free trial
                },
            )

            logger.info(f"Created checkout session {session.id} for user {user_id}, plan {plan}")

            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise

    @staticmethod
    async def create_portal_session(customer_id: str, return_url: str) -> dict[str, Any]:
        """
        Create a Stripe Customer Portal session for subscription management.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session

        Returns:
            dict with portal_url
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

            return {"portal_url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            raise

    @staticmethod
    async def get_subscription(subscription_id: str) -> dict[str, Any] | None:
        """
        Get subscription details from Stripe.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription details or None
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                "id": subscription.id,
                "status": subscription.status,
                "plan": subscription.metadata.get("plan", "premium"),
                "current_period_start": datetime.fromtimestamp(
                    subscription.current_period_start
                ).isoformat(),
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end
                ).isoformat(),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "customer_id": subscription.customer,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {e}")
            return None

    @staticmethod
    async def cancel_subscription(subscription_id: str, immediate: bool = False) -> dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            immediate: If True, cancel immediately. If False, cancel at period end.

        Returns:
            Updated subscription details
        """
        try:
            if immediate:
                subscription = stripe.Subscription.cancel(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )

            logger.info(f"Cancelled subscription {subscription_id}, immediate={immediate}")

            return {
                "id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {e}")
            raise

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
        """
        Construct and verify a Stripe webhook event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header

        Returns:
            Verified Stripe event
        """
        try:
            event = Webhook.construct_event(
                payload,
                sig_header,
                settings.stripe_webhook_secret,
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            raise


# Singleton instance
stripe_service = StripeService()
