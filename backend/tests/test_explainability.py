"""Tests for prediction explainability module."""

import numpy as np
import pytest

from src.prediction_engine.explainability import (
    FeatureContribution,
    PredictionExplainer,
    PredictionExplanation,
    explain_prediction,
)


class TestFeatureContribution:
    """Test FeatureContribution dataclass."""

    def test_feature_contribution_creation(self):
        """Test creating a feature contribution."""
        contrib = FeatureContribution(
            feature="home_attack",
            contribution=0.15,
            value=1.5,
            importance_rank=1,
        )

        assert contrib.feature == "home_attack"
        assert contrib.contribution == 0.15
        assert contrib.value == 1.5
        assert contrib.importance_rank == 1


class TestPredictionExplanation:
    """Test PredictionExplanation dataclass."""

    def test_explanation_creation(self):
        """Test creating a prediction explanation."""
        explanations = [
            FeatureContribution("home_attack", 0.15, 1.5, 1),
            FeatureContribution("away_defense", 0.08, 1.2, 2),
            FeatureContribution("recent_form_home", -0.05, 60.0, 3),
        ]

        exp = PredictionExplanation(
            predicted_outcome="home_win",
            confidence=0.72,
            explanations=explanations,
            method="xgboost_native",
        )

        assert exp.predicted_outcome == "home_win"
        assert exp.confidence == 0.72
        assert len(exp.explanations) == 3
        assert exp.method == "xgboost_native"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        explanations = [
            FeatureContribution("home_attack", 0.1523, 1.5, 1),
            FeatureContribution("away_defense", 0.0812, 1.2, 2),
        ]

        exp = PredictionExplanation(
            predicted_outcome="home_win",
            confidence=0.72,
            explanations=explanations,
            method="xgboost_native",
        )

        result = exp.to_dict()

        assert result["prediction"] == "Home Win"
        assert result["confidence"] == 0.72
        assert len(result["explanations"]) == 2
        assert result["explanations"][0]["feature"] == "home_attack"
        assert result["explanations"][0]["contribution"] == 0.1523
        assert result["method"] == "xgboost_native"

    def test_top_features(self):
        """Test getting top contributing features."""
        explanations = [
            FeatureContribution("home_attack", 0.15, 1.5, 1),
            FeatureContribution("away_defense", -0.20, 1.2, 2),  # Largest abs
            FeatureContribution("recent_form_home", 0.05, 60.0, 3),
            FeatureContribution("head_to_head_home", 0.10, 0.2, 4),
        ]

        exp = PredictionExplanation(
            predicted_outcome="home_win",
            confidence=0.72,
            explanations=explanations,
        )

        top = exp.top_features(2)

        assert len(top) == 2
        # Sorted by absolute contribution
        assert abs(top[0].contribution) >= abs(top[1].contribution)


class TestPredictionExplainer:
    """Test PredictionExplainer class."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained XGBoost model."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        # Generate training data
        np.random.seed(42)
        n_samples = 300
        X_train = np.random.rand(n_samples, 7)
        y_train = np.random.choice([0, 1, 2], n_samples)

        X_val = np.random.rand(50, 7)
        y_val = np.random.choice([0, 1, 2], 50)

        model.train(X_train, y_train, X_val, y_val)

        return model

    def test_explainer_initialization(self, trained_model):
        """Test explainer can be initialized with model."""
        explainer = PredictionExplainer(trained_model.model)

        assert explainer.model is not None
        assert len(explainer.FEATURE_NAMES) == 7

    def test_explainer_without_model(self):
        """Test explainer handles None model gracefully."""
        explainer = PredictionExplainer(None)

        explanation = explainer.explain(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
        )

        assert explanation.method == "fallback"
        assert explanation.confidence == 0.33

    def test_explain_single_prediction(self, trained_model):
        """Test explaining a single prediction."""
        explainer = PredictionExplainer(trained_model.model)

        explanation = explainer.explain(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            recent_form_home=65.0,
            recent_form_away=55.0,
            head_to_head_home=0.2,
        )

        assert explanation.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= explanation.confidence <= 1
        assert len(explanation.explanations) == 7
        assert explanation.method == "xgboost_native"

    def test_explain_batch(self, trained_model):
        """Test explaining batch predictions."""
        explainer = PredictionExplainer(trained_model.model)

        features = np.array(
            [
                [1.5, 1.2, 1.3, 1.1, 65.0, 55.0, 0.2],
                [1.2, 1.4, 1.6, 1.0, 45.0, 70.0, -0.1],
                [1.8, 1.1, 1.1, 1.3, 80.0, 40.0, 0.5],
            ]
        )

        explanations = explainer.explain_batch(features)

        assert len(explanations) == 3
        for exp in explanations:
            assert exp.predicted_outcome in ["home_win", "draw", "away_win"]
            assert len(exp.explanations) == 7

    def test_contributions_are_ranked(self, trained_model):
        """Test that contributions are properly ranked."""
        explainer = PredictionExplainer(trained_model.model)

        explanation = explainer.explain(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
        )

        # Check ranks are assigned 1-7
        ranks = [e.importance_rank for e in explanation.explanations]
        assert set(ranks) == {1, 2, 3, 4, 5, 6, 7}

    def test_get_global_importance(self, trained_model):
        """Test getting global feature importance."""
        explainer = PredictionExplainer(trained_model.model)

        importance = explainer.get_global_importance()

        assert len(importance) == 7
        # Should sum to approximately 1
        assert sum(importance.values()) == pytest.approx(1.0, abs=0.01)

    def test_get_feature_label(self, trained_model):
        """Test getting human-readable feature labels."""
        explainer = PredictionExplainer(trained_model.model)

        label = explainer.get_feature_label("home_attack")
        assert label == "Home Attack Strength"

        label = explainer.get_feature_label("unknown_feature")
        assert label == "unknown_feature"


class TestExplainPredictionFunction:
    """Test the convenience function."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained XGBoost model."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        np.random.seed(42)
        X_train = np.random.rand(200, 7)
        y_train = np.random.choice([0, 1, 2], 200)

        X_val = np.random.rand(50, 7)
        y_val = np.random.choice([0, 1, 2], 50)

        model.train(X_train, y_train, X_val, y_val)

        return model

    def test_explain_prediction_returns_dict(self, trained_model):
        """Test that explain_prediction returns API-ready dict."""
        result = explain_prediction(
            trained_model.model,
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            recent_form_home=60.0,
            recent_form_away=50.0,
            head_to_head_home=0.1,
        )

        assert isinstance(result, dict)
        assert "prediction" in result
        assert "confidence" in result
        assert "explanations" in result
        assert "method" in result

        assert result["prediction"] in ["Home Win", "Draw", "Away Win"]
        assert isinstance(result["explanations"], list)


class TestXGBoostModelExplainability:
    """Test XGBoostModel explainability integration."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained XGBoost model."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        np.random.seed(42)
        X_train = np.random.rand(300, 7)
        y_train = np.random.choice([0, 1, 2], 300)

        X_val = np.random.rand(50, 7)
        y_val = np.random.choice([0, 1, 2], 50)

        model.train(X_train, y_train, X_val, y_val)

        return model

    def test_predict_explained(self, trained_model):
        """Test predict_explained method on XGBoostModel."""
        from src.prediction_engine.models.xgboost_model import ExplainedPrediction

        result = trained_model.predict_explained(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            recent_form_home=60.0,
            recent_form_away=50.0,
            head_to_head_home=0.15,
        )

        assert isinstance(result, ExplainedPrediction)
        assert 0 <= result.home_win_prob <= 1
        assert 0 <= result.draw_prob <= 1
        assert 0 <= result.away_win_prob <= 1
        assert result.predicted_outcome in ["home_win", "draw", "away_win"]
        assert len(result.explanations) > 0
        assert result.model_type == "xgboost_explained"

    def test_predict_explained_top_n(self, trained_model):
        """Test predict_explained with custom top_n."""
        result = trained_model.predict_explained(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.1,
            top_n=3,
        )

        assert len(result.explanations) == 3

    def test_get_explainer(self, trained_model):
        """Test get_explainer returns valid explainer."""
        explainer = trained_model.get_explainer()

        assert explainer is not None
        assert hasattr(explainer, "explain")
        assert hasattr(explainer, "explain_batch")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_extreme_feature_values(self):
        """Test with extreme feature values."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        np.random.seed(42)
        X_train = np.random.rand(200, 7)
        y_train = np.random.choice([0, 1, 2], 200)

        model.train(X_train, y_train)
        explainer = PredictionExplainer(model.model)

        # Extreme values
        explanation = explainer.explain(
            home_attack=10.0,  # Very high
            home_defense=0.1,  # Very low
            away_attack=0.1,
            away_defense=10.0,
            recent_form_home=100.0,
            recent_form_away=0.0,
            head_to_head_home=1.0,
        )

        # Should still produce valid output
        assert explanation.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= explanation.confidence <= 1

    def test_uniform_features(self):
        """Test with all features equal."""
        from src.prediction_engine.models.xgboost_model import XGBoostModel

        model = XGBoostModel()

        np.random.seed(42)
        X_train = np.random.rand(200, 7)
        y_train = np.random.choice([0, 1, 2], 200)

        model.train(X_train, y_train)
        explainer = PredictionExplainer(model.model)

        # All features = 1.0
        explanation = explainer.explain(
            home_attack=1.0,
            home_defense=1.0,
            away_attack=1.0,
            away_defense=1.0,
            recent_form_home=50.0,
            recent_form_away=50.0,
            head_to_head_home=0.0,
        )

        assert explanation.predicted_outcome in ["home_win", "draw", "away_win"]
        assert len(explanation.explanations) == 7
