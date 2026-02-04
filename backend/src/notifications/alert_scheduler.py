"""Alert scheduler for triggering match notifications."""

import logging
from datetime import UTC, datetime, timedelta

from src.data.database import db_session, get_placeholder
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
        now = datetime.now(UTC)
        alert_window_start = now + timedelta(minutes=self.MATCH_START_MINUTES_BEFORE - 5)
        alert_window_end = now + timedelta(minutes=self.MATCH_START_MINUTES_BEFORE + 5)

        ph = get_placeholder()
        alerts_sent = []

        with db_session() as conn:
            cursor = conn.cursor()

            # Find matches in the alert window that haven't been notified
            cursor.execute(
                f"""
                SELECT m.id, m.home_team, m.away_team, m.competition, m.utc_date,
                       p.predicted_outcome
                FROM matches m
                LEFT JOIN predictions p ON m.id = p.match_id
                WHERE m.utc_date >= {ph}
                  AND m.utc_date <= {ph}
                  AND m.status = 'SCHEDULED'
                  AND m.id NOT IN (
                      SELECT DISTINCT match_id FROM notification_log
                      WHERE notification_type = 'match_start'
                      AND created_at >= {ph}
                  )
                ORDER BY m.utc_date
                LIMIT 10
                """,
                (
                    alert_window_start.isoformat(),
                    alert_window_end.isoformat(),
                    (now - timedelta(hours=2)).isoformat(),
                ),
            )
            matches = cursor.fetchall()

        for match in matches:
            match_id, home_team, away_team, competition, utc_date, prediction = match

            try:
                result = await self.push_service.send_match_start_alert(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    competition=competition or "Football",
                    kickoff_time=utc_date,
                    prediction=prediction,
                )

                # Log the notification
                self._log_notification(
                    match_id=match_id,
                    notification_type="match_start",
                    sent_count=result["sent"],
                )

                alerts_sent.append(
                    {
                        "match_id": match_id,
                        "match": f"{home_team} vs {away_team}",
                        "sent": result["sent"],
                    }
                )

                logger.info(
                    f"Match start alert sent for {home_team} vs {away_team}: {result['sent']} notifications"
                )

            except Exception as e:
                logger.error(f"Failed to send match start alert for match {match_id}: {e}")

        return alerts_sent

    async def send_daily_picks_alert(self) -> dict:
        """Send daily picks notification."""
        ph = get_placeholder()
        today = datetime.now(UTC).date()

        # Check if already sent today
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM notification_log
                WHERE notification_type = 'daily_picks'
                AND DATE(created_at) = {ph}
                """,
                (today.isoformat(),),
            )
            count = cursor.fetchone()[0]

        if count > 0:
            logger.info("Daily picks notification already sent today")
            return {"sent": 0, "already_sent": True}

        # Get top pick for today
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT m.home_team, m.away_team
                FROM matches m
                JOIN predictions p ON m.id = p.match_id
                WHERE DATE(m.utc_date) = {ph}
                  AND m.status = 'SCHEDULED'
                ORDER BY p.value_score DESC
                LIMIT 1
                """,
                (today.isoformat(),),
            )
            top_pick = cursor.fetchone()

        top_pick_match = f"{top_pick[0]} vs {top_pick[1]}" if top_pick else None

        result = await self.push_service.send_daily_picks_notification(
            picks_count=5,
            top_pick_match=top_pick_match,
        )

        self._log_notification(
            match_id=None,
            notification_type="daily_picks",
            sent_count=result["sent"],
        )

        return result

    def _log_notification(
        self,
        match_id: int | None,
        notification_type: str,
        sent_count: int,
    ):
        """Log a sent notification to prevent duplicates."""
        ph = get_placeholder()

        with db_session() as conn:
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    notification_type TEXT NOT NULL,
                    sent_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(
                f"""
                INSERT INTO notification_log (match_id, notification_type, sent_count, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph})
                """,
                (
                    match_id,
                    notification_type,
                    sent_count,
                    datetime.now(UTC).isoformat(),
                ),
            )

    async def run_alert_check(self) -> dict:
        """Run a complete alert check cycle."""
        results = {
            "match_alerts": [],
            "daily_picks": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Check match start alerts
        try:
            results["match_alerts"] = await self.check_upcoming_matches()
        except Exception as e:
            logger.error(f"Error checking upcoming matches: {e}")
            results["match_alerts_error"] = str(e)

        # Check daily picks (only send once per day at specific times)
        now = datetime.now(UTC)
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
