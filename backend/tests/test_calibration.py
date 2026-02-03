"""Tests for probability calibration module."""

import numpy as np
import pytest

from src.prediction_engine.calibration import (
    CalibrationMetrics,
    ProbabilityCalibrator,
    calculate_brier_score,
    create_reliability_diagram_data,
)


class TestBrierScore:
    """Test Brier score calculation."""

    def test_perfect_predictions(self):
        """Perfect predictions should have Brier score of 0."""
        # Predict exactly what happened
        predicted = np.array([
            [1.0, 0.0, 0.0],  # Predict home win
            [0.0, 1.0, 0.0],  # Predict draw
            [0.0, 0.0, 1.0],  # Predict away win
        ])
        actual = np.array([0, 1, 2])  # Home, draw, away

        brier = calculate_brier_score(predicted, actual)
        assert brier == pytest.approx(0.0, abs=1e-6)

    def test_uniform_predictions(self):
        """Uniform predictions should have Brier score of ~0.222."""
        predicted = np.array([
            [1/3, 1/3, 1/3],
            [1/3, 1/3, 1/3],
            [1/3, 1/3, 1/3],
        ])
        actual = np.array([0, 1, 2])

        brier = calculate_brier_score(predicted, actual)
        # Expected: (2/9 + 2/9 + 2/9) / 3 = 2/9 ≈ 0.222
        assert brier == pytest.approx(2/9, abs=0.01)

    def test_wrong_predictions(self):
        """Completely wrong predictions should have high Brier score."""
        predicted = np.array([
            [0.0, 0.0, 1.0],  # Predict away, actual home
            [1.0, 0.0, 0.0],  # Predict home, actual draw
            [0.0, 1.0, 0.0],  # Predict draw, actual away
        ])
        actual = np.array([0, 1, 2])

        brier = calculate_brier_score(predicted, actual)
        # Should be higher than uniform
        assert brier > 0.5


class TestProbabilityCalibrator:
    """Test ProbabilityCalibrator class."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample prediction data."""
        np.random.seed(42)
        n_samples = 200

        # Generate overconfident predictions (common issue)
        # The model predicts more extreme probabilities than reality
        probs = np.random.dirichlet([2, 1, 1], n_samples)

        # Add some bias - make predictions overconfident
        probs = np.power(probs, 0.7)  # Flatten probabilities
        probs = probs / probs.sum(axis=1, keepdims=True)

        # Generate outcomes based on slightly different distribution
        outcomes = np.random.choice([0, 1, 2], n_samples, p=[0.4, 0.3, 0.3])

        return probs, outcomes

    def test_calibrator_initialization(self):
        """Test calibrator can be initialized."""
        cal = ProbabilityCalibrator(method="platt")
        assert cal.method == "platt"
        assert not cal.is_fitted

        cal = ProbabilityCalibrator(method="isotonic")
        assert cal.method == "isotonic"
        assert not cal.is_fitted

    def test_calibrator_fit_platt(self, sample_data):
        """Test Platt scaling calibration."""
        probs, outcomes = sample_data
        cal = ProbabilityCalibrator(method="platt")

        metrics = cal.fit(probs, outcomes)

        assert cal.is_fitted
        assert isinstance(metrics, CalibrationMetrics)
        assert metrics.brier_score >= 0
        assert metrics.expected_calibration_error >= 0
        assert metrics.n_samples == len(outcomes)

    def test_calibrator_fit_isotonic(self, sample_data):
        """Test isotonic regression calibration."""
        probs, outcomes = sample_data
        cal = ProbabilityCalibrator(method="isotonic")

        metrics = cal.fit(probs, outcomes)

        assert cal.is_fitted
        assert isinstance(metrics, CalibrationMetrics)
        assert metrics.brier_score >= 0

    def test_calibrate_single_prediction(self, sample_data):
        """Test calibrating a single prediction."""
        probs, outcomes = sample_data
        cal = ProbabilityCalibrator(method="isotonic")
        cal.fit(probs, outcomes)

        result = cal.calibrate(0.6, 0.25, 0.15)

        assert result.calibration_method == "isotonic"
        assert 0 <= result.home_win_prob <= 1
        assert 0 <= result.draw_prob <= 1
        assert 0 <= result.away_win_prob <= 1
        # Probabilities should sum to 1
        total = result.home_win_prob + result.draw_prob + result.away_win_prob
        assert total == pytest.approx(1.0, abs=0.01)

    def test_calibrate_batch(self, sample_data):
        """Test batch calibration."""
        probs, outcomes = sample_data
        cal = ProbabilityCalibrator(method="isotonic")
        cal.fit(probs, outcomes)

        # Calibrate a subset
        test_probs = probs[:10]
        calibrated = cal.calibrate_batch(test_probs)

        assert calibrated.shape == test_probs.shape
        # All values should be valid probabilities
        assert np.all(calibrated >= 0)
        assert np.all(calibrated <= 1)
        # Each row should sum to 1
        row_sums = calibrated.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=0.01)

    def test_uncalibrated_passthrough(self):
        """Test that uncalibrated returns original values."""
        cal = ProbabilityCalibrator(method="isotonic")
        # Don't fit

        result = cal.calibrate(0.6, 0.25, 0.15)

        assert result.calibration_method == "none"
        assert result.home_win_prob == 0.6
        assert result.draw_prob == 0.25
        assert result.away_win_prob == 0.15

    def test_evaluate_improvement(self, sample_data):
        """Test calibration evaluation."""
        probs, outcomes = sample_data
        cal = ProbabilityCalibrator(method="isotonic")
        cal.fit(probs, outcomes)

        before, after = cal.evaluate(probs, outcomes)

        assert isinstance(before, CalibrationMetrics)
        assert isinstance(after, CalibrationMetrics)
        # After calibration, ECE should generally improve
        # (not always guaranteed but usually)
        assert after.expected_calibration_error <= before.expected_calibration_error + 0.1


class TestReliabilityDiagram:
    """Test reliability diagram data generation."""

    def test_reliability_diagram_structure(self):
        """Test reliability diagram data structure."""
        np.random.seed(42)
        probs = np.random.dirichlet([1, 1, 1], 100)
        outcomes = np.random.choice([0, 1, 2], 100)

        data = create_reliability_diagram_data(probs, outcomes, n_bins=5)

        assert "home_win" in data
        assert "draw" in data
        assert "away_win" in data

        for outcome in ["home_win", "draw", "away_win"]:
            assert "bin_centers" in data[outcome]
            assert "observed_frequency" in data[outcome]
            assert "counts" in data[outcome]

    def test_reliability_diagram_values(self):
        """Test reliability diagram values are valid."""
        np.random.seed(42)
        probs = np.random.dirichlet([1, 1, 1], 100)
        outcomes = np.random.choice([0, 1, 2], 100)

        data = create_reliability_diagram_data(probs, outcomes, n_bins=5)

        for outcome in ["home_win", "draw", "away_win"]:
            # Bin centers should be between 0 and 1
            for center in data[outcome]["bin_centers"]:
                assert 0 <= center <= 1

            # Observed frequencies should be between 0 and 1
            for freq in data[outcome]["observed_frequency"]:
                assert 0 <= freq <= 1

            # Counts should be positive
            for count in data[outcome]["counts"]:
                assert count > 0


class TestCalibrationMetrics:
    """Test calibration metrics calculation."""

    def test_metrics_dataclass(self):
        """Test CalibrationMetrics dataclass."""
        metrics = CalibrationMetrics(
            brier_score=0.2,
            expected_calibration_error=0.05,
            max_calibration_error=0.15,
            reliability_data={},
            n_samples=100,
        )

        assert metrics.brier_score == 0.2
        assert metrics.expected_calibration_error == 0.05
        assert metrics.max_calibration_error == 0.15
        assert metrics.n_samples == 100


class TestXGBoostCalibration:
    """Test XGBoost model calibration integration."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained XGBoost model."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        # Generate training data
        np.random.seed(42)
        n_samples = 500
        X_train = np.random.rand(n_samples, 7)
        # Generate labels based on features
        y_train = np.random.choice([0, 1, 2], n_samples)

        X_val = np.random.rand(100, 7)
        y_val = np.random.choice([0, 1, 2], 100)

        model.train(X_train, y_train, X_val, y_val)

        return model, X_val, y_val

    def test_xgboost_calibration_fit(self, trained_model):
        """Test fitting calibration on XGBoost model."""
        model, X_val, y_val = trained_model

        metrics = model.fit_calibration(X_val, y_val, method="isotonic")

        assert model.is_calibrated
        assert "brier_before" in metrics
        assert "brier_after" in metrics
        assert "ece_before" in metrics
        assert "ece_after" in metrics

    def test_xgboost_calibrated_prediction(self, trained_model):
        """Test calibrated prediction from XGBoost."""
        model, X_val, y_val = trained_model
        model.fit_calibration(X_val, y_val, method="isotonic")

        pred = model.predict_calibrated(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            recent_form_home=60.0,
            recent_form_away=50.0,
            head_to_head_home=0.2,
        )

        assert pred.model_type == "xgboost_calibrated"
        assert 0 <= pred.home_win_prob <= 1
        assert 0 <= pred.draw_prob <= 1
        assert 0 <= pred.away_win_prob <= 1

        # Should sum to ~1
        total = pred.home_win_prob + pred.draw_prob + pred.away_win_prob
        assert total == pytest.approx(1.0, abs=0.05)

    def test_xgboost_batch_calibration(self, trained_model):
        """Test batch calibration from XGBoost."""
        model, X_val, y_val = trained_model
        model.fit_calibration(X_val, y_val, method="platt")

        probs = model.predict_batch_calibrated(X_val)

        assert probs.shape == (len(X_val), 3)
        assert np.all(probs >= 0)
        assert np.all(probs <= 1)
        # Rows should sum to ~1
        row_sums = probs.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=0.05)
