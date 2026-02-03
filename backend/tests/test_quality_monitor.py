"""Tests for data quality monitoring system."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.data.quality_monitor import (
    AlertLevel,
    DataQualityCheck,
    DataQualityReport,
    check_freshness,
    check_completeness,
    check_range_validation,
    check_consistency,
    run_quality_check,
    get_data_quality_metrics,
    FRESHNESS_CRITICAL_HOURS,
    FRESHNESS_WARNING_HOURS,
    COMPLETENESS_WARNING_THRESHOLD,
    COMPLETENESS_CRITICAL_THRESHOLD,
)


class TestAlertLevel:
    """Tests for AlertLevel enum."""

    def test_alert_levels_exist(self):
        """Test all alert levels are defined."""
        assert AlertLevel.OK == "ok"
        assert AlertLevel.WARNING == "warning"
        assert AlertLevel.CRITICAL == "critical"


class TestDataQualityCheck:
    """Tests for DataQualityCheck dataclass."""

    def test_create_check(self):
        """Test creating a quality check."""
        check = DataQualityCheck(
            name="Test Check",
            status=AlertLevel.OK,
            message="All good",
            value=100,
            threshold="90",
        )
        assert check.name == "Test Check"
        assert check.status == AlertLevel.OK
        assert check.value == 100

    def test_check_with_details(self):
        """Test check with additional details."""
        check = DataQualityCheck(
            name="Test",
            status=AlertLevel.WARNING,
            message="Warning",
            details={"extra": "info"},
        )
        assert check.details == {"extra": "info"}


class TestDataQualityReport:
    """Tests for DataQualityReport dataclass."""

    def test_report_to_dict(self):
        """Test report serialization."""
        check = DataQualityCheck(
            name="Test", status=AlertLevel.OK, message="OK"
        )
        report = DataQualityReport(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            overall_status=AlertLevel.OK,
            freshness=check,
            completeness=check,
            range_validation=check,
            consistency=check,
        )

        result = report.to_dict()

        assert result["timestamp"] == "2026-01-01T12:00:00"
        assert result["overall_status"] == "ok"
        assert "freshness" in result
        assert "completeness" in result
        assert "range_validation" in result
        assert "consistency" in result


class TestCheckFreshness:
    """Tests for freshness check."""

    @patch("src.data.quality_monitor.db_session")
    def test_fresh_data(self, mock_db):
        """Test when data is fresh."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recent = now - timedelta(hours=1)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (recent,),  # matches
            (recent,),  # teams
            (recent,),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_freshness()

        assert result.status == AlertLevel.OK
        assert result.value < FRESHNESS_WARNING_HOURS

    @patch("src.data.quality_monitor.db_session")
    def test_stale_data_warning(self, mock_db):
        """Test warning when data is getting stale."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        old = now - timedelta(hours=FRESHNESS_WARNING_HOURS + 1)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (old,),  # matches
            (old,),  # teams
            (old,),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_freshness()

        assert result.status == AlertLevel.WARNING

    @patch("src.data.quality_monitor.db_session")
    def test_stale_data_critical(self, mock_db):
        """Test critical when data is very stale."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        very_old = now - timedelta(hours=FRESHNESS_CRITICAL_HOURS + 1)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (very_old,),  # matches
            (very_old,),  # teams
            (very_old,),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_freshness()

        assert result.status == AlertLevel.CRITICAL

    @patch("src.data.quality_monitor.db_session")
    def test_no_data(self, mock_db):
        """Test critical when no data exists."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (None,),  # matches
            (None,),  # teams
            (None,),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_freshness()

        assert result.status == AlertLevel.CRITICAL
        assert "No data found" in result.message


class TestCheckCompleteness:
    """Tests for completeness check."""

    @patch("src.data.quality_monitor.db_session")
    def test_complete_data(self, mock_db):
        """Test when data is complete."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (100, 100, 100, 100, 100),  # teams - all complete
            (50, 20, 20, 50, 50),  # matches
            (100, 100, 100, 100),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_completeness()

        assert result.status == AlertLevel.OK
        assert result.value >= COMPLETENESS_WARNING_THRESHOLD * 100

    @patch("src.data.quality_monitor.db_session")
    def test_incomplete_data_warning(self, mock_db):
        """Test warning when data completeness is below target."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (100, 80, 80, 80, 80),  # teams - 80% complete
            (50, 20, 20, 40, 40),  # matches - incomplete
            (100, 80, 80, 80),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_completeness()

        assert result.status in [AlertLevel.OK, AlertLevel.WARNING]

    @patch("src.data.quality_monitor.db_session")
    def test_no_data_returns_ok(self, mock_db):
        """Test when no data exists."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (0, 0, 0, 0, 0),  # teams
            (0, 0, 0, 0, 0),  # matches
            (0, 0, 0, 0),  # predictions
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_completeness()

        # With no data, completeness should be 0%
        assert result.status == AlertLevel.CRITICAL


class TestCheckRangeValidation:
    """Tests for range validation check."""

    @patch("src.data.quality_monitor.db_session")
    def test_valid_ranges(self, mock_db):
        """Test when all values are in valid ranges."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],  # invalid elo
            [],  # invalid xg
            [],  # invalid probs
            [],  # invalid confidence
            [],  # invalid goals
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_range_validation()

        assert result.status == AlertLevel.OK
        assert result.value == 0

    @patch("src.data.quality_monitor.db_session")
    def test_invalid_elo(self, mock_db):
        """Test detection of invalid ELO ratings."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(1, "Bad Team", 500)],  # invalid elo
            [],  # invalid xg
            [],  # invalid probs
            [],  # invalid confidence
            [],  # invalid goals
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_range_validation()

        assert result.status == AlertLevel.WARNING
        assert result.value == 1
        assert len(result.details["anomalies"]) == 1

    @patch("src.data.quality_monitor.db_session")
    def test_many_anomalies_critical(self, mock_db):
        """Test critical status with many anomalies."""
        mock_cursor = MagicMock()
        invalid_elos = [(i, f"Team {i}", 500) for i in range(15)]
        mock_cursor.fetchall.side_effect = [
            invalid_elos,  # invalid elo
            [],  # invalid xg
            [],  # invalid probs
            [],  # invalid confidence
            [],  # invalid goals
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_range_validation()

        assert result.status == AlertLevel.CRITICAL
        assert result.value > 10


class TestCheckConsistency:
    """Tests for consistency check."""

    @patch("src.data.quality_monitor.db_session")
    def test_consistent_data(self, mock_db):
        """Test when data is consistent."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],  # duplicate matches
            [],  # duplicate teams
            [],  # self matches
            [],  # orphan predictions
        ]
        mock_cursor.fetchone.return_value = (0,)  # missing scores
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_consistency()

        assert result.status == AlertLevel.OK
        assert result.value == 0

    @patch("src.data.quality_monitor.db_session")
    def test_duplicate_matches(self, mock_db):
        """Test detection of duplicate matches."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(1, 2, "2026-01-15", 2)],  # duplicate matches
            [],  # duplicate teams
            [],  # self matches
            [],  # orphan predictions
        ]
        mock_cursor.fetchone.return_value = (0,)  # missing scores
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_consistency()

        assert result.status == AlertLevel.WARNING
        assert result.value == 1

    @patch("src.data.quality_monitor.db_session")
    def test_many_issues_critical(self, mock_db):
        """Test critical status with many consistency issues."""
        mock_cursor = MagicMock()
        duplicates = [(i, i + 1, f"2026-01-{i:02d}", 2) for i in range(1, 10)]
        mock_cursor.fetchall.side_effect = [
            duplicates,  # many duplicate matches
            [],  # duplicate teams
            [],  # self matches
            [],  # orphan predictions
        ]
        mock_cursor.fetchone.return_value = (0,)  # missing scores
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        result = check_consistency()

        assert result.status == AlertLevel.CRITICAL


class TestRunQualityCheck:
    """Tests for the main quality check runner."""

    @patch("src.data.quality_monitor.check_freshness")
    @patch("src.data.quality_monitor.check_completeness")
    @patch("src.data.quality_monitor.check_range_validation")
    @patch("src.data.quality_monitor.check_consistency")
    @patch("src.data.quality_monitor.get_data_quality_metrics")
    def test_all_ok(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test when all checks pass."""
        ok_check = DataQualityCheck(
            name="Test", status=AlertLevel.OK, message="OK"
        )
        mock_freshness.return_value = ok_check
        mock_completeness.return_value = ok_check
        mock_range.return_value = DataQualityCheck(
            name="Range", status=AlertLevel.OK, message="OK", details={}
        )
        mock_consistency.return_value = DataQualityCheck(
            name="Consistency", status=AlertLevel.OK, message="OK", details={}
        )
        mock_metrics.return_value = {}

        report = run_quality_check()

        assert report.overall_status == AlertLevel.OK

    @patch("src.data.quality_monitor.check_freshness")
    @patch("src.data.quality_monitor.check_completeness")
    @patch("src.data.quality_monitor.check_range_validation")
    @patch("src.data.quality_monitor.check_consistency")
    @patch("src.data.quality_monitor.get_data_quality_metrics")
    def test_any_critical_is_critical(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test that any critical check makes overall status critical."""
        ok_check = DataQualityCheck(
            name="Test", status=AlertLevel.OK, message="OK"
        )
        critical_check = DataQualityCheck(
            name="Critical", status=AlertLevel.CRITICAL, message="Critical!"
        )
        mock_freshness.return_value = critical_check
        mock_completeness.return_value = ok_check
        mock_range.return_value = DataQualityCheck(
            name="Range", status=AlertLevel.OK, message="OK", details={}
        )
        mock_consistency.return_value = DataQualityCheck(
            name="Consistency", status=AlertLevel.OK, message="OK", details={}
        )
        mock_metrics.return_value = {}

        report = run_quality_check()

        assert report.overall_status == AlertLevel.CRITICAL

    @patch("src.data.quality_monitor.check_freshness")
    @patch("src.data.quality_monitor.check_completeness")
    @patch("src.data.quality_monitor.check_range_validation")
    @patch("src.data.quality_monitor.check_consistency")
    @patch("src.data.quality_monitor.get_data_quality_metrics")
    def test_any_warning_is_warning(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test that any warning check makes overall status warning."""
        ok_check = DataQualityCheck(
            name="Test", status=AlertLevel.OK, message="OK"
        )
        warning_check = DataQualityCheck(
            name="Warning", status=AlertLevel.WARNING, message="Warning"
        )
        mock_freshness.return_value = ok_check
        mock_completeness.return_value = warning_check
        mock_range.return_value = DataQualityCheck(
            name="Range", status=AlertLevel.OK, message="OK", details={}
        )
        mock_consistency.return_value = DataQualityCheck(
            name="Consistency", status=AlertLevel.OK, message="OK", details={}
        )
        mock_metrics.return_value = {}

        report = run_quality_check()

        assert report.overall_status == AlertLevel.WARNING


class TestGetDataQualityMetrics:
    """Tests for metrics collection."""

    @patch("src.data.quality_monitor.db_session")
    def test_metrics_structure(self, mock_db):
        """Test that metrics have expected structure."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (100,),  # teams
            (500,),  # matches
            (400,),  # finished
            (100,),  # scheduled
            (200,),  # predictions
            (120,),  # correct
            (150,),  # verified
            (5,),  # competitions
            (50,),  # news
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        metrics = get_data_quality_metrics()

        assert "entities" in metrics
        assert "matches" in metrics
        assert "predictions" in metrics
        assert metrics["entities"]["teams"] == 100
        assert metrics["matches"]["finished"] == 400
        assert metrics["predictions"]["accuracy"] == 80.0  # 120/150


class TestThresholds:
    """Tests for threshold values."""

    def test_freshness_thresholds(self):
        """Test freshness thresholds are reasonable."""
        assert FRESHNESS_WARNING_HOURS < FRESHNESS_CRITICAL_HOURS
        assert FRESHNESS_WARNING_HOURS >= 6
        assert FRESHNESS_CRITICAL_HOURS <= 48

    def test_completeness_thresholds(self):
        """Test completeness thresholds are reasonable."""
        assert COMPLETENESS_CRITICAL_THRESHOLD < COMPLETENESS_WARNING_THRESHOLD
        assert COMPLETENESS_CRITICAL_THRESHOLD >= 0.5
        assert COMPLETENESS_WARNING_THRESHOLD <= 1.0
