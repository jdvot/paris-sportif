"""Tests for prompt versioning and A/B testing system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.llm.prompt_versioning import (
    ABTestConfig,
    PromptMetrics,
    PromptType,
    PromptVersion,
    PromptVersionManager,
)


class TestPromptVersion:
    """Tests for PromptVersion dataclass."""

    def test_create_version(self):
        """Test creating a prompt version."""
        version = PromptVersion(
            version_id="test_v1",
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Analyze injury for {team_name}",
            description="Test version",
        )

        assert version.version_id == "test_v1"
        assert version.prompt_type == PromptType.INJURY_ANALYSIS
        assert version.is_active is True
        assert version.is_baseline is False
        assert isinstance(version.created_at, datetime)

    def test_template_hash(self):
        """Test template hash generation."""
        version = PromptVersion(
            version_id="test_v1",
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Analyze injury for {team_name}",
            description="Test version",
        )

        hash1 = version.template_hash
        assert len(hash1) == 8  # MD5 truncated to 8 chars

        # Same template should produce same hash
        version2 = PromptVersion(
            version_id="test_v2",
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Analyze injury for {team_name}",
            description="Different desc",
        )
        assert version.template_hash == version2.template_hash

        # Different template should produce different hash
        version3 = PromptVersion(
            version_id="test_v3",
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Different template",
            description="Test version",
        )
        assert version.template_hash != version3.template_hash


class TestPromptMetrics:
    """Tests for PromptMetrics dataclass."""

    def test_empty_metrics(self):
        """Test metrics with no samples."""
        metrics = PromptMetrics(
            version_id="test_v1",
            prompt_type=PromptType.INJURY_ANALYSIS,
        )

        assert metrics.sample_count == 0
        assert metrics.accuracy == 0.0
        assert metrics.avg_brier_score == 1.0  # Worst possible when no samples
        assert metrics.avg_latency_ms == 0.0

    def test_metrics_calculation(self):
        """Test accuracy and average calculations."""
        metrics = PromptMetrics(
            version_id="test_v1",
            prompt_type=PromptType.INJURY_ANALYSIS,
            sample_count=10,
            correct_predictions=7,
            total_brier_score=2.0,
            total_latency_ms=1000.0,
        )

        assert metrics.accuracy == 0.7
        assert metrics.avg_brier_score == 0.2
        assert metrics.avg_latency_ms == 100.0


class TestABTestConfig:
    """Tests for ABTestConfig."""

    def test_get_version_weighted(self):
        """Test weighted random selection."""
        config = ABTestConfig(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"v1": 1.0, "v2": 0.0},  # 100% v1
        )

        # Should always return v1 with 100% weight
        for _ in range(10):
            assert config.get_version() == "v1"

    def test_get_version_normalized(self):
        """Test that weights are normalized."""
        config = ABTestConfig(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"v1": 50, "v2": 50},  # Should normalize to 0.5/0.5
        )

        # Run many times to ensure both versions selected
        versions_seen = set()
        for _ in range(100):
            versions_seen.add(config.get_version())

        assert "v1" in versions_seen
        assert "v2" in versions_seen

    def test_get_version_empty_weights(self):
        """Test error on empty weights."""
        config = ABTestConfig(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={},
        )

        with pytest.raises(ValueError, match="No versions configured"):
            config.get_version()


class TestPromptVersionManager:
    """Tests for PromptVersionManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return PromptVersionManager()

    def test_default_versions_registered(self, manager):
        """Test that default versions are registered on init."""
        # Should have default versions for all prompt types
        for prompt_type in [
            PromptType.INJURY_ANALYSIS,
            PromptType.SENTIMENT_ANALYSIS,
            PromptType.MATCH_EXPLANATION,
        ]:
            versions = manager.get_versions(prompt_type)
            assert len(versions) >= 1
            baseline = manager.get_baseline_version(prompt_type)
            assert baseline is not None
            assert baseline.is_baseline is True

    def test_create_version(self, manager):
        """Test creating new versions."""
        version = manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="New template for {team_name}",
            description="New test version",
        )

        assert version.version_id == "injury_analysis_v2"
        assert version.is_baseline is False

        # Should be retrievable
        retrieved = manager.get_version("injury_analysis_v2")
        assert retrieved is not None
        assert retrieved.template == "New template for {team_name}"

    def test_create_version_with_suffix(self, manager):
        """Test creating version with custom suffix."""
        version = manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Custom version",
            description="Custom",
            version_suffix="custom_v1",
        )

        assert version.version_id == "injury_analysis_custom_v1"

    def test_get_active_version_without_ab_test(self, manager):
        """Test getting active version without A/B test."""
        active = manager.get_active_version(PromptType.INJURY_ANALYSIS)

        assert active is not None
        assert active.is_baseline is True  # Should return baseline when no A/B test

    def test_get_prompt(self, manager):
        """Test getting formatted prompt."""
        prompt, version_id = manager.get_prompt(
            PromptType.INJURY_ANALYSIS,
            team_name="Liverpool",
            news_text="Salah injured",
        )

        assert "Liverpool" in prompt
        assert "Salah injured" in prompt
        assert version_id.startswith("injury_analysis_")

    def test_start_ab_test(self, manager):
        """Test starting an A/B test."""
        # First create a test version
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test version {team_name}",
            description="For A/B test",
        )

        config = manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={
                "injury_analysis_v1": 0.5,
                "injury_analysis_v2": 0.5,
            },
            duration_days=7,
        )

        assert config is not None
        assert config.prompt_type == PromptType.INJURY_ANALYSIS
        assert config.end_time is not None

        # Should get random version during A/B test
        versions_seen = set()
        for _ in range(50):
            active = manager.get_active_version(PromptType.INJURY_ANALYSIS)
            versions_seen.add(active.version_id)

        assert len(versions_seen) == 2

    def test_stop_ab_test(self, manager):
        """Test stopping an A/B test."""
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test version",
            description="For A/B test",
        )

        manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"injury_analysis_v1": 0.5, "injury_analysis_v2": 0.5},
        )

        stopped = manager.stop_ab_test(PromptType.INJURY_ANALYSIS)
        assert stopped is True

        # Should return baseline after stopping
        active = manager.get_active_version(PromptType.INJURY_ANALYSIS)
        assert active.is_baseline is True

    def test_record_result(self, manager):
        """Test recording prediction results."""
        version_id = "injury_analysis_v1"

        manager.record_result(
            version_id=version_id,
            was_correct=True,
            brier_score=0.1,
            latency_ms=150.0,
        )

        metrics = manager.get_metrics(version_id)
        assert metrics is not None
        assert metrics.sample_count == 1
        assert metrics.correct_predictions == 1
        assert metrics.avg_brier_score == 0.1
        assert metrics.avg_latency_ms == 150.0

    def test_record_multiple_results(self, manager):
        """Test recording multiple results."""
        version_id = "injury_analysis_v1"

        manager.record_result(version_id=version_id, was_correct=True, brier_score=0.1)
        manager.record_result(version_id=version_id, was_correct=True, brier_score=0.2)
        manager.record_result(version_id=version_id, was_correct=False, brier_score=0.4)

        metrics = manager.get_metrics(version_id)
        assert metrics.sample_count == 3
        assert metrics.correct_predictions == 2
        assert metrics.accuracy == pytest.approx(0.666, rel=0.01)

    def test_compare_versions(self, manager):
        """Test comparing version metrics."""
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test v2",
            description="For comparison",
        )

        # Record results for both versions
        manager.record_result("injury_analysis_v1", was_correct=True, brier_score=0.15)
        manager.record_result("injury_analysis_v1", was_correct=True, brier_score=0.15)
        manager.record_result("injury_analysis_v2", was_correct=True, brier_score=0.10)
        manager.record_result("injury_analysis_v2", was_correct=False, brier_score=0.30)

        comparison = manager.compare_versions(PromptType.INJURY_ANALYSIS)

        assert "injury_analysis_v1" in comparison
        assert "injury_analysis_v2" in comparison
        assert comparison["injury_analysis_v1"]["is_baseline"] is True
        assert comparison["injury_analysis_v2"]["is_baseline"] is False

    def test_check_rollback_needed(self, manager):
        """Test rollback detection on performance degradation."""
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test v2",
            description="For rollback test",
        )

        # Start A/B test
        manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"injury_analysis_v1": 0.5, "injury_analysis_v2": 0.5},
        )

        # Simulate good baseline performance (80% accuracy)
        for _ in range(60):
            manager.record_result("injury_analysis_v1", was_correct=True)
        for _ in range(15):
            manager.record_result("injury_analysis_v1", was_correct=False)

        # Simulate poor test version performance (50% accuracy)
        for _ in range(30):
            manager.record_result("injury_analysis_v2", was_correct=True)
        for _ in range(30):
            manager.record_result("injury_analysis_v2", was_correct=False)

        # Should recommend rollback (50% vs 80% = 37.5% degradation > 10% threshold)
        rollback_to = manager.check_rollback_needed(PromptType.INJURY_ANALYSIS)
        assert rollback_to == "injury_analysis_v1"

    def test_no_rollback_when_performing_well(self, manager):
        """Test no rollback when test version performs well."""
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test v2",
            description="For rollback test",
        )

        manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"injury_analysis_v1": 0.5, "injury_analysis_v2": 0.5},
        )

        # Both versions perform similarly
        for _ in range(60):
            manager.record_result("injury_analysis_v1", was_correct=True)
            manager.record_result("injury_analysis_v2", was_correct=True)
        for _ in range(15):
            manager.record_result("injury_analysis_v1", was_correct=False)
            manager.record_result("injury_analysis_v2", was_correct=False)

        # Should not recommend rollback
        rollback_to = manager.check_rollback_needed(PromptType.INJURY_ANALYSIS)
        assert rollback_to is None

    def test_export_import_state(self, manager):
        """Test state serialization and restoration."""
        # Create versions and record results
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test v2",
            description="For export test",
        )
        manager.record_result("injury_analysis_v1", was_correct=True, brier_score=0.1)
        manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"injury_analysis_v1": 0.5, "injury_analysis_v2": 0.5},
        )

        # Export state
        state = manager.export_state()

        assert "versions" in state
        assert "metrics" in state
        assert "ab_tests" in state
        assert len(state["versions"]) >= 2

        # Import into new manager (simulating restart)
        new_manager = PromptVersionManager()
        imported = new_manager.import_state(state)

        # Should have imported metrics and A/B test
        assert imported >= 1

    def test_rollback_to_baseline(self, manager):
        """Test rollback stops A/B test."""
        manager.create_version(
            prompt_type=PromptType.INJURY_ANALYSIS,
            template="Test v2",
            description="For rollback",
        )
        manager.start_ab_test(
            prompt_type=PromptType.INJURY_ANALYSIS,
            version_weights={"injury_analysis_v1": 0.5, "injury_analysis_v2": 0.5},
        )

        result = manager.rollback_to_baseline(PromptType.INJURY_ANALYSIS)
        assert result is True

        # A/B test should be stopped
        ab_test = manager.get_ab_test(PromptType.INJURY_ANALYSIS)
        assert ab_test is None


class TestPromptTypeEnum:
    """Tests for PromptType enum."""

    def test_all_prompt_types(self):
        """Test all prompt types are defined."""
        expected_types = [
            "INJURY_ANALYSIS",
            "SENTIMENT_ANALYSIS",
            "MATCH_EXPLANATION",
            "TACTICAL_ANALYSIS",
            "DAILY_PICKS",
            "WEATHER_IMPACT",
            "MOTIVATION_FACTORS",
            "HEAD_TO_HEAD",
        ]

        for type_name in expected_types:
            assert hasattr(PromptType, type_name)

    def test_prompt_type_values(self):
        """Test prompt type string values."""
        assert PromptType.INJURY_ANALYSIS.value == "injury_analysis"
        assert PromptType.SENTIMENT_ANALYSIS.value == "sentiment_analysis"
