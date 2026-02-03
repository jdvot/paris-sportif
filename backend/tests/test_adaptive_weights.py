"""Tests for adaptive ensemble weights module."""

from datetime import datetime, timedelta

import numpy as np
import pytest

from src.prediction_engine.adaptive_weights import (
    AdaptiveWeightCalculator,
    AdaptiveWeights,
    ModelPerformanceMetrics,
    ModelPredictionRecord,
)


class TestModelPredictionRecord:
    """Test ModelPredictionRecord dataclass."""

    def test_correct_prediction(self):
        """Test that was_correct is True when prediction matches outcome."""
        record = ModelPredictionRecord(
            model_name="poisson",
            match_id=1,
            predicted_outcome="home",
            actual_outcome="home",
            predicted_probs=(0.6, 0.2, 0.2),
            prediction_date=datetime.now(),
        )
        assert record.was_correct is True

    def test_incorrect_prediction(self):
        """Test that was_correct is False when prediction doesn't match."""
        record = ModelPredictionRecord(
            model_name="elo",
            match_id=2,
            predicted_outcome="home",
            actual_outcome="away",
            predicted_probs=(0.5, 0.3, 0.2),
            prediction_date=datetime.now(),
        )
        assert record.was_correct is False


class TestAdaptiveWeightCalculator:
    """Test AdaptiveWeightCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a fresh calculator for each test."""
        return AdaptiveWeightCalculator(
            rolling_window_days=30,
            temperature=0.5,
            min_weight=0.05,
        )

    def test_initialization(self, calculator):
        """Test calculator initializes with correct parameters."""
        assert calculator.rolling_window_days == 30
        assert calculator.temperature == 0.5
        assert calculator.min_weight == 0.05

    def test_record_prediction(self, calculator):
        """Test recording a single prediction."""
        calculator.record_prediction(
            model_name="poisson",
            match_id=1,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
        )

        records = calculator._get_records_in_window("poisson")
        assert len(records) == 1
        assert records[0].model_name == "poisson"
        assert records[0].was_correct is True

    def test_record_batch(self, calculator):
        """Test recording multiple predictions at once."""
        records = [
            {
                "model_name": "poisson",
                "match_id": 1,
                "predicted_probs": [0.6, 0.2, 0.2],
                "actual_outcome": "home",
            },
            {
                "model_name": "elo",
                "match_id": 1,
                "predicted_probs": [0.5, 0.3, 0.2],
                "actual_outcome": "home",
            },
        ]

        count = calculator.record_batch(records)
        assert count == 2

    def test_calculate_model_metrics(self, calculator):
        """Test calculating metrics for a model with sufficient data."""
        # Add enough predictions for valid metrics
        for i in range(20):
            calculator.record_prediction(
                model_name="poisson",
                match_id=i,
                predicted_probs=(0.6, 0.2, 0.2),
                actual_outcome="home" if i < 15 else "away",  # 75% accuracy
            )

        metrics = calculator.calculate_model_metrics("poisson")

        assert metrics is not None
        assert metrics.model_name == "poisson"
        assert metrics.n_predictions == 20
        assert metrics.accuracy == pytest.approx(0.75, abs=0.01)
        assert metrics.is_valid is True

    def test_calculate_model_metrics_insufficient_data(self, calculator):
        """Test that metrics return None with too few predictions."""
        calculator.record_prediction(
            model_name="poisson",
            match_id=1,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
        )

        metrics = calculator.calculate_model_metrics("poisson")
        assert metrics is None

    def test_calculate_weights_no_data(self, calculator):
        """Test weights calculation with no performance data."""
        weights = calculator.calculate_weights()

        assert weights.method == "default"
        assert "poisson" in weights.weights
        assert weights.weights["poisson"] == 0.25  # Default weight

    def test_calculate_weights_with_data(self, calculator):
        """Test weights calculation with performance data."""
        # Add data for multiple models with different accuracies
        np.random.seed(42)

        # Poisson: ~80% accuracy
        for i in range(30):
            correct = i < 24
            calculator.record_prediction(
                model_name="poisson",
                match_id=i,
                predicted_probs=(0.6, 0.2, 0.2),
                actual_outcome="home" if correct else "away",
            )

        # ELO: ~60% accuracy
        for i in range(30):
            correct = i < 18
            calculator.record_prediction(
                model_name="elo",
                match_id=i + 100,
                predicted_probs=(0.5, 0.3, 0.2),
                actual_outcome="home" if correct else "draw",
            )

        weights = calculator.calculate_weights()

        assert weights.method == "softmax_accuracy"
        assert "poisson" in weights.weights
        assert "elo" in weights.weights
        # Higher accuracy should mean higher weight
        assert weights.weights["poisson"] > weights.weights["elo"]

    def test_min_weight_constraint(self, calculator):
        """Test that minimum weight constraint is applied."""
        # Add data where one model is much better
        for i in range(30):
            calculator.record_prediction(
                model_name="poisson",
                match_id=i,
                predicted_probs=(0.9, 0.05, 0.05),
                actual_outcome="home",  # 100% accuracy
            )
            calculator.record_prediction(
                model_name="elo",
                match_id=i + 100,
                predicted_probs=(0.1, 0.1, 0.8),
                actual_outcome="home",  # 0% accuracy for home
            )

        weights = calculator.calculate_weights()

        # Even the worst model should have min_weight
        assert weights.weights["elo"] >= calculator.min_weight

    def test_softmax_temperature_effect(self):
        """Test that temperature affects weight distribution."""
        # Low temperature = more extreme weights
        calc_low_temp = AdaptiveWeightCalculator(temperature=0.1)
        # High temperature = more uniform weights
        calc_high_temp = AdaptiveWeightCalculator(temperature=2.0)

        # Same data for both
        for calc in [calc_low_temp, calc_high_temp]:
            for i in range(30):
                calc.record_prediction(
                    model_name="poisson",
                    match_id=i,
                    predicted_probs=(0.6, 0.2, 0.2),
                    actual_outcome="home" if i < 24 else "away",  # 80%
                )
                calc.record_prediction(
                    model_name="elo",
                    match_id=i + 100,
                    predicted_probs=(0.5, 0.3, 0.2),
                    actual_outcome="home" if i < 18 else "draw",  # 60%
                )

        weights_low = calc_low_temp.calculate_weights()
        weights_high = calc_high_temp.calculate_weights()

        # Low temperature should have bigger difference between weights
        diff_low = abs(weights_low.weights["poisson"] - weights_low.weights["elo"])
        diff_high = abs(weights_high.weights["poisson"] - weights_high.weights["elo"])

        assert diff_low > diff_high

    def test_rolling_window(self, calculator):
        """Test that old records are excluded from calculations."""
        # Add old record (outside window)
        old_date = datetime.now() - timedelta(days=60)
        calculator.record_prediction(
            model_name="poisson",
            match_id=1,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
            prediction_date=old_date,
        )

        records = calculator._get_records_in_window("poisson")
        assert len(records) == 0  # Old record should be excluded

    def test_clear_old_records(self, calculator):
        """Test clearing old records."""
        # Add old and new records
        old_date = datetime.now() - timedelta(days=60)
        calculator.record_prediction(
            model_name="poisson",
            match_id=1,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
            prediction_date=old_date,
        )
        calculator.record_prediction(
            model_name="poisson",
            match_id=2,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
        )

        removed = calculator.clear_old_records(days_to_keep=30)

        assert removed == 1
        assert len(calculator._records) == 1

    def test_export_import_records(self, calculator):
        """Test exporting and importing records."""
        calculator.record_prediction(
            model_name="poisson",
            match_id=1,
            predicted_probs=(0.6, 0.2, 0.2),
            actual_outcome="home",
        )

        # Export
        exported = calculator.export_records()
        assert len(exported) == 1
        assert exported[0]["model_name"] == "poisson"

        # Import into new calculator
        new_calc = AdaptiveWeightCalculator()
        count = new_calc.import_records(exported)

        assert count == 1
        assert len(new_calc._records) == 1

    def test_get_weight(self, calculator):
        """Test getting weight for a specific model."""
        # Without data, should return default
        weight = calculator.get_weight("poisson")
        assert weight == 0.25  # Default weight

    def test_cache_invalidation(self, calculator):
        """Test that cache is invalidated when new predictions are added."""
        # Add initial data
        for i in range(20):
            calculator.record_prediction(
                model_name="poisson",
                match_id=i,
                predicted_probs=(0.6, 0.2, 0.2),
                actual_outcome="home",
            )

        # Calculate weights (should cache)
        weights1 = calculator.calculate_weights()

        # Add more data (should invalidate cache)
        for i in range(10):
            calculator.record_prediction(
                model_name="poisson",
                match_id=i + 100,
                predicted_probs=(0.6, 0.2, 0.2),
                actual_outcome="away",  # Wrong predictions
            )

        # New calculation should reflect new data
        weights2 = calculator.calculate_weights()

        # Accuracy should be lower now
        assert weights2.metrics["poisson"].accuracy < weights1.metrics["poisson"].accuracy


class TestAdaptiveWeights:
    """Test AdaptiveWeights dataclass."""

    def test_get_weight(self):
        """Test getting weight for a model."""
        weights = AdaptiveWeights(
            weights={"poisson": 0.3, "elo": 0.2},
            calculated_at=datetime.now(),
            period_days=30,
        )

        assert weights.get_weight("poisson") == 0.3
        assert weights.get_weight("unknown") == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        weights = AdaptiveWeights(
            weights={"poisson": 0.3, "elo": 0.2},
            calculated_at=datetime.now(),
            period_days=30,
            method="softmax_accuracy",
        )

        result = weights.to_dict()

        assert "weights" in result
        assert "calculated_at" in result
        assert result["method"] == "softmax_accuracy"


class TestEnsembleIntegration:
    """Test integration with EnsemblePredictor."""

    def test_ensemble_with_adaptive_weights(self):
        """Test EnsemblePredictor uses adaptive weights when enabled."""
        from src.prediction_engine.ensemble import EnsemblePredictor

        # Create predictor with adaptive weights enabled
        predictor = EnsemblePredictor(use_adaptive_weights=True)

        # Add performance data
        for i in range(30):
            predictor.record_prediction_outcome(
                match_id=i,
                actual_outcome="home",
                model_predictions={
                    "poisson": (0.6, 0.2, 0.2),
                    "elo": (0.5, 0.3, 0.2),
                },
            )

        # Get adaptive weights
        weights = predictor.get_adaptive_weights()

        assert weights is not None
        assert "poisson" in weights.weights

    def test_ensemble_disable_adaptive_weights(self):
        """Test disabling adaptive weights."""
        from src.prediction_engine.ensemble import EnsemblePredictor

        predictor = EnsemblePredictor(use_adaptive_weights=True)
        predictor.enable_adaptive_weights(False)

        assert predictor.use_adaptive_weights is False

    def test_ensemble_prediction_uses_weights(self):
        """Test that predictions use the correct weights."""
        from src.prediction_engine.ensemble import EnsemblePredictor

        # Create predictor with adaptive weights disabled (uses defaults)
        predictor = EnsemblePredictor(use_adaptive_weights=False)

        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            home_elo=1500,
            away_elo=1450,
        )

        # Check that contributions have correct default weights
        assert prediction.poisson_contribution.weight == 0.25
        assert prediction.elo_contribution.weight == 0.15
