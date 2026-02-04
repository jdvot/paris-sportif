"""Probability calibration for football match predictions.

Implements calibration methods to improve the reliability of predicted probabilities:
- Platt Scaling (sigmoid): Logistic regression on prediction scores
- Isotonic Regression: Non-parametric monotonic transformation

Calibration ensures that when we predict 70% probability, the event occurs ~70% of the time.

References:
- Platt, J. (1999). Probabilistic Outputs for Support Vector Machines
- Zadrozny, B. & Elkan, C. (2002). Transforming Classifier Scores into Calibration
"""

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.calibration import calibration_curve
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn not available - calibration features disabled")


@dataclass
class CalibrationMetrics:
    """Calibration quality metrics."""

    brier_score: float  # Lower is better (0 = perfect)
    expected_calibration_error: float  # ECE - Lower is better
    max_calibration_error: float  # MCE - Maximum bin error
    reliability_data: dict  # For plotting reliability diagram
    n_samples: int


@dataclass
class CalibratedProbabilities:
    """Calibrated probability output."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    calibration_method: str
    original_probs: tuple[float, float, float]


class ProbabilityCalibrator:
    """
    Calibrates predicted probabilities using Platt Scaling or Isotonic Regression.

    Usage:
        1. Train calibrator on validation data with known outcomes
        2. Apply calibration to new predictions

    Methods:
        - 'platt' (sigmoid): Fits logistic regression, good for small datasets
        - 'isotonic': Non-parametric, more flexible, needs more data
    """

    def __init__(self, method: Literal["platt", "isotonic"] = "isotonic"):
        """
        Initialize calibrator.

        Args:
            method: 'platt' for Platt scaling, 'isotonic' for isotonic regression
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("sklearn required for calibration")

        self.method = method
        self.calibrators: dict[str, IsotonicRegression | LogisticRegression] = {}
        self.is_fitted = False
        self._training_metrics: CalibrationMetrics | None = None

    def fit(
        self,
        predicted_probs: np.ndarray,
        true_outcomes: np.ndarray,
    ) -> CalibrationMetrics:
        """
        Fit calibration models on validation data.

        Args:
            predicted_probs: Array of shape (N, 3) with [home, draw, away] probabilities
            true_outcomes: Array of shape (N,) with actual outcomes (0=home, 1=draw, 2=away)

        Returns:
            CalibrationMetrics before calibration
        """
        if len(predicted_probs) < 50:
            logger.warning("Less than 50 samples - calibration may be unreliable")

        # Calculate pre-calibration metrics
        pre_metrics = self._calculate_metrics(predicted_probs, true_outcomes)

        # Fit separate calibrator for each outcome
        outcome_names = ["home", "draw", "away"]

        for i, outcome in enumerate(outcome_names):
            # Binary labels: 1 if this outcome occurred, 0 otherwise
            y_binary = (true_outcomes == i).astype(int)
            probs = predicted_probs[:, i]

            if self.method == "platt":
                # Platt scaling: logistic regression on log-odds
                calibrator = LogisticRegression(solver="lbfgs", max_iter=1000)
                # Reshape for sklearn
                calibrator.fit(probs.reshape(-1, 1), y_binary)
            else:
                # Isotonic regression: non-parametric monotonic transformation
                calibrator = IsotonicRegression(out_of_bounds="clip")
                calibrator.fit(probs, y_binary)

            self.calibrators[outcome] = calibrator

        self.is_fitted = True
        self._training_metrics = pre_metrics

        logger.info(
            f"Calibration fitted with {self.method} method on {len(predicted_probs)} samples. "
            f"Pre-calibration Brier: {pre_metrics.brier_score:.4f}, ECE: {pre_metrics.expected_calibration_error:.4f}"
        )

        return pre_metrics

    def calibrate(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
    ) -> CalibratedProbabilities:
        """
        Calibrate a single prediction.

        Args:
            home_prob: Predicted probability of home win
            draw_prob: Predicted probability of draw
            away_prob: Predicted probability of away win

        Returns:
            CalibratedProbabilities with adjusted probabilities
        """
        if not self.is_fitted:
            # Return original if not fitted
            return CalibratedProbabilities(
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                calibration_method="none",
                original_probs=(home_prob, draw_prob, away_prob),
            )

        probs = {"home": home_prob, "draw": draw_prob, "away": away_prob}
        calibrated = {}

        for outcome, prob in probs.items():
            calibrator = self.calibrators[outcome]

            if self.method == "platt":
                # Platt: use predict_proba
                cal_prob = calibrator.predict_proba([[prob]])[0, 1]
            else:
                # Isotonic: direct transform
                cal_prob = calibrator.predict([prob])[0]

            # Clip to valid range
            calibrated[outcome] = float(np.clip(cal_prob, 0.01, 0.99))

        # Normalize to sum to 1
        total = sum(calibrated.values())
        if total > 0:
            for outcome in calibrated:
                calibrated[outcome] /= total

        return CalibratedProbabilities(
            home_win_prob=calibrated["home"],
            draw_prob=calibrated["draw"],
            away_win_prob=calibrated["away"],
            calibration_method=self.method,
            original_probs=(home_prob, draw_prob, away_prob),
        )

    def calibrate_batch(
        self,
        predicted_probs: np.ndarray,
    ) -> np.ndarray:
        """
        Calibrate a batch of predictions.

        Args:
            predicted_probs: Array of shape (N, 3) with [home, draw, away] probabilities

        Returns:
            Array of shape (N, 3) with calibrated probabilities
        """
        if not self.is_fitted:
            return predicted_probs

        calibrated = np.zeros_like(predicted_probs)
        outcome_indices = {"home": 0, "draw": 1, "away": 2}

        for outcome, idx in outcome_indices.items():
            probs = predicted_probs[:, idx]
            calibrator = self.calibrators[outcome]

            if self.method == "platt":
                cal_probs = calibrator.predict_proba(probs.reshape(-1, 1))[:, 1]
            else:
                cal_probs = calibrator.predict(probs)

            calibrated[:, idx] = np.clip(cal_probs, 0.01, 0.99)

        # Normalize rows to sum to 1
        row_sums = calibrated.sum(axis=1, keepdims=True)
        calibrated = calibrated / row_sums

        return calibrated

    def _calculate_metrics(
        self,
        predicted_probs: np.ndarray,
        true_outcomes: np.ndarray,
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """
        Calculate calibration metrics.

        Args:
            predicted_probs: Array of shape (N, 3) with probabilities
            true_outcomes: Array of shape (N,) with actual outcomes
            n_bins: Number of bins for reliability diagram

        Returns:
            CalibrationMetrics
        """
        n_samples = len(true_outcomes)

        # Brier score: mean squared error of probabilities
        # For multi-class: average of one-vs-rest Brier scores
        brier_scores = []
        reliability_data = {"bins": [], "accuracy": [], "confidence": [], "counts": []}

        for i in range(3):  # For each outcome
            y_binary = (true_outcomes == i).astype(float)
            probs = predicted_probs[:, i]

            # Brier score for this class
            brier = np.mean((probs - y_binary) ** 2)
            brier_scores.append(brier)

            # Reliability curve (calibration curve)
            try:
                fraction_positive, mean_predicted = calibration_curve(
                    y_binary, probs, n_bins=n_bins, strategy="uniform"
                )
                reliability_data["bins"].append(mean_predicted.tolist())
                reliability_data["accuracy"].append(fraction_positive.tolist())
            except ValueError:
                # Not enough data for calibration curve
                pass

        avg_brier = float(np.mean(brier_scores))

        # Expected Calibration Error (ECE)
        # Weighted average of |accuracy - confidence| per bin
        ece = self._calculate_ece(predicted_probs, true_outcomes, n_bins)

        # Maximum Calibration Error (MCE)
        mce = self._calculate_mce(predicted_probs, true_outcomes, n_bins)

        return CalibrationMetrics(
            brier_score=avg_brier,
            expected_calibration_error=ece,
            max_calibration_error=mce,
            reliability_data=reliability_data,
            n_samples=n_samples,
        )

    def _calculate_ece(
        self,
        predicted_probs: np.ndarray,
        true_outcomes: np.ndarray,
        n_bins: int = 10,
    ) -> float:
        """
        Calculate Expected Calibration Error.

        ECE = sum(|accuracy(bin) - confidence(bin)| * n(bin) / N)
        """
        ece_total = 0.0
        n_total = len(true_outcomes)

        for class_idx in range(3):
            y_binary = (true_outcomes == class_idx).astype(float)
            probs = predicted_probs[:, class_idx]

            # Bin by predicted probability
            bin_boundaries = np.linspace(0, 1, n_bins + 1)

            for i in range(n_bins):
                in_bin = (probs >= bin_boundaries[i]) & (probs < bin_boundaries[i + 1])
                n_in_bin = np.sum(in_bin)

                if n_in_bin > 0:
                    accuracy = np.mean(y_binary[in_bin])
                    confidence = np.mean(probs[in_bin])
                    ece_total += np.abs(accuracy - confidence) * n_in_bin

        # Average over classes and normalize
        ece = ece_total / (n_total * 3)
        return float(ece)

    def _calculate_mce(
        self,
        predicted_probs: np.ndarray,
        true_outcomes: np.ndarray,
        n_bins: int = 10,
    ) -> float:
        """Calculate Maximum Calibration Error."""
        max_error = 0.0

        for class_idx in range(3):
            y_binary = (true_outcomes == class_idx).astype(float)
            probs = predicted_probs[:, class_idx]

            bin_boundaries = np.linspace(0, 1, n_bins + 1)

            for i in range(n_bins):
                in_bin = (probs >= bin_boundaries[i]) & (probs < bin_boundaries[i + 1])
                n_in_bin = np.sum(in_bin)

                if n_in_bin > 0:
                    accuracy = np.mean(y_binary[in_bin])
                    confidence = np.mean(probs[in_bin])
                    error = np.abs(accuracy - confidence)
                    max_error = max(max_error, error)

        return float(max_error)

    def evaluate(
        self,
        predicted_probs: np.ndarray,
        true_outcomes: np.ndarray,
    ) -> tuple[CalibrationMetrics, CalibrationMetrics]:
        """
        Evaluate calibration improvement.

        Args:
            predicted_probs: Original predicted probabilities (N, 3)
            true_outcomes: Actual outcomes (N,)

        Returns:
            Tuple of (before_metrics, after_metrics)
        """
        before = self._calculate_metrics(predicted_probs, true_outcomes)

        if self.is_fitted:
            calibrated_probs = self.calibrate_batch(predicted_probs)
            after = self._calculate_metrics(calibrated_probs, true_outcomes)
        else:
            after = before

        return before, after

    def get_training_metrics(self) -> CalibrationMetrics | None:
        """Get metrics from training data."""
        return self._training_metrics


def calculate_brier_score(
    predicted_probs: np.ndarray,
    true_outcomes: np.ndarray,
) -> float:
    """
    Calculate Brier score for multi-class predictions.

    Args:
        predicted_probs: Array of shape (N, 3) with probabilities
        true_outcomes: Array of shape (N,) with outcomes (0, 1, or 2)

    Returns:
        Average Brier score (lower is better, 0 = perfect)
    """
    n_samples = len(true_outcomes)
    brier = 0.0

    for i in range(n_samples):
        true_class = int(true_outcomes[i])
        for j in range(3):
            target = 1.0 if j == true_class else 0.0
            brier += (predicted_probs[i, j] - target) ** 2

    return brier / (n_samples * 3)


def create_reliability_diagram_data(
    predicted_probs: np.ndarray,
    true_outcomes: np.ndarray,
    n_bins: int = 10,
) -> dict:
    """
    Create data for reliability diagram visualization.

    Returns dict with bin centers, observed frequencies, and sample counts
    for each outcome class.
    """
    outcome_names = ["home_win", "draw", "away_win"]
    result = {}

    for class_idx, name in enumerate(outcome_names):
        y_binary = (true_outcomes == class_idx).astype(float)
        probs = predicted_probs[:, class_idx]

        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_centers = []
        observed_freq = []
        counts = []

        for i in range(n_bins):
            in_bin = (probs >= bin_boundaries[i]) & (probs < bin_boundaries[i + 1])
            n_in_bin = np.sum(in_bin)

            if n_in_bin > 0:
                bin_centers.append((bin_boundaries[i] + bin_boundaries[i + 1]) / 2)
                observed_freq.append(float(np.mean(y_binary[in_bin])))
                counts.append(int(n_in_bin))

        result[name] = {
            "bin_centers": bin_centers,
            "observed_frequency": observed_freq,
            "counts": counts,
        }

    return result
