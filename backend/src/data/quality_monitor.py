"""Data quality monitoring system.

Provides comprehensive data quality checks including:
- Freshness: Alert if data > 24h old
- Completeness: % of missing fields
- Range validation: Values within expected bounds (xG, ELO, etc.)
- Consistency: Duplicates and conflicts detection
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.data.database import db_session

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DataQualityCheck:
    """Result of a single data quality check."""

    name: str
    status: AlertLevel
    message: str
    value: float | int | str | None = None
    threshold: float | int | str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityReport:
    """Complete data quality report."""

    timestamp: datetime
    overall_status: AlertLevel
    freshness: DataQualityCheck
    completeness: DataQualityCheck
    range_validation: DataQualityCheck
    consistency: DataQualityCheck
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "freshness": {
                "name": self.freshness.name,
                "status": self.freshness.status.value,
                "message": self.freshness.message,
                "value": self.freshness.value,
                "threshold": self.freshness.threshold,
                "details": self.freshness.details,
            },
            "completeness": {
                "name": self.completeness.name,
                "status": self.completeness.status.value,
                "message": self.completeness.message,
                "value": self.completeness.value,
                "threshold": self.completeness.threshold,
                "details": self.completeness.details,
            },
            "range_validation": {
                "name": self.range_validation.name,
                "status": self.range_validation.status.value,
                "message": self.range_validation.message,
                "value": self.range_validation.value,
                "threshold": self.range_validation.threshold,
                "details": self.range_validation.details,
            },
            "consistency": {
                "name": self.consistency.name,
                "status": self.consistency.status.value,
                "message": self.consistency.message,
                "value": self.consistency.value,
                "threshold": self.consistency.threshold,
                "details": self.consistency.details,
            },
            "anomalies": self.anomalies,
            "metrics": self.metrics,
        }


# Thresholds for data quality checks
FRESHNESS_WARNING_HOURS = 12
FRESHNESS_CRITICAL_HOURS = 24
COMPLETENESS_WARNING_THRESHOLD = 0.90  # 90%
COMPLETENESS_CRITICAL_THRESHOLD = 0.80  # 80%

# Valid ranges for data validation
VALID_RANGES = {
    "elo_rating": {"min": 1000, "max": 2500},
    "xg": {"min": 0.0, "max": 6.0},
    "probability": {"min": 0.0, "max": 1.0},
    "confidence": {"min": 0.0, "max": 1.0},
    "goals": {"min": 0, "max": 15},
    "odds": {"min": 1.01, "max": 100.0},
}


def check_freshness() -> DataQualityCheck:
    """Check data freshness - when was data last updated."""
    with db_session() as conn:
        cursor = conn.cursor()

        # Check last match update
        cursor.execute(
            """
            SELECT MAX(updated_at) as last_update
            FROM matches
        """
        )
        result = cursor.fetchone()
        last_match_update = result[0] if result and result[0] else None

        # Check last team update
        cursor.execute(
            """
            SELECT MAX(updated_at) as last_update
            FROM teams
        """
        )
        result = cursor.fetchone()
        last_team_update = result[0] if result and result[0] else None

        # Check last prediction update
        cursor.execute(
            """
            SELECT MAX(updated_at) as last_update
            FROM predictions
        """
        )
        result = cursor.fetchone()
        last_prediction_update = result[0] if result and result[0] else None

    # Find the most recent update
    updates = [
        ("matches", last_match_update),
        ("teams", last_team_update),
        ("predictions", last_prediction_update),
    ]
    valid_updates = [(name, dt) for name, dt in updates if dt]

    if not valid_updates:
        return DataQualityCheck(
            name="Data Freshness",
            status=AlertLevel.CRITICAL,
            message="No data found in database",
            value=None,
            threshold=f"{FRESHNESS_CRITICAL_HOURS}h",
        )

    # Calculate hours since last update
    now = datetime.now(UTC).replace(tzinfo=None)
    oldest_entity = min(valid_updates, key=lambda x: x[1])
    oldest_name, oldest_dt = oldest_entity

    # Handle timezone-naive datetime
    if oldest_dt.tzinfo is not None:
        oldest_dt = oldest_dt.replace(tzinfo=None)

    hours_since_update = (now - oldest_dt).total_seconds() / 3600

    # Determine status
    if hours_since_update >= FRESHNESS_CRITICAL_HOURS:
        status = AlertLevel.CRITICAL
        message = f"Data is stale: {oldest_name} not updated in {hours_since_update:.1f}h"
    elif hours_since_update >= FRESHNESS_WARNING_HOURS:
        status = AlertLevel.WARNING
        message = f"Data getting stale: {oldest_name} last updated {hours_since_update:.1f}h ago"
    else:
        status = AlertLevel.OK
        message = f"Data is fresh: last update {hours_since_update:.1f}h ago"

    return DataQualityCheck(
        name="Data Freshness",
        status=status,
        message=message,
        value=round(hours_since_update, 1),
        threshold=f"{FRESHNESS_CRITICAL_HOURS}h",
        details={
            "matches_updated": last_match_update.isoformat() if last_match_update else None,
            "teams_updated": last_team_update.isoformat() if last_team_update else None,
            "predictions_updated": (
                last_prediction_update.isoformat() if last_prediction_update else None
            ),
            "oldest_entity": oldest_name,
        },
    )


def check_completeness() -> DataQualityCheck:
    """Check data completeness - percentage of fields that are populated."""
    with db_session() as conn:
        cursor = conn.cursor()

        # Check teams completeness
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN elo_rating IS NOT NULL THEN 1 ELSE 0 END) as has_elo,
                SUM(CASE WHEN avg_goals_scored_home IS NOT NULL THEN 1 ELSE 0 END) as has_home_goals,
                SUM(CASE WHEN avg_goals_scored_away IS NOT NULL THEN 1 ELSE 0 END) as has_away_goals,
                SUM(CASE WHEN avg_xg_for IS NOT NULL THEN 1 ELSE 0 END) as has_xg
            FROM teams
        """
        )
        team_stats = cursor.fetchone()

        # Check matches completeness
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'finished' THEN 1 ELSE 0 END) as finished,
                SUM(CASE WHEN status = 'finished' AND home_score IS NOT NULL THEN 1 ELSE 0 END) as has_score,
                SUM(CASE WHEN home_xg IS NOT NULL THEN 1 ELSE 0 END) as has_xg,
                SUM(CASE WHEN odds_home IS NOT NULL THEN 1 ELSE 0 END) as has_odds
            FROM matches
        """
        )
        match_stats = cursor.fetchone()

        # Check predictions completeness
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN explanation IS NOT NULL AND explanation != '' THEN 1 ELSE 0 END) as has_explanation,
                SUM(CASE WHEN key_factors IS NOT NULL THEN 1 ELSE 0 END) as has_factors,
                SUM(CASE WHEN model_details IS NOT NULL THEN 1 ELSE 0 END) as has_model_details
            FROM predictions
        """
        )
        pred_stats = cursor.fetchone()

    # Calculate completeness scores
    details = {}

    # Teams completeness
    if team_stats and team_stats[0] > 0:
        total_teams = team_stats[0]
        team_completeness = {
            "elo_rating": team_stats[1] / total_teams if total_teams else 0,
            "home_goals_avg": team_stats[2] / total_teams if total_teams else 0,
            "away_goals_avg": team_stats[3] / total_teams if total_teams else 0,
            "xg_data": team_stats[4] / total_teams if total_teams else 0,
        }
        details["teams"] = {
            "total": total_teams,
            "completeness": team_completeness,
        }
    else:
        team_completeness = {}
        details["teams"] = {"total": 0, "completeness": {}}

    # Matches completeness
    if match_stats and match_stats[0] > 0:
        total_matches = match_stats[0]
        finished_matches = match_stats[1]
        match_completeness = {
            "finished_with_score": (match_stats[2] / finished_matches if finished_matches else 1.0),
            "xg_data": match_stats[3] / total_matches if total_matches else 0,
            "odds_data": match_stats[4] / total_matches if total_matches else 0,
        }
        details["matches"] = {
            "total": total_matches,
            "finished": finished_matches,
            "completeness": match_completeness,
        }
    else:
        match_completeness = {}
        details["matches"] = {"total": 0, "finished": 0, "completeness": {}}

    # Predictions completeness
    if pred_stats and pred_stats[0] > 0:
        total_preds = pred_stats[0]
        pred_completeness = {
            "explanation": pred_stats[1] / total_preds if total_preds else 0,
            "key_factors": pred_stats[2] / total_preds if total_preds else 0,
            "model_details": pred_stats[3] / total_preds if total_preds else 0,
        }
        details["predictions"] = {
            "total": total_preds,
            "completeness": pred_completeness,
        }
    else:
        pred_completeness = {}
        details["predictions"] = {"total": 0, "completeness": {}}

    # Calculate overall completeness (weighted average)
    all_scores = (
        list(team_completeness.values())
        + list(match_completeness.values())
        + list(pred_completeness.values())
    )
    overall_completeness = sum(all_scores) / len(all_scores) if all_scores else 0

    # Determine status
    if overall_completeness < COMPLETENESS_CRITICAL_THRESHOLD:
        status = AlertLevel.CRITICAL
        message = f"Data completeness is critically low: {overall_completeness:.1%}"
    elif overall_completeness < COMPLETENESS_WARNING_THRESHOLD:
        status = AlertLevel.WARNING
        message = f"Data completeness below target: {overall_completeness:.1%}"
    else:
        status = AlertLevel.OK
        message = f"Data completeness is good: {overall_completeness:.1%}"

    return DataQualityCheck(
        name="Data Completeness",
        status=status,
        message=message,
        value=round(overall_completeness * 100, 1),
        threshold=f"{COMPLETENESS_WARNING_THRESHOLD * 100}%",
        details=details,
    )


def check_range_validation() -> DataQualityCheck:
    """Check data values are within valid ranges."""
    anomalies = []

    with db_session() as conn:
        cursor = conn.cursor()

        # Check ELO ratings
        cursor.execute(
            """
            SELECT id, name, elo_rating
            FROM teams
            WHERE elo_rating < %s
               OR elo_rating > %s
        """,
            (VALID_RANGES["elo_rating"]["min"], VALID_RANGES["elo_rating"]["max"]),
        )
        invalid_elo = cursor.fetchall()
        for row in invalid_elo:
            anomalies.append(
                {
                    "type": "range_violation",
                    "entity": "team",
                    "id": row[0],
                    "name": row[1],
                    "field": "elo_rating",
                    "value": float(row[2]) if row[2] else None,
                    "valid_range": VALID_RANGES["elo_rating"],
                }
            )

        # Check xG values
        cursor.execute(
            """
            SELECT m.id, t1.name, t2.name, m.home_xg, m.away_xg
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE (m.home_xg IS NOT NULL AND (m.home_xg < %s OR m.home_xg > %s))
               OR (m.away_xg IS NOT NULL AND (m.away_xg < %s OR m.away_xg > %s))
        """,
            (
                VALID_RANGES["xg"]["min"],
                VALID_RANGES["xg"]["max"],
                VALID_RANGES["xg"]["min"],
                VALID_RANGES["xg"]["max"],
            ),
        )
        invalid_xg = cursor.fetchall()
        for row in invalid_xg:
            home_xg = float(row[3]) if row[3] else None
            away_xg = float(row[4]) if row[4] else None
            if home_xg and (
                home_xg < VALID_RANGES["xg"]["min"] or home_xg > VALID_RANGES["xg"]["max"]
            ):
                anomalies.append(
                    {
                        "type": "range_violation",
                        "entity": "match",
                        "id": row[0],
                        "name": f"{row[1]} vs {row[2]}",
                        "field": "home_xg",
                        "value": home_xg,
                        "valid_range": VALID_RANGES["xg"],
                    }
                )
            if away_xg and (
                away_xg < VALID_RANGES["xg"]["min"] or away_xg > VALID_RANGES["xg"]["max"]
            ):
                anomalies.append(
                    {
                        "type": "range_violation",
                        "entity": "match",
                        "id": row[0],
                        "name": f"{row[1]} vs {row[2]}",
                        "field": "away_xg",
                        "value": away_xg,
                        "valid_range": VALID_RANGES["xg"],
                    }
                )

        # Check prediction probabilities sum to 1 (with tolerance)
        cursor.execute(
            """
            SELECT p.id, p.home_prob, p.draw_prob, p.away_prob,
                   t1.name, t2.name
            FROM predictions p
            JOIN matches m ON p.match_id = m.id
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE ABS((p.home_prob + p.draw_prob + p.away_prob) - 1.0) > 0.01
        """
        )
        invalid_probs = cursor.fetchall()
        for row in invalid_probs:
            prob_sum = float(row[1]) + float(row[2]) + float(row[3])
            anomalies.append(
                {
                    "type": "probability_sum_invalid",
                    "entity": "prediction",
                    "id": row[0],
                    "name": f"{row[4]} vs {row[5]}",
                    "field": "probabilities",
                    "value": round(prob_sum, 4),
                    "expected": 1.0,
                }
            )

        # Check confidence in valid range
        cursor.execute(
            """
            SELECT p.id, p.confidence, t1.name, t2.name
            FROM predictions p
            JOIN matches m ON p.match_id = m.id
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE p.confidence < %s
               OR p.confidence > %s
        """,
            (VALID_RANGES["confidence"]["min"], VALID_RANGES["confidence"]["max"]),
        )
        invalid_conf = cursor.fetchall()
        for row in invalid_conf:
            anomalies.append(
                {
                    "type": "range_violation",
                    "entity": "prediction",
                    "id": row[0],
                    "name": f"{row[2]} vs {row[3]}",
                    "field": "confidence",
                    "value": float(row[1]) if row[1] else None,
                    "valid_range": VALID_RANGES["confidence"],
                }
            )

        # Check goal scores are reasonable
        cursor.execute(
            """
            SELECT m.id, t1.name, t2.name, m.home_score, m.away_score
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE (m.home_score IS NOT NULL AND m.home_score > %s)
               OR (m.away_score IS NOT NULL AND m.away_score > %s)
        """,
            (VALID_RANGES["goals"]["max"], VALID_RANGES["goals"]["max"]),
        )
        invalid_goals = cursor.fetchall()
        for row in invalid_goals:
            anomalies.append(
                {
                    "type": "range_violation",
                    "entity": "match",
                    "id": row[0],
                    "name": f"{row[1]} vs {row[2]}",
                    "field": "score",
                    "value": f"{row[3]}-{row[4]}",
                    "valid_range": VALID_RANGES["goals"],
                }
            )

    # Determine status
    anomaly_count = len(anomalies)
    if anomaly_count > 10:
        status = AlertLevel.CRITICAL
        message = f"Found {anomaly_count} range violations - immediate attention required"
    elif anomaly_count > 0:
        status = AlertLevel.WARNING
        message = f"Found {anomaly_count} range violations"
    else:
        status = AlertLevel.OK
        message = "All data values within valid ranges"

    return DataQualityCheck(
        name="Range Validation",
        status=status,
        message=message,
        value=anomaly_count,
        threshold="0",
        details={"anomalies": anomalies[:20]},  # Limit to first 20
    )


def check_consistency() -> DataQualityCheck:
    """Check data consistency - duplicates and conflicts."""
    issues = []

    with db_session() as conn:
        cursor = conn.cursor()

        # Check for duplicate matches (same teams, same date)
        cursor.execute(
            """
            SELECT home_team_id, away_team_id, DATE(match_date), COUNT(*) as cnt
            FROM matches
            GROUP BY home_team_id, away_team_id, DATE(match_date)
            HAVING COUNT(*) > 1
        """
        )
        duplicate_matches = cursor.fetchall()
        for row in duplicate_matches:
            issues.append(
                {
                    "type": "duplicate",
                    "entity": "match",
                    "description": f"Duplicate match: teams {row[0]} vs {row[1]} on {row[2]}",
                    "count": row[3],
                }
            )

        # Check for duplicate teams (same external_id)
        cursor.execute(
            """
            SELECT external_id, COUNT(*) as cnt
            FROM teams
            GROUP BY external_id
            HAVING COUNT(*) > 1
        """
        )
        duplicate_teams = cursor.fetchall()
        for row in duplicate_teams:
            issues.append(
                {
                    "type": "duplicate",
                    "entity": "team",
                    "description": f"Duplicate team external_id: {row[0]}",
                    "count": row[1],
                }
            )

        # Check for matches with same team as home and away
        cursor.execute(
            """
            SELECT m.id, t.name
            FROM matches m
            JOIN teams t ON m.home_team_id = t.id
            WHERE m.home_team_id = m.away_team_id
        """
        )
        self_matches = cursor.fetchall()
        for row in self_matches:
            issues.append(
                {
                    "type": "conflict",
                    "entity": "match",
                    "description": f"Match {row[0]} has same team as home and away: {row[1]}",
                }
            )

        # Check for predictions without matching match
        cursor.execute(
            """
            SELECT p.id
            FROM predictions p
            LEFT JOIN matches m ON p.match_id = m.id
            WHERE m.id IS NULL
        """
        )
        orphan_predictions = cursor.fetchall()
        if orphan_predictions:
            issues.append(
                {
                    "type": "orphan",
                    "entity": "prediction",
                    "description": f"Found {len(orphan_predictions)} predictions without matching match",
                    "count": len(orphan_predictions),
                }
            )

        # Check for finished matches without scores
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE status = 'finished'
              AND (home_score IS NULL OR away_score IS NULL)
        """
        )
        result = cursor.fetchone()
        missing_scores = result[0] if result else 0
        if missing_scores > 0:
            issues.append(
                {
                    "type": "missing_data",
                    "entity": "match",
                    "description": f"{missing_scores} finished matches missing scores",
                    "count": missing_scores,
                }
            )

    # Determine status
    issue_count = len(issues)
    if issue_count > 5:
        status = AlertLevel.CRITICAL
        message = f"Found {issue_count} consistency issues - data integrity at risk"
    elif issue_count > 0:
        status = AlertLevel.WARNING
        message = f"Found {issue_count} consistency issues"
    else:
        status = AlertLevel.OK
        message = "Data is consistent - no duplicates or conflicts detected"

    return DataQualityCheck(
        name="Data Consistency",
        status=status,
        message=message,
        value=issue_count,
        threshold="0",
        details={"issues": issues},
    )


def get_data_quality_metrics() -> dict[str, Any]:
    """Get additional data quality metrics."""
    with db_session() as conn:
        cursor = conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM teams")
        total_teams = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'finished'")
        finished_matches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'scheduled'")
        scheduled_matches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_predictions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prediction_results WHERE was_correct = 1")
        correct_predictions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prediction_results")
        verified_predictions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM competitions")
        total_competitions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM news_items")
        total_news = cursor.fetchone()[0]

    accuracy = (
        round(correct_predictions / verified_predictions * 100, 1)
        if verified_predictions > 0
        else 0
    )

    return {
        "entities": {
            "teams": total_teams,
            "matches": total_matches,
            "competitions": total_competitions,
            "predictions": total_predictions,
            "news_items": total_news,
        },
        "matches": {
            "finished": finished_matches,
            "scheduled": scheduled_matches,
        },
        "predictions": {
            "total": total_predictions,
            "verified": verified_predictions,
            "correct": correct_predictions,
            "accuracy": accuracy,
        },
    }


def run_quality_check() -> DataQualityReport:
    """Run all data quality checks and generate report."""
    logger.info("Starting data quality check...")

    # Run all checks
    freshness = check_freshness()
    completeness = check_completeness()
    range_validation = check_range_validation()
    consistency = check_consistency()

    # Get metrics
    metrics = get_data_quality_metrics()

    # Collect all anomalies
    anomalies = []
    if range_validation.details.get("anomalies"):
        anomalies.extend(range_validation.details["anomalies"])
    if consistency.details.get("issues"):
        anomalies.extend(consistency.details["issues"])

    # Determine overall status
    all_checks = [freshness, completeness, range_validation, consistency]
    if any(check.status == AlertLevel.CRITICAL for check in all_checks):
        overall_status = AlertLevel.CRITICAL
    elif any(check.status == AlertLevel.WARNING for check in all_checks):
        overall_status = AlertLevel.WARNING
    else:
        overall_status = AlertLevel.OK

    report = DataQualityReport(
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        overall_status=overall_status,
        freshness=freshness,
        completeness=completeness,
        range_validation=range_validation,
        consistency=consistency,
        anomalies=anomalies,
        metrics=metrics,
    )

    logger.info(f"Data quality check complete: {overall_status.value}")
    return report


async def send_slack_alert(report: DataQualityReport, webhook_url: str | None = None) -> bool:
    """Send alert to Slack webhook if critical issues found.

    Args:
        report: Data quality report
        webhook_url: Slack webhook URL (optional, uses env var if not provided)

    Returns:
        True if alert was sent successfully, False otherwise
    """
    import os

    import httpx

    if report.overall_status != AlertLevel.CRITICAL:
        return False

    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        logger.warning("No Slack webhook URL configured, skipping alert")
        return False

    # Build message
    critical_checks = []
    for check_name in ["freshness", "completeness", "range_validation", "consistency"]:
        check = getattr(report, check_name)
        if check.status == AlertLevel.CRITICAL:
            critical_checks.append(f"*{check.name}*: {check.message}")

    message = {
        "text": ":warning: *Data Quality Alert* :warning:",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Data Quality Alert - Critical Issues Detected",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(critical_checks),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Timestamp: {report.timestamp.isoformat()}",
                    }
                ],
            },
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=message)
            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Error sending Slack alert: {e}")
        return False
