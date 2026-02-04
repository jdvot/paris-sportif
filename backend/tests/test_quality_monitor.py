"""Tests for data quality monitoring system."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.data.quality_monitor import (
    COMPLETENESS_CRITICAL_THRESHOLD,
    COMPLETENESS_WARNING_THRESHOLD,
    FRESHNESS_CRITICAL_HOURS,
    FRESHNESS_WARNING_HOURS,
    AlertLevel,
    DataQualityCheck,
    DataQualityReport,
    check_completeness,
    check_consistency,
    check_freshness,
    check_range_validation,
    get_data_quality_metrics,
    run_quality_check,
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
        check = DataQualityCheck(name="Test", status=AlertLevel.OK, message="OK")
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

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_fresh_data(self, mock_get_uow):
        """Test when data is fresh."""
        now = datetime.now(UTC).replace(tzinfo=None)
        recent = now - timedelta(hours=1)

        # Setup mock UoW
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = recent
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_freshness()

        assert result.status == AlertLevel.OK
        assert result.value < FRESHNESS_WARNING_HOURS

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_no_data(self, mock_get_uow):
        """Test critical when no data exists."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_freshness()

        assert result.status == AlertLevel.CRITICAL
        assert "No data found" in result.message


class TestCheckCompleteness:
    """Tests for completeness check."""

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_complete_data(self, mock_get_uow):
        """Test when data is complete."""
        mock_session = MagicMock()

        # Create different mock results for each query
        results = iter([
            100,  # total teams
            100,  # total matches
            50,   # finished matches
            50,   # matches with score
            100,  # total predictions
            90,   # predictions with explanation
        ])

        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = lambda: next(results)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_completeness()

        assert result.status == AlertLevel.OK
        assert result.value >= COMPLETENESS_WARNING_THRESHOLD * 100


class TestCheckRangeValidation:
    """Tests for range validation check."""

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_valid_ranges(self, mock_get_uow):
        """Test when all values are in valid ranges."""
        mock_session = MagicMock()
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = []  # No anomalies

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_range_validation()

        assert result.status == AlertLevel.OK
        assert result.value == 0

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_invalid_confidence(self, mock_get_uow):
        """Test detection of invalid confidence values."""
        mock_session = MagicMock()

        # Mock prediction with invalid confidence
        mock_pred = MagicMock()
        mock_pred.id = 1
        mock_pred.home_prob = 0.5
        mock_pred.draw_prob = 0.3
        mock_pred.away_prob = 0.2
        mock_pred.confidence = 1.5  # Invalid - over 1.0

        mock_scalars_result = MagicMock()
        # First call (probs) - no anomalies, second call (confidence) - has anomaly
        mock_scalars_result.all.side_effect = [[], [mock_pred], []]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_range_validation()

        assert result.status == AlertLevel.WARNING
        assert result.value == 1

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_many_anomalies_critical(self, mock_get_uow):
        """Test critical status with many anomalies."""
        mock_session = MagicMock()

        # Create many mock predictions with invalid probs
        invalid_preds = []
        for i in range(15):
            mock_pred = MagicMock()
            mock_pred.id = i
            mock_pred.home_prob = 0.5
            mock_pred.draw_prob = 0.5
            mock_pred.away_prob = 0.5  # Sum > 1
            invalid_preds.append(mock_pred)

        mock_scalars_result = MagicMock()
        mock_scalars_result.all.side_effect = [invalid_preds, [], []]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_range_validation()

        assert result.status == AlertLevel.CRITICAL
        assert result.value > 10


class TestCheckConsistency:
    """Tests for consistency check."""

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_consistent_data(self, mock_get_uow):
        """Test when data is consistent."""
        mock_session = MagicMock()

        mock_result_all = MagicMock()
        mock_result_all.all.return_value = []  # No duplicates

        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = []  # No self-matches

        mock_result_scalar = MagicMock()
        mock_result_scalar.scalar_one.return_value = 0  # No orphans/missing scores

        # Setup different returns for different queries
        call_count = [0]
        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] <= 2:
                mock_result.all.return_value = []  # Duplicate checks
            elif call_count[0] == 3:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = []  # Self-matches
                mock_result.scalars.return_value = mock_scalars
            else:
                mock_result.scalar_one.return_value = 0  # Counts
            return mock_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_consistency()

        assert result.status == AlertLevel.OK
        assert result.value == 0

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_duplicate_matches(self, mock_get_uow):
        """Test detection of duplicate matches."""
        mock_session = MagicMock()

        call_count = [0]
        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                # Duplicate matches found
                mock_result.all.return_value = [(1, 2, "2026-01-15", 2)]
            elif call_count[0] == 2:
                mock_result.all.return_value = []  # No duplicate teams
            elif call_count[0] == 3:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = []  # No self-matches
                mock_result.scalars.return_value = mock_scalars
            else:
                mock_result.scalar_one.return_value = 0  # Counts
            return mock_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_consistency()

        assert result.status == AlertLevel.WARNING
        assert result.value == 1

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_many_issues_critical(self, mock_get_uow):
        """Test critical status with many consistency issues."""
        mock_session = MagicMock()

        # Create many duplicate match entries
        duplicates = [(i, i + 1, f"2026-01-{i:02d}", 2) for i in range(1, 10)]

        call_count = [0]
        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.all.return_value = duplicates  # Many duplicates
            elif call_count[0] == 2:
                mock_result.all.return_value = []
            elif call_count[0] == 3:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = []
                mock_result.scalars.return_value = mock_scalars
            else:
                mock_result.scalar_one.return_value = 0
            return mock_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        result = await check_consistency()

        assert result.status == AlertLevel.CRITICAL


class TestRunQualityCheck:
    """Tests for the main quality check runner."""

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.check_freshness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_completeness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_range_validation", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_consistency", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.get_data_quality_metrics", new_callable=AsyncMock)
    async def test_all_ok(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test when all checks pass."""
        ok_check = DataQualityCheck(name="Test", status=AlertLevel.OK, message="OK")
        mock_freshness.return_value = ok_check
        mock_completeness.return_value = ok_check
        mock_range.return_value = DataQualityCheck(
            name="Range", status=AlertLevel.OK, message="OK", details={}
        )
        mock_consistency.return_value = DataQualityCheck(
            name="Consistency", status=AlertLevel.OK, message="OK", details={}
        )
        mock_metrics.return_value = {}

        report = await run_quality_check()

        assert report.overall_status == AlertLevel.OK

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.check_freshness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_completeness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_range_validation", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_consistency", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.get_data_quality_metrics", new_callable=AsyncMock)
    async def test_any_critical_is_critical(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test that any critical check makes overall status critical."""
        ok_check = DataQualityCheck(name="Test", status=AlertLevel.OK, message="OK")
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

        report = await run_quality_check()

        assert report.overall_status == AlertLevel.CRITICAL

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.check_freshness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_completeness", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_range_validation", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.check_consistency", new_callable=AsyncMock)
    @patch("src.data.quality_monitor.get_data_quality_metrics", new_callable=AsyncMock)
    async def test_any_warning_is_warning(
        self,
        mock_metrics,
        mock_consistency,
        mock_range,
        mock_completeness,
        mock_freshness,
    ):
        """Test that any warning check makes overall status warning."""
        ok_check = DataQualityCheck(name="Test", status=AlertLevel.OK, message="OK")
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

        report = await run_quality_check()

        assert report.overall_status == AlertLevel.WARNING


class TestGetDataQualityMetrics:
    """Tests for metrics collection."""

    @pytest.mark.asyncio
    @patch("src.data.quality_monitor.get_uow")
    async def test_metrics_structure(self, mock_get_uow):
        """Test that metrics have expected structure."""
        mock_session = MagicMock()

        # Return values for each count query
        values = iter([100, 500, 400, 100, 200, 120, 150])

        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = lambda: next(values)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_uow = MagicMock()
        mock_uow.session = mock_session
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_get_uow.return_value = mock_uow

        metrics = await get_data_quality_metrics()

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
