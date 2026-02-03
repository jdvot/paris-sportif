"""Adaptive ensemble weights based on rolling model performance.

Dynamically adjusts model weights based on their recent accuracy over a
configurable rolling window (default 30 days).

Algorithm:
1. Track each model's prediction accuracy over rolling window
2. Calculate weights using softmax: weights = softmax(accuracy / temperature)
3. Apply minimum weight constraint to prevent any model from being ignored
4. Update weights daily or on-demand

Parameters:
- rolling_window: Number of days to consider (default 30)
- temperature: Controls weight distribution (lower = more extreme, default 0.5)
- min_weight: Minimum weight for any model (default 0.05)

References:
- Ensemble learning: https://scikit-learn.org/stable/modules/ensemble.html
- Softmax temperature: https://en.wikipedia.org/wiki/Softmax_function
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

ModelName = Literal["poisson", "elo", "xg", "xgboost", "random_forest"]

# Default static weights (used as fallback and initial values)
DEFAULT_WEIGHTS: dict[ModelName, float] = {
    "poisson": 0.25,
    "elo": 0.15,
    "xg": 0.25,
    "xgboost": 0.35,
    "random_forest": 0.0,  # Optional model
}


@dataclass
class ModelPredictionRecord:
    """Record of a single model prediction and its outcome."""

    model_name: str
    match_id: int
    predicted_outcome: Literal["home", "draw", "away"]
    actual_outcome: Literal["home", "draw", "away"]
    predicted_probs: tuple[float, float, float]  # (home, draw, away)
    prediction_date: datetime
    was_correct: bool = field(init=False)

    def __post_init__(self):
        self.was_correct = self.predicted_outcome == self.actual_outcome


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for a single model."""

    model_name: str
    accuracy: float  # Proportion of correct predictions
    brier_score: float  # Lower is better
    log_loss: float  # Lower is better
    n_predictions: int
    period_start: datetime
    period_end: datetime

    @property
    def is_valid(self) -> bool:
        """Check if enough predictions for reliable metrics."""
        return self.n_predictions >= 10


@dataclass
class AdaptiveWeights:
    """Current adaptive weights with metadata."""

    weights: dict[str, float]
    calculated_at: datetime
    period_days: int
    metrics: dict[str, ModelPerformanceMetrics] = field(default_factory=dict)
    method: str = "softmax"

    def get_weight(self, model_name: str) -> float:
        """Get weight for a specific model."""
        return self.weights.get(model_name, 0.0)

    def to_dict(self) -> dict:
        """Convert to API-friendly dictionary."""
        return {
            "weights": self.weights,
            "calculated_at": self.calculated_at.isoformat(),
            "period_days": self.period_days,
            "method": self.method,
            "metrics": {
                name: {
                    "accuracy": m.accuracy,
                    "brier_score": m.brier_score,
                    "n_predictions": m.n_predictions,
                }
                for name, m in self.metrics.items()
            },
        }


class AdaptiveWeightCalculator:
    """
    Calculates adaptive ensemble weights based on recent model performance.

    Uses softmax with temperature scaling to convert accuracy scores to weights.
    Lower temperature = more extreme weight differences.
    Higher temperature = more uniform weights.
    """

    def __init__(
        self,
        rolling_window_days: int = 30,
        temperature: float = 0.5,
        min_weight: float = 0.05,
        default_weights: dict[str, float] | None = None,
    ):
        """
        Initialize adaptive weight calculator.

        Args:
            rolling_window_days: Number of days in the rolling window
            temperature: Softmax temperature (0.1-2.0, lower = more extreme)
            min_weight: Minimum weight for any model (prevents zero weights)
            default_weights: Default weights to use when no performance data
        """
        self.rolling_window_days = rolling_window_days
        self.temperature = max(0.1, min(2.0, temperature))  # Clamp to safe range
        self.min_weight = max(0.01, min(0.20, min_weight))  # Clamp to reasonable range
        self.default_weights = default_weights or dict(DEFAULT_WEIGHTS)

        # In-memory storage for prediction records
        self._records: list[ModelPredictionRecord] = []
        self._cached_weights: AdaptiveWeights | None = None
        self._cache_valid_until: datetime | None = None

    def record_prediction(
        self,
        model_name: str,
        match_id: int,
        predicted_probs: tuple[float, float, float],
        actual_outcome: Literal["home", "draw", "away"],
        prediction_date: datetime | None = None,
    ) -> None:
        """
        Record a model's prediction and its actual outcome.

        Args:
            model_name: Name of the model (poisson, elo, xg, xgboost, random_forest)
            match_id: Unique match identifier
            predicted_probs: (home_prob, draw_prob, away_prob)
            actual_outcome: The actual match result
            prediction_date: When the prediction was made (defaults to now)
        """
        # Determine predicted outcome from probabilities
        outcomes: list[Literal["home", "draw", "away"]] = ["home", "draw", "away"]
        predicted_idx = int(np.argmax(predicted_probs))
        predicted_outcome = outcomes[predicted_idx]

        record = ModelPredictionRecord(
            model_name=model_name,
            match_id=match_id,
            predicted_outcome=predicted_outcome,
            actual_outcome=actual_outcome,
            predicted_probs=predicted_probs,
            prediction_date=prediction_date or datetime.now(),
        )

        self._records.append(record)
        self._invalidate_cache()

        logger.debug(
            f"Recorded prediction for {model_name}: "
            f"predicted={predicted_outcome}, actual={actual_outcome}, "
            f"correct={record.was_correct}"
        )

    def record_batch(
        self,
        records: list[dict],
    ) -> int:
        """
        Record multiple predictions at once.

        Args:
            records: List of dicts with keys: model_name, match_id, predicted_probs,
                    actual_outcome, prediction_date (optional)

        Returns:
            Number of records added
        """
        count = 0
        for rec in records:
            try:
                self.record_prediction(
                    model_name=rec["model_name"],
                    match_id=rec["match_id"],
                    predicted_probs=tuple(rec["predicted_probs"]),  # type: ignore
                    actual_outcome=rec["actual_outcome"],
                    prediction_date=rec.get("prediction_date"),
                )
                count += 1
            except (KeyError, TypeError) as e:
                logger.warning(f"Skipping invalid record: {e}")

        return count

    def _invalidate_cache(self) -> None:
        """Invalidate cached weights."""
        self._cache_valid_until = None

    def _get_records_in_window(self, model_name: str | None = None) -> list[ModelPredictionRecord]:
        """Get records within the rolling window."""
        cutoff = datetime.now() - timedelta(days=self.rolling_window_days)

        records = [r for r in self._records if r.prediction_date >= cutoff]

        if model_name:
            records = [r for r in records if r.model_name == model_name]

        return records

    def calculate_model_metrics(self, model_name: str) -> ModelPerformanceMetrics | None:
        """
        Calculate performance metrics for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            ModelPerformanceMetrics or None if not enough data
        """
        records = self._get_records_in_window(model_name)

        if len(records) < 5:
            return None

        # Calculate accuracy
        correct = sum(1 for r in records if r.was_correct)
        accuracy = correct / len(records)

        # Calculate Brier score (mean squared error of probabilities)
        brier_scores = []
        for r in records:
            outcome_idx = ["home", "draw", "away"].index(r.actual_outcome)
            # One-hot encode actual outcome
            actual = [0.0, 0.0, 0.0]
            actual[outcome_idx] = 1.0
            # MSE between predicted probs and actual
            mse = sum((p - a) ** 2 for p, a in zip(r.predicted_probs, actual)) / 3
            brier_scores.append(mse)
        brier_score = float(np.mean(brier_scores))

        # Calculate log loss
        log_losses = []
        for r in records:
            outcome_idx = ["home", "draw", "away"].index(r.actual_outcome)
            prob = max(r.predicted_probs[outcome_idx], 1e-10)  # Avoid log(0)
            log_losses.append(-np.log(prob))
        log_loss = float(np.mean(log_losses))

        dates = [r.prediction_date for r in records]

        return ModelPerformanceMetrics(
            model_name=model_name,
            accuracy=accuracy,
            brier_score=brier_score,
            log_loss=log_loss,
            n_predictions=len(records),
            period_start=min(dates),
            period_end=max(dates),
        )

    def calculate_weights(
        self,
        models: list[str] | None = None,
        metric: Literal["accuracy", "brier", "log_loss"] = "accuracy",
        force_refresh: bool = False,
    ) -> AdaptiveWeights:
        """
        Calculate adaptive weights for all models.

        Args:
            models: List of model names to include (defaults to all with data)
            metric: Which metric to use for weighting
            force_refresh: Force recalculation even if cache is valid

        Returns:
            AdaptiveWeights with calculated weights
        """
        # Check cache
        if (
            not force_refresh
            and self._cached_weights
            and self._cache_valid_until
            and datetime.now() < self._cache_valid_until
        ):
            return self._cached_weights

        # Get all model names with data
        if models is None:
            models = list(set(r.model_name for r in self._get_records_in_window()))

        if not models:
            # No data - use default weights
            logger.info("No performance data available, using default weights")
            return AdaptiveWeights(
                weights=self.default_weights.copy(),
                calculated_at=datetime.now(),
                period_days=self.rolling_window_days,
                method="default",
            )

        # Calculate metrics for each model
        metrics: dict[str, ModelPerformanceMetrics] = {}
        scores: dict[str, float] = {}

        for model_name in models:
            model_metrics = self.calculate_model_metrics(model_name)
            if model_metrics and model_metrics.is_valid:
                metrics[model_name] = model_metrics

                # Get score based on metric
                if metric == "accuracy":
                    scores[model_name] = model_metrics.accuracy
                elif metric == "brier":
                    # Invert brier (lower is better -> higher score)
                    scores[model_name] = 1.0 - model_metrics.brier_score
                else:  # log_loss
                    # Invert and normalize log loss
                    scores[model_name] = 1.0 / (1.0 + model_metrics.log_loss)

        if not scores:
            # Not enough data - use default weights
            logger.info("Insufficient performance data, using default weights")
            return AdaptiveWeights(
                weights=self.default_weights.copy(),
                calculated_at=datetime.now(),
                period_days=self.rolling_window_days,
                method="default",
            )

        # Apply softmax with temperature to get weights
        weights = self._softmax_weights(scores)

        # Apply minimum weight constraint
        weights = self._apply_min_weight(weights)

        result = AdaptiveWeights(
            weights=weights,
            calculated_at=datetime.now(),
            period_days=self.rolling_window_days,
            metrics=metrics,
            method=f"softmax_{metric}",
        )

        # Cache for 1 hour
        self._cached_weights = result
        self._cache_valid_until = datetime.now() + timedelta(hours=1)

        logger.info(
            f"Calculated adaptive weights: {weights} "
            f"(based on {sum(m.n_predictions for m in metrics.values())} predictions)"
        )

        return result

    def _softmax_weights(self, scores: dict[str, float]) -> dict[str, float]:
        """
        Apply softmax with temperature scaling to convert scores to weights.

        weights_i = exp(score_i / T) / sum(exp(score_j / T))
        """
        if not scores:
            return {}

        # Convert to numpy array for softmax
        model_names = list(scores.keys())
        score_values = np.array([scores[m] for m in model_names])

        # Apply temperature scaling
        scaled = score_values / self.temperature

        # Softmax (with numerical stability)
        exp_scaled = np.exp(scaled - np.max(scaled))
        softmax_weights = exp_scaled / np.sum(exp_scaled)

        return {model_names[i]: float(softmax_weights[i]) for i in range(len(model_names))}

    def _apply_min_weight(self, weights: dict[str, float]) -> dict[str, float]:
        """
        Apply minimum weight constraint and renormalize.

        Ensures no model has weight below min_weight.
        """
        if not weights:
            return weights

        # Apply minimum weight
        adjusted = {k: max(v, self.min_weight) for k, v in weights.items()}

        # Renormalize to sum to 1
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}

    def get_weight(self, model_name: str) -> float:
        """
        Get the current adaptive weight for a model.

        Args:
            model_name: Name of the model

        Returns:
            Current weight (0.0 to 1.0)
        """
        weights = self.calculate_weights()
        return weights.get_weight(model_name)

    def get_all_weights(self) -> dict[str, float]:
        """Get all current adaptive weights."""
        return self.calculate_weights().weights

    def clear_old_records(self, days_to_keep: int | None = None) -> int:
        """
        Remove records older than the specified number of days.

        Args:
            days_to_keep: Days of records to keep (defaults to rolling_window_days * 2)

        Returns:
            Number of records removed
        """
        days = days_to_keep or (self.rolling_window_days * 2)
        cutoff = datetime.now() - timedelta(days=days)

        original_count = len(self._records)
        self._records = [r for r in self._records if r.prediction_date >= cutoff]

        removed = original_count - len(self._records)
        if removed > 0:
            self._invalidate_cache()
            logger.info(f"Removed {removed} old prediction records")

        return removed

    def export_records(self) -> list[dict]:
        """Export all records as dictionaries for persistence."""
        return [
            {
                "model_name": r.model_name,
                "match_id": r.match_id,
                "predicted_outcome": r.predicted_outcome,
                "actual_outcome": r.actual_outcome,
                "predicted_probs": list(r.predicted_probs),
                "prediction_date": r.prediction_date.isoformat(),
                "was_correct": r.was_correct,
            }
            for r in self._records
        ]

    def import_records(self, records: list[dict]) -> int:
        """
        Import records from dictionaries (e.g., from database).

        Args:
            records: List of record dictionaries

        Returns:
            Number of records imported
        """
        count = 0
        for rec in records:
            try:
                self._records.append(
                    ModelPredictionRecord(
                        model_name=rec["model_name"],
                        match_id=rec["match_id"],
                        predicted_outcome=rec["predicted_outcome"],
                        actual_outcome=rec["actual_outcome"],
                        predicted_probs=tuple(rec["predicted_probs"]),  # type: ignore
                        prediction_date=(
                            datetime.fromisoformat(rec["prediction_date"])
                            if isinstance(rec["prediction_date"], str)
                            else rec["prediction_date"]
                        ),
                    )
                )
                count += 1
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping invalid record: {e}")

        if count > 0:
            self._invalidate_cache()

        return count


# Global instance with default settings
adaptive_weight_calculator = AdaptiveWeightCalculator()
