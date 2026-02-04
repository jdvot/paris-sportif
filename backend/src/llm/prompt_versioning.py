"""Prompt versioning and A/B testing system.

Provides versioned prompts with:
- Multiple versions per prompt type
- A/B testing with configurable traffic split
- Performance metrics tracking per version
- Automatic rollback on degradation
"""

import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    """Types of prompts in the system."""

    INJURY_ANALYSIS = "injury_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    MATCH_EXPLANATION = "match_explanation"
    TACTICAL_ANALYSIS = "tactical_analysis"
    DAILY_PICKS = "daily_picks"
    WEATHER_IMPACT = "weather_impact"
    MOTIVATION_FACTORS = "motivation_factors"
    HEAD_TO_HEAD = "head_to_head"


@dataclass
class PromptVersion:
    """A versioned prompt template."""

    version_id: str
    prompt_type: PromptType
    template: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    is_baseline: bool = False  # The control version for A/B tests

    @property
    def template_hash(self) -> str:
        """Get hash of template for change detection."""
        return hashlib.md5(self.template.encode()).hexdigest()[:8]


@dataclass
class PromptMetrics:
    """Performance metrics for a prompt version."""

    version_id: str
    prompt_type: PromptType
    sample_count: int = 0
    correct_predictions: int = 0
    total_brier_score: float = 0.0
    total_latency_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy rate."""
        if self.sample_count == 0:
            return 0.0
        return self.correct_predictions / self.sample_count

    @property
    def avg_brier_score(self) -> float:
        """Calculate average Brier score (lower is better)."""
        if self.sample_count == 0:
            return 1.0
        return self.total_brier_score / self.sample_count

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.sample_count == 0:
            return 0.0
        return self.total_latency_ms / self.sample_count


@dataclass
class ABTestConfig:
    """Configuration for A/B testing between prompt versions."""

    prompt_type: PromptType
    version_weights: dict[str, float]  # version_id -> weight (0.0-1.0)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    min_samples_per_version: int = 100
    significance_threshold: float = 0.05  # p-value for statistical significance

    def get_version(self) -> str:
        """Select a version based on weights (weighted random)."""
        if not self.version_weights:
            raise ValueError("No versions configured for A/B test")

        versions = list(self.version_weights.keys())
        weights = list(self.version_weights.values())

        # Normalize weights
        total = sum(weights)
        normalized = [w / total for w in weights]

        return random.choices(versions, weights=normalized, k=1)[0]


class PromptVersionManager:
    """Manages prompt versions and A/B testing.

    Features:
    - Version management with baseline and test versions
    - Traffic splitting for A/B tests
    - Metrics tracking per version
    - Automatic rollback on degradation
    """

    # Degradation threshold: if test version is 10% worse, consider rollback
    DEGRADATION_THRESHOLD = 0.10
    MIN_SAMPLES_FOR_ROLLBACK = 50

    def __init__(self) -> None:
        """Initialize the prompt version manager."""
        self._versions: dict[str, PromptVersion] = {}
        self._metrics: dict[str, PromptMetrics] = {}
        self._ab_tests: dict[PromptType, ABTestConfig] = {}
        self._active_version_cache: dict[PromptType, str] = {}

        # Register default versions
        self._register_default_versions()

    def _register_default_versions(self) -> None:
        """Register default prompt versions from prompts.py."""
        from src.llm.prompts import (
            DAILY_PICKS_SUMMARY_PROMPT,
            INJURY_ANALYSIS_PROMPT,
            MATCH_EXPLANATION_PROMPT,
            MOTIVATION_FACTORS_PROMPT,
            SENTIMENT_ANALYSIS_PROMPT,
            TACTICAL_ANALYSIS_PROMPT,
            WEATHER_IMPACT_PROMPT,
        )

        defaults = [
            (
                PromptType.INJURY_ANALYSIS,
                INJURY_ANALYSIS_PROMPT,
                "Original injury analysis with few-shot examples",
            ),
            (
                PromptType.SENTIMENT_ANALYSIS,
                SENTIMENT_ANALYSIS_PROMPT,
                "Original sentiment analysis with examples",
            ),
            (
                PromptType.MATCH_EXPLANATION,
                MATCH_EXPLANATION_PROMPT,
                "Original match explanation prompt",
            ),
            (
                PromptType.TACTICAL_ANALYSIS,
                TACTICAL_ANALYSIS_PROMPT,
                "Original tactical analysis prompt",
            ),
            (PromptType.DAILY_PICKS, DAILY_PICKS_SUMMARY_PROMPT, "Original daily picks summary"),
            (PromptType.WEATHER_IMPACT, WEATHER_IMPACT_PROMPT, "Original weather impact analysis"),
            (
                PromptType.MOTIVATION_FACTORS,
                MOTIVATION_FACTORS_PROMPT,
                "Original motivation factors analysis",
            ),
        ]

        for prompt_type, template, description in defaults:
            version = PromptVersion(
                version_id=f"{prompt_type.value}_v1",
                prompt_type=prompt_type,
                template=template,
                description=description,
                is_baseline=True,
            )
            self.register_version(version)

    def register_version(self, version: PromptVersion) -> None:
        """Register a new prompt version.

        Args:
            version: The prompt version to register
        """
        self._versions[version.version_id] = version

        # Initialize metrics if not exists
        if version.version_id not in self._metrics:
            self._metrics[version.version_id] = PromptMetrics(
                version_id=version.version_id,
                prompt_type=version.prompt_type,
            )

        # Clear cache for this prompt type
        self._active_version_cache.pop(version.prompt_type, None)

        logger.info(
            f"Registered prompt version: {version.version_id} "
            f"(type={version.prompt_type.value}, baseline={version.is_baseline})"
        )

    def create_version(
        self,
        prompt_type: PromptType,
        template: str,
        description: str,
        version_suffix: str | None = None,
    ) -> PromptVersion:
        """Create and register a new prompt version.

        Args:
            prompt_type: Type of prompt
            template: The prompt template text
            description: Description of this version
            version_suffix: Optional suffix for version_id (auto-generated if None)

        Returns:
            The created PromptVersion
        """
        # Generate version ID
        existing = [v for v in self._versions.values() if v.prompt_type == prompt_type]
        next_num = len(existing) + 1

        if version_suffix:
            version_id = f"{prompt_type.value}_{version_suffix}"
        else:
            version_id = f"{prompt_type.value}_v{next_num}"

        version = PromptVersion(
            version_id=version_id,
            prompt_type=prompt_type,
            template=template,
            description=description,
        )

        self.register_version(version)
        return version

    def get_version(self, version_id: str) -> PromptVersion | None:
        """Get a specific prompt version by ID."""
        return self._versions.get(version_id)

    def get_versions(self, prompt_type: PromptType) -> list[PromptVersion]:
        """Get all versions for a prompt type."""
        return [v for v in self._versions.values() if v.prompt_type == prompt_type]

    def get_baseline_version(self, prompt_type: PromptType) -> PromptVersion | None:
        """Get the baseline version for a prompt type."""
        for v in self._versions.values():
            if v.prompt_type == prompt_type and v.is_baseline:
                return v
        return None

    def get_active_version(self, prompt_type: PromptType) -> PromptVersion | None:
        """Get the currently active version for a prompt type.

        If A/B test is running, selects based on traffic split.
        Otherwise returns the baseline or most recent active version.
        """
        # Check if A/B test is active
        if prompt_type in self._ab_tests:
            ab_test = self._ab_tests[prompt_type]
            now = datetime.now()

            if ab_test.end_time is None or now < ab_test.end_time:
                # A/B test is active
                selected_id = ab_test.get_version()
                return self._versions.get(selected_id)

        # No A/B test, return baseline or first active version
        baseline = self.get_baseline_version(prompt_type)
        if baseline and baseline.is_active:
            return baseline

        # Find any active version
        for v in self._versions.values():
            if v.prompt_type == prompt_type and v.is_active:
                return v

        return None

    def get_prompt(self, prompt_type: PromptType, **kwargs: Any) -> tuple[str, str]:
        """Get formatted prompt for the active version.

        Args:
            prompt_type: Type of prompt needed
            **kwargs: Variables to format into the template

        Returns:
            Tuple of (formatted_prompt, version_id)
        """
        version = self.get_active_version(prompt_type)

        if version is None:
            raise ValueError(f"No active version found for prompt type: {prompt_type}")

        formatted = version.template.format(**kwargs)
        return formatted, version.version_id

    # A/B Testing methods
    def start_ab_test(
        self,
        prompt_type: PromptType,
        version_weights: dict[str, float],
        duration_days: int | None = None,
    ) -> ABTestConfig:
        """Start an A/B test for a prompt type.

        Args:
            prompt_type: Type of prompt to test
            version_weights: Dict of version_id -> traffic weight
            duration_days: Test duration in days (None for indefinite)

        Returns:
            The created ABTestConfig
        """
        # Validate versions exist
        for version_id in version_weights:
            if version_id not in self._versions:
                raise ValueError(f"Version not found: {version_id}")

        end_time = None
        if duration_days:
            end_time = datetime.now() + timedelta(days=duration_days)

        config = ABTestConfig(
            prompt_type=prompt_type,
            version_weights=version_weights,
            end_time=end_time,
        )

        self._ab_tests[prompt_type] = config

        logger.info(
            f"Started A/B test for {prompt_type.value}: "
            f"versions={list(version_weights.keys())}, weights={list(version_weights.values())}"
        )

        return config

    def stop_ab_test(self, prompt_type: PromptType) -> bool:
        """Stop an active A/B test.

        Args:
            prompt_type: Type of prompt

        Returns:
            True if test was stopped, False if no test was running
        """
        if prompt_type in self._ab_tests:
            del self._ab_tests[prompt_type]
            logger.info(f"Stopped A/B test for {prompt_type.value}")
            return True
        return False

    def get_ab_test(self, prompt_type: PromptType) -> ABTestConfig | None:
        """Get the A/B test config for a prompt type."""
        return self._ab_tests.get(prompt_type)

    # Metrics tracking methods
    def record_result(
        self,
        version_id: str,
        was_correct: bool,
        brier_score: float | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """Record a prediction result for a version.

        Args:
            version_id: The version that was used
            was_correct: Whether prediction was correct
            brier_score: Optional Brier score
            latency_ms: Optional response latency
        """
        if version_id not in self._metrics:
            version = self._versions.get(version_id)
            if not version:
                logger.warning(f"Recording result for unknown version: {version_id}")
                return
            self._metrics[version_id] = PromptMetrics(
                version_id=version_id,
                prompt_type=version.prompt_type,
            )

        metrics = self._metrics[version_id]
        metrics.sample_count += 1
        if was_correct:
            metrics.correct_predictions += 1
        if brier_score is not None:
            metrics.total_brier_score += brier_score
        if latency_ms is not None:
            metrics.total_latency_ms += latency_ms
        metrics.updated_at = datetime.now()

    def get_metrics(self, version_id: str) -> PromptMetrics | None:
        """Get metrics for a specific version."""
        return self._metrics.get(version_id)

    def get_all_metrics(self, prompt_type: PromptType) -> list[PromptMetrics]:
        """Get metrics for all versions of a prompt type."""
        return [m for m in self._metrics.values() if m.prompt_type == prompt_type]

    def compare_versions(
        self,
        prompt_type: PromptType,
    ) -> dict[str, dict[str, Any]]:
        """Compare metrics across versions.

        Args:
            prompt_type: Type of prompt to compare

        Returns:
            Dict with version_id -> metrics comparison
        """
        result: dict[str, dict[str, Any]] = {}
        baseline = self.get_baseline_version(prompt_type)

        for metrics in self.get_all_metrics(prompt_type):
            version = self._versions.get(metrics.version_id)
            is_baseline = version is not None and version.is_baseline

            comparison: dict[str, Any] = {
                "version_id": metrics.version_id,
                "is_baseline": is_baseline,
                "sample_count": metrics.sample_count,
                "accuracy": metrics.accuracy,
                "avg_brier_score": metrics.avg_brier_score,
                "avg_latency_ms": metrics.avg_latency_ms,
            }

            # Calculate relative performance vs baseline
            if baseline and not is_baseline:
                baseline_metrics = self._metrics.get(baseline.version_id)
                if baseline_metrics and baseline_metrics.sample_count > 0:
                    if baseline_metrics.accuracy > 0:
                        comparison["accuracy_vs_baseline"] = (
                            metrics.accuracy - baseline_metrics.accuracy
                        ) / baseline_metrics.accuracy
                    if baseline_metrics.avg_brier_score > 0:
                        comparison["brier_vs_baseline"] = (
                            baseline_metrics.avg_brier_score - metrics.avg_brier_score
                        ) / baseline_metrics.avg_brier_score

            result[metrics.version_id] = comparison

        return result

    # Rollback logic
    def check_rollback_needed(self, prompt_type: PromptType) -> str | None:
        """Check if rollback is needed based on performance degradation.

        Args:
            prompt_type: Type of prompt to check

        Returns:
            version_id to rollback to, or None if no rollback needed
        """
        ab_test = self._ab_tests.get(prompt_type)
        if not ab_test:
            return None

        baseline = self.get_baseline_version(prompt_type)
        if not baseline:
            return None

        baseline_metrics = self._metrics.get(baseline.version_id)
        if not baseline_metrics or baseline_metrics.sample_count < self.MIN_SAMPLES_FOR_ROLLBACK:
            return None

        # Check each test version
        for version_id in ab_test.version_weights:
            if version_id == baseline.version_id:
                continue

            test_metrics = self._metrics.get(version_id)
            if not test_metrics or test_metrics.sample_count < self.MIN_SAMPLES_FOR_ROLLBACK:
                continue

            # Check for degradation
            if baseline_metrics.accuracy > 0:
                relative_diff = (
                    baseline_metrics.accuracy - test_metrics.accuracy
                ) / baseline_metrics.accuracy

                if relative_diff > self.DEGRADATION_THRESHOLD:
                    logger.warning(
                        f"Version {version_id} shows {relative_diff:.1%} degradation "
                        f"vs baseline (threshold: {self.DEGRADATION_THRESHOLD:.1%}). "
                        f"Recommending rollback."
                    )
                    return baseline.version_id

        return None

    def rollback_to_baseline(self, prompt_type: PromptType) -> bool:
        """Rollback to baseline version by stopping A/B test.

        Args:
            prompt_type: Type of prompt

        Returns:
            True if rollback was performed
        """
        if self.stop_ab_test(prompt_type):
            logger.info(f"Rolled back {prompt_type.value} to baseline")
            return True
        return False

    # Serialization for persistence
    def export_state(self) -> dict[str, Any]:
        """Export current state for persistence."""
        return {
            "versions": [
                {
                    "version_id": v.version_id,
                    "prompt_type": v.prompt_type.value,
                    "template": v.template,
                    "description": v.description,
                    "created_at": v.created_at.isoformat(),
                    "is_active": v.is_active,
                    "is_baseline": v.is_baseline,
                }
                for v in self._versions.values()
            ],
            "metrics": [
                {
                    "version_id": m.version_id,
                    "prompt_type": m.prompt_type.value,
                    "sample_count": m.sample_count,
                    "correct_predictions": m.correct_predictions,
                    "total_brier_score": m.total_brier_score,
                    "total_latency_ms": m.total_latency_ms,
                    "created_at": m.created_at.isoformat(),
                    "updated_at": m.updated_at.isoformat(),
                }
                for m in self._metrics.values()
            ],
            "ab_tests": [
                {
                    "prompt_type": t.prompt_type.value,
                    "version_weights": t.version_weights,
                    "start_time": t.start_time.isoformat(),
                    "end_time": t.end_time.isoformat() if t.end_time else None,
                }
                for t in self._ab_tests.values()
            ],
        }

    def import_state(self, state: dict[str, Any]) -> int:
        """Import state from persistence.

        Args:
            state: The state dict from export_state

        Returns:
            Number of items imported
        """
        count = 0

        # Import versions (skip defaults)
        for v_data in state.get("versions", []):
            version_id = v_data["version_id"]
            if version_id not in self._versions:
                version = PromptVersion(
                    version_id=version_id,
                    prompt_type=PromptType(v_data["prompt_type"]),
                    template=v_data["template"],
                    description=v_data["description"],
                    created_at=datetime.fromisoformat(v_data["created_at"]),
                    is_active=v_data["is_active"],
                    is_baseline=v_data["is_baseline"],
                )
                self.register_version(version)
                count += 1

        # Import metrics
        for m_data in state.get("metrics", []):
            version_id = m_data["version_id"]
            self._metrics[version_id] = PromptMetrics(
                version_id=version_id,
                prompt_type=PromptType(m_data["prompt_type"]),
                sample_count=m_data["sample_count"],
                correct_predictions=m_data["correct_predictions"],
                total_brier_score=m_data["total_brier_score"],
                total_latency_ms=m_data["total_latency_ms"],
                created_at=datetime.fromisoformat(m_data["created_at"]),
                updated_at=datetime.fromisoformat(m_data["updated_at"]),
            )
            count += 1

        # Import A/B tests
        for t_data in state.get("ab_tests", []):
            prompt_type = PromptType(t_data["prompt_type"])
            end_time = None
            if t_data["end_time"]:
                end_time = datetime.fromisoformat(t_data["end_time"])

            self._ab_tests[prompt_type] = ABTestConfig(
                prompt_type=prompt_type,
                version_weights=t_data["version_weights"],
                start_time=datetime.fromisoformat(t_data["start_time"]),
                end_time=end_time,
            )
            count += 1

        return count


# Global instance
prompt_version_manager = PromptVersionManager()
