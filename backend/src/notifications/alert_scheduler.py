"""Alert scheduler for triggering match notifications."""

import logging
from datetime import timezone,  datetime, timedelta

from src.db.repositories import get_uow
from src.notifications.push_service import get_push_service

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Scheduler for match alerts and notifications."""

    # Alert windows
    MATCH_START_MINUTES_BEFORE = 60  # 1 hour before kickoff
    ALERT_CHECK_INTERVAL_MINUTES = 5

    def __init__(self):
        """Initialize the alert scheduler."""
        self.push_service = get_push_service()
        self._last_check: datetime | None = None

    async def check_upcoming_matches(self) -> list[dict]:
        """
        Check for matches starting soon and send alerts.

        Returns:
            List of matches that triggered alerts
        """
        now = datetime.now(timezone.utc)
        alert_window_start = now + timedelta(minutes=self.MATCH_START_MINUTES_BEFORE - 5)
        alert_window_end = now + timedelta(minutes=self.MATCH_START_MINUTES_BEFORE + 5)

        alerts_sent = []

        async with get_uow() as uow:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            from src.db.models import Match, Prediction

            # Find matches in the alert window
            stmt = (
                select(Match)
                .outerjoin(Prediction, Match.id == Prediction.match_id)
                .options(joinedload(Match.home_team), joinedload(Match.away_team))
                .where(
                    Match.match_date >= alert_window_start,
                    Match.match_date <= alert_window_end,
                    Match.status.in_(["SCHEDULED", "scheduled", "TIMED"]),
                )
                .order_by(Match.match_date)
                .limit(10)
            )

            result = await uow._session.execute(stmt)
            matches = result.unique().scalars().all()

        # Filter out recently notified matches and process
        for match in matches:
            # Check if already notified (simple in-DB check)
            already_notified = await self._check_if_notified(match.id, "match_start")
            if already_notified:
                continue

            home_team = match.home_team.name if match.home_team else "Unknown"
            away_team = match.away_team.name if match.away_team else "Unknown"

            # Get prediction if available
            prediction = None
            async with get_uow() as uow:
                pred = await uow.predictions.get_by_match_id(match.id)
                if pred:
                    prediction = pred.predicted_outcome

            try:
                result = await self.push_service.send_match_start_alert(
                    match_id=match.id,
                    home_team=home_team,
                    away_team=away_team,
                    competition="Football",  # Could be enriched with competition data
                    kickoff_time=match.match_date.isoformat() if match.match_date else "",
                    prediction=prediction,
                )

                # Log the notification
                await self._log_notification(
                    match_id=match.id,
                    notification_type="match_start",
                    sent_count=result["sent"],
                    title="Match dans 1h",
                    body=f"{home_team} vs {away_team}",
                )

                alerts_sent.append(
                    {
                        "match_id": match.id,
                        "match": f"{home_team} vs {away_team}",
                        "sent": result["sent"],
                    }
                )

                logger.info(
                    f"Match start alert sent for {home_team} vs {away_team}: {result['sent']} notifications"
                )

            except Exception as e:
                logger.error(f"Failed to send match start alert for match {match.id}: {e}")

        return alerts_sent

    async def _check_if_notified(self, match_id: int, notification_type: str) -> bool:
        """Check if a notification has already been sent for this match."""
        async with get_uow() as uow:
            from sqlalchemy import func, select

            from src.db.models import NotificationLog

            now = datetime.now(timezone.utc)
            stmt = select(func.count(NotificationLog.id)).where(
                NotificationLog.notification_type == notification_type,
                NotificationLog.payload.contains(f'"match_id": {match_id}'),
                NotificationLog.created_at >= (now - timedelta(hours=2)),
            )
            result = await uow._session.execute(stmt)
            count = result.scalar_one()
            return count > 0

    async def send_daily_picks_alert(self) -> dict:
        """Send daily picks notification."""
        today = datetime.now(timezone.utc).date()

        # Check if already sent today
        async with get_uow() as uow:
            from sqlalchemy import func, select

            from src.db.models import NotificationLog

            stmt = select(func.count(NotificationLog.id)).where(
                NotificationLog.notification_type == "daily_picks",
                func.date(NotificationLog.created_at) == today,
            )
            result = await uow._session.execute(stmt)
            count = result.scalar_one()

        if count > 0:
            logger.info("Daily picks notification already sent today")
            return {"sent": 0, "already_sent": True}

        # Get top pick for today
        top_pick_match = None
        async with get_uow() as uow:
            from sqlalchemy import func, select
            from sqlalchemy.orm import joinedload

            from src.db.models import Match, Prediction

            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

            stmt = (
                select(Match)
                .join(Prediction, Match.id == Prediction.match_id)
                .options(joinedload(Match.home_team), joinedload(Match.away_team))
                .where(
                    Match.match_date >= today_start,
                    Match.match_date <= today_end,
                    Match.status.in_(["SCHEDULED", "scheduled", "TIMED"]),
                )
                .order_by(Prediction.confidence.desc())
                .limit(1)
            )
            result = await uow._session.execute(stmt)
            top_match = result.unique().scalar_one_or_none()

            if top_match:
                home_name = top_match.home_team.name if top_match.home_team else "Unknown"
                away_name = top_match.away_team.name if top_match.away_team else "Unknown"
                top_pick_match = f"{home_name} vs {away_name}"

        result = await self.push_service.send_daily_picks_notification(
            picks_count=5,
            top_pick_match=top_pick_match,
        )

        await self._log_notification(
            match_id=None,
            notification_type="daily_picks",
            sent_count=result["sent"],
            title="Picks du jour disponibles!",
            body="5 picks premium disponibles",
        )

        return result

    async def _log_notification(
        self,
        match_id: int | None,
        notification_type: str,
        sent_count: int,
        title: str = "",
        body: str = "",
    ):
        """Log a sent notification to prevent duplicates."""
        import json

        async with get_uow() as uow:
            from src.db.models import NotificationLog

            log_entry = NotificationLog(
                notification_type=notification_type,
                channel="push",
                title=title,
                body=body,
                payload=json.dumps({"match_id": match_id, "sent_count": sent_count}),
                status="sent",
                sent_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            uow._session.add(log_entry)
            await uow.commit()

    async def run_alert_check(self) -> dict:
        """Run a complete alert check cycle."""
        results: dict = {
            "match_alerts": [],
            "daily_picks": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Check match start alerts
        try:
            results["match_alerts"] = await self.check_upcoming_matches()
        except Exception as e:
            logger.error(f"Error checking upcoming matches: {e}")
            results["match_alerts_error"] = str(e)

        # Check daily picks (only send once per day at specific times)
        now = datetime.now(timezone.utc)
        if 7 <= now.hour <= 9:  # Send between 7-9 AM UTC
            try:
                results["daily_picks"] = await self.send_daily_picks_alert()
            except Exception as e:
                logger.error(f"Error sending daily picks alert: {e}")
                results["daily_picks_error"] = str(e)

        self._last_check = now
        return results


# Singleton instance
_scheduler: AlertScheduler | None = None


def get_alert_scheduler() -> AlertScheduler:
    """Get the singleton AlertScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AlertScheduler()
    return _scheduler
