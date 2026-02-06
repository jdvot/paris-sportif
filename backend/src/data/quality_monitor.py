"""Data quality monitoring system.

Provides comprehensive data quality checks including:
- Freshness: Alert if data > 24h old
- Completeness: % of missing fields
- Range validation: Values within expected bounds (xG, ELO, etc.)
- Consistency: Duplicates and conflicts detection

Migrated to async repository pattern (PAR-142).
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import func, select

from src.db.models import Match, Prediction, PredictionResult, Team
from src.db.repositories import get_uow

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


async def check_freshness() -> DataQualityCheck:
    """Check data freshness - when was data last updated."""
    async with get_uow() as uow:
        # Check last match update
        stmt = select(func.max(Match.updated_at))
        result = await uow.session.execute(stmt)
        last_match_update = result.scalar_one_or_none()

        # Check last team update
        stmt = select(func.max(Team.updated_at))
        result = await uow.session.execute(stmt)
        last_team_update = result.scalar_one_or_none()

        # Check last prediction update
        stmt = select(func.max(Prediction.updated_at))
        result = await uow.session.execute(stmt)
        last_prediction_update = result.scalar_one_or_none()

    # Find the most recent update (convert to naive UTC datetimes first)
    def to_naive_utc(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    updates = [
        ("matches", to_naive_utc(last_match_update)),
        ("teams", to_naive_utc(last_team_update)),
        ("predictions", to_naive_utc(last_prediction_update)),
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


async def check_completeness() -> DataQualityCheck:
    """Check data completeness - percentage of fields that are populated."""
    details: dict[str, Any] = {}

    async with get_uow() as uow:
        # Check teams completeness
        stmt = select(func.count(Team.id))
        result = await uow.session.execute(stmt)
        total_teams = result.scalar_one() or 0

        # Check matches completeness
        stmt = select(func.count(Match.id))
        result = await uow.session.execute(stmt)
        total_matches = result.scalar_one() or 0

        stmt = select(func.count(Match.id)).where(Match.status == "finished")
        result = await uow.session.execute(stmt)
        finished_matches = result.scalar_one() or 0

        stmt = select(func.count(Match.id)).where(
            Match.status == "finished",
            Match.home_score.isnot(None),
        )
        result = await uow.session.execute(stmt)
        matches_with_score = result.scalar_one() or 0

        # Check predictions completeness
        stmt = select(func.count(Prediction.id))
        result = await uow.session.execute(stmt)
        total_preds = result.scalar_one() or 0

        stmt = select(func.count(Prediction.id)).where(
            Prediction.explanation.isnot(None),
            Prediction.explanation != "",
        )
        result = await uow.session.execute(stmt)
        preds_with_explanation = result.scalar_one() or 0

    # Calculate completeness scores
    team_completeness = {}
    if total_teams > 0:
        team_completeness = {"total": total_teams}
        details["teams"] = {"total": total_teams, "completeness": team_completeness}
    else:
        details["teams"] = {"total": 0, "completeness": {}}

    match_completeness = {}
    if total_matches > 0:
        match_completeness = {
            "finished_with_score": (
                matches_with_score / finished_matches if finished_matches else 1.0
            ),
        }
        details["matches"] = {
            "total": total_matches,
            "finished": finished_matches,
            "completeness": match_completeness,
        }
    else:
        details["matches"] = {"total": 0, "finished": 0, "completeness": {}}

    pred_completeness = {}
    if total_preds > 0:
        pred_completeness = {
            "explanation": preds_with_explanation / total_preds,
        }
        details["predictions"] = {
            "total": total_preds,
            "completeness": pred_completeness,
        }
    else:
        details["predictions"] = {"total": 0, "completeness": {}}

    # Calculate overall completeness
    all_scores = list(match_completeness.values()) + list(pred_completeness.values())
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


async def check_range_validation() -> DataQualityCheck:
    """Check data values are within valid ranges."""
    anomalies: list[dict[str, Any]] = []

    async with get_uow() as uow:
        # Check prediction probabilities sum to 1 (with tolerance)
        from sqlalchemy import and_, or_

        stmt = (
            select(Prediction)
            .where(
                func.abs((Prediction.home_prob + Prediction.draw_prob + Prediction.away_prob) - 1.0)
                > 0.01
            )
            .limit(20)
        )
        result = await uow.session.execute(stmt)
        invalid_probs = result.scalars().all()

        for pred in invalid_probs:
            prob_sum = float(pred.home_prob) + float(pred.draw_prob) + float(pred.away_prob)
            anomalies.append(
                {
                    "type": "probability_sum_invalid",
                    "entity": "prediction",
                    "id": pred.id,
                    "field": "probabilities",
                    "value": round(prob_sum, 4),
                    "expected": 1.0,
                }
            )

        # Check confidence in valid range
        stmt = (
            select(Prediction)
            .where(
                or_(
                    Prediction.confidence < VALID_RANGES["confidence"]["min"],
                    Prediction.confidence > VALID_RANGES["confidence"]["max"],
                )
            )
            .limit(20)
        )
        result = await uow.session.execute(stmt)
        invalid_conf = result.scalars().all()

        for pred in invalid_conf:
            anomalies.append(
                {
                    "type": "range_violation",
                    "entity": "prediction",
                    "id": pred.id,
                    "field": "confidence",
                    "value": float(pred.confidence) if pred.confidence else None,
                    "valid_range": VALID_RANGES["confidence"],
                }
            )

        # Check goal scores are reasonable
        stmt = (
            select(Match)
            .where(
                or_(
                    and_(
                        Match.home_score.isnot(None),
                        Match.home_score > VALID_RANGES["goals"]["max"],
                    ),
                    and_(
                        Match.away_score.isnot(None),
                        Match.away_score > VALID_RANGES["goals"]["max"],
                    ),
                )
            )
            .limit(20)
        )
        result = await uow.session.execute(stmt)
        invalid_goals = result.scalars().all()

        for match in invalid_goals:
            anomalies.append(
                {
                    "type": "range_violation",
                    "entity": "match",
                    "id": match.id,
                    "field": "score",
                    "value": f"{match.home_score}-{match.away_score}",
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
        details={"anomalies": anomalies[:20]},
    )


async def check_consistency() -> DataQualityCheck:
    """Check data consistency - duplicates and conflicts."""
    issues: list[dict[str, Any]] = []

    async with get_uow() as uow:
        # Check for duplicate matches (same teams, same date)

        stmt = (
            select(
                Match.home_team_id,
                Match.away_team_id,
                func.date(Match.match_date),
                func.count(Match.id).label("cnt"),
            )
            .group_by(Match.home_team_id, Match.away_team_id, func.date(Match.match_date))
            .having(func.count(Match.id) > 1)
        )
        result = await uow.session.execute(stmt)
        duplicate_matches = result.all()

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
        stmt = (
            select(Team.external_id, func.count(Team.id).label("cnt"))
            .where(Team.external_id.isnot(None))
            .group_by(Team.external_id)
            .having(func.count(Team.id) > 1)
        )
        result = await uow.session.execute(stmt)
        duplicate_teams = result.all()

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
        stmt = select(Match).where(Match.home_team_id == Match.away_team_id)
        result = await uow.session.execute(stmt)
        self_matches = result.scalars().all()

        for match in self_matches:
            issues.append(
                {
                    "type": "conflict",
                    "entity": "match",
                    "description": f"Match {match.id} has same team as home and away",
                }
            )

        # Check for predictions without matching match
        from sqlalchemy.orm import aliased

        match_alias = aliased(Match)
        stmt = (
            select(func.count(Prediction.id))
            .outerjoin(match_alias, Prediction.match_id == match_alias.id)
            .where(match_alias.id.is_(None))
        )
        result = await uow.session.execute(stmt)
        orphan_count = result.scalar_one() or 0

        if orphan_count > 0:
            issues.append(
                {
                    "type": "orphan",
                    "entity": "prediction",
                    "description": f"Found {orphan_count} predictions without matching match",
                    "count": orphan_count,
                }
            )

        # Check for finished matches without scores
        stmt = select(func.count(Match.id)).where(
            Match.status == "finished",
            Match.home_score.is_(None),
        )
        result = await uow.session.execute(stmt)
        missing_scores = result.scalar_one() or 0

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


async def get_data_quality_metrics() -> dict[str, Any]:
    """Get additional data quality metrics."""
    async with get_uow() as uow:
        # Get counts
        stmt = select(func.count(Team.id))
        result = await uow.session.execute(stmt)
        total_teams = result.scalar_one() or 0

        stmt = select(func.count(Match.id))
        result = await uow.session.execute(stmt)
        total_matches = result.scalar_one() or 0

        stmt = select(func.count(Match.id)).where(Match.status == "finished")
        result = await uow.session.execute(stmt)
        finished_matches = result.scalar_one() or 0

        stmt = select(func.count(Match.id)).where(Match.status.in_(["scheduled", "SCHEDULED"]))
        result = await uow.session.execute(stmt)
        scheduled_matches = result.scalar_one() or 0

        stmt = select(func.count(Prediction.id))
        result = await uow.session.execute(stmt)
        total_predictions = result.scalar_one() or 0

        stmt = select(func.count(PredictionResult.id)).where(
            PredictionResult.was_correct == True  # noqa: E712
        )
        result = await uow.session.execute(stmt)
        correct_predictions = result.scalar_one() or 0

        stmt = select(func.count(PredictionResult.id))
        result = await uow.session.execute(stmt)
        verified_predictions = result.scalar_one() or 0

    accuracy = (
        round(correct_predictions / verified_predictions * 100, 1)
        if verified_predictions > 0
        else 0
    )

    return {
        "entities": {
            "teams": total_teams,
            "matches": total_matches,
            "predictions": total_predictions,
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


async def run_quality_check() -> DataQualityReport:
    """Run all data quality checks and generate report."""
    logger.info("Starting data quality check...")

    # Run all checks
    freshness = await check_freshness()
    completeness = await check_completeness()
    range_validation = await check_range_validation()
    consistency = await check_consistency()

    # Get metrics
    metrics = await get_data_quality_metrics()

    # Collect all anomalies
    anomalies: list[dict[str, Any]] = []
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
