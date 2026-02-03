"""Unit tests for ML prediction models.

Tests cover:
- Poisson model: Goal distribution predictions
- ELO model: Rating-based predictions
- XGBoost model: ML-based predictions
- Ensemble predictor: Model combination
- LLM adjustments: Pydantic validation

Run with: cd backend && uv run pytest tests/test_models.py -v
"""

import numpy as np
import pytest

from src.prediction_engine.models.poisson import PoissonModel, PoissonPrediction
from src.prediction_engine.models.elo import ELOSystem, ELOPrediction
from src.prediction_engine.models.xgboost_model import XGBoostModel, XGBoostPrediction
from src.prediction_engine.ensemble import (
    EnsemblePredictor,
    EnsemblePrediction,
    LLMAdjustments,
)
from src.llm.adjustments import (
    InjuryAnalysis,
    SentimentAnalysis,
    FormAnalysis,
    FormAssessment,
    validate_injury_analysis,
    validate_sentiment_analysis,
    validate_form_analysis,
)


# =============================================================================
# Poisson Model Tests
# =============================================================================


class TestPoissonModel:
    """Test cases for Poisson distribution model."""

    @pytest.fixture
    def model(self) -> PoissonModel:
        """Create a default Poisson model."""
        return PoissonModel()

    def test_initialization_defaults(self, model: PoissonModel):
        """Test default initialization values."""
        assert model.league_avg_goals == 2.75
        assert model.home_advantage == 1.15
        assert model.MAX_GOALS == 8

    def test_initialization_custom(self):
        """Test custom initialization values."""
        model = PoissonModel(league_avg_goals=3.0, home_advantage_factor=1.2)
        assert model.league_avg_goals == 3.0
        assert model.home_advantage == 1.2

    def test_expected_goals_calculation(self, model: PoissonModel):
        """Test expected goals calculation."""
        # Balanced teams
        exp_home, exp_away = model.calculate_expected_goals(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
        )

        # Home team should have slight advantage
        assert exp_home > 0.3
        assert exp_away > 0.3
        assert exp_home < 5.0
        assert exp_away < 5.0

    def test_expected_goals_clamping(self, model: PoissonModel):
        """Test that expected goals are clamped to valid range."""
        # Extreme values
        exp_home, exp_away = model.calculate_expected_goals(
            home_attack=10.0,
            home_defense=0.1,
            away_attack=0.1,
            away_defense=10.0,
        )

        assert exp_home <= 5.0
        assert exp_away >= 0.3

    def test_predict_returns_valid_probabilities(self, model: PoissonModel):
        """Test that predictions return valid probabilities summing to 1."""
        prediction = model.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
        )

        assert isinstance(prediction, PoissonPrediction)

        # Probabilities sum to 1
        total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        assert abs(total - 1.0) < 0.001

        # All probabilities are valid
        assert 0 <= prediction.home_win_prob <= 1
        assert 0 <= prediction.draw_prob <= 1
        assert 0 <= prediction.away_win_prob <= 1

    def test_predict_strong_home_team(self, model: PoissonModel):
        """Test prediction for strong home team."""
        prediction = model.predict(
            home_attack=2.5,
            home_defense=0.8,
            away_attack=0.8,
            away_defense=2.0,
        )

        # Strong home team should be favored
        assert prediction.home_win_prob > prediction.away_win_prob

    def test_predict_strong_away_team(self, model: PoissonModel):
        """Test prediction for strong away team."""
        prediction = model.predict(
            home_attack=0.8,
            home_defense=2.0,
            away_attack=2.5,
            away_defense=0.8,
        )

        # Strong away team should be favored (but home advantage may reduce gap)
        assert prediction.away_win_prob > 0.25

    def test_predict_expected_goals(self, model: PoissonModel):
        """Test that expected goals are reasonable."""
        prediction = model.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
        )

        assert prediction.expected_home_goals > 0
        assert prediction.expected_away_goals > 0
        assert prediction.expected_home_goals < 5
        assert prediction.expected_away_goals < 5

    def test_predict_most_likely_score(self, model: PoissonModel):
        """Test most likely score is a valid tuple."""
        prediction = model.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
        )

        assert isinstance(prediction.most_likely_score, tuple)
        assert len(prediction.most_likely_score) == 2
        assert prediction.most_likely_score[0] >= 0
        assert prediction.most_likely_score[1] >= 0

    def test_predict_with_xg(self, model: PoissonModel):
        """Test xG-based prediction."""
        prediction = model.predict_with_xg(
            home_xg_for=1.8,
            home_xg_against=1.0,
            away_xg_for=1.2,
            away_xg_against=1.5,
        )

        assert isinstance(prediction, PoissonPrediction)
        total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        assert abs(total - 1.0) < 0.001

    def test_over_under_probability(self, model: PoissonModel):
        """Test over/under probability calculation."""
        over_prob, under_prob = model.over_under_probability(
            expected_home=1.5,
            expected_away=1.3,
            line=2.5,
        )

        assert 0 <= over_prob <= 1
        assert 0 <= under_prob <= 1
        assert abs(over_prob + under_prob - 1.0) < 0.001

    def test_btts_probability(self, model: PoissonModel):
        """Test both teams to score probability."""
        btts_prob = model.btts_probability(
            expected_home=1.5,
            expected_away=1.3,
        )

        assert 0 <= btts_prob <= 1


# =============================================================================
# ELO Model Tests
# =============================================================================


class TestELOSystem:
    """Test cases for ELO rating system."""

    @pytest.fixture
    def system(self) -> ELOSystem:
        """Create a default ELO system."""
        return ELOSystem()

    def test_initialization_defaults(self, system: ELOSystem):
        """Test default initialization values."""
        assert system.k_factor == 20.0
        assert system.home_advantage == 100.0
        assert system.draw_factor == 0.4
        assert ELOSystem.INITIAL_RATING == 1500.0

    def test_initialization_custom(self):
        """Test custom initialization values."""
        system = ELOSystem(k_factor=32.0, home_advantage=80.0, draw_factor=0.35)
        assert system.k_factor == 32.0
        assert system.home_advantage == 80.0
        assert system.draw_factor == 0.35

    def test_expected_score_equal_ratings(self, system: ELOSystem):
        """Test expected score for equal ratings."""
        # Equal ratings, home advantage applies
        exp_score = system.expected_score(1500, 1500, is_a_home=True)

        # Home team should have slight advantage
        assert exp_score > 0.5

    def test_expected_score_higher_rating(self, system: ELOSystem):
        """Test expected score for higher-rated team."""
        # Much higher rated team A
        exp_score = system.expected_score(1800, 1500, is_a_home=False)

        # Higher rated team should be favored even away
        assert exp_score > 0.5

    def test_expected_score_range(self, system: ELOSystem):
        """Test expected score is in valid range."""
        for home_elo in [1200, 1500, 1800]:
            for away_elo in [1200, 1500, 1800]:
                exp_score = system.expected_score(home_elo, away_elo, is_a_home=True)
                assert 0 < exp_score < 1

    def test_calculate_outcome_probabilities(self, system: ELOSystem):
        """Test outcome probability calculation."""
        home_prob, draw_prob, away_prob = system.calculate_outcome_probabilities(1500, 1500)

        # Probabilities sum to 1
        assert abs(home_prob + draw_prob + away_prob - 1.0) < 0.001

        # All probabilities are valid
        assert 0 <= home_prob <= 1
        assert 0 <= draw_prob <= 1
        assert 0 <= away_prob <= 1

        # Draw probability should be reasonable (not too high or low)
        assert 0.08 <= draw_prob <= 0.35

    def test_actual_score(self, system: ELOSystem):
        """Test actual score conversion."""
        assert system.actual_score("home") == (1.0, 0.0)
        assert system.actual_score("away") == (0.0, 1.0)
        assert system.actual_score("draw") == (0.5, 0.5)

    def test_goal_difference_multiplier(self, system: ELOSystem):
        """Test goal difference K-factor multiplier."""
        assert system.goal_difference_multiplier(0) == 1.0
        assert system.goal_difference_multiplier(1) == 1.0
        assert system.goal_difference_multiplier(2) == 1.5
        assert system.goal_difference_multiplier(3) > 1.5
        assert system.goal_difference_multiplier(5) > system.goal_difference_multiplier(3)

    def test_update_ratings_home_win(self, system: ELOSystem):
        """Test rating update after home win."""
        new_home, new_away = system.update_ratings(1500, 1500, 2, 1)

        # Home winner should gain rating
        assert new_home > 1500
        # Away loser should lose rating
        assert new_away < 1500
        # Zero-sum (approximately)
        assert abs((new_home - 1500) + (new_away - 1500)) < 0.1

    def test_update_ratings_draw(self, system: ELOSystem):
        """Test rating update after draw."""
        new_home, new_away = system.update_ratings(1500, 1500, 1, 1)

        # Ratings should change slightly due to home advantage expectation
        # Home was expected to win slightly, so loses a bit on draw
        assert new_home < 1500
        assert new_away > 1500

    def test_predict_returns_valid_prediction(self, system: ELOSystem):
        """Test that predict returns valid ELOPrediction."""
        prediction = system.predict(1500, 1450)

        assert isinstance(prediction, ELOPrediction)

        # Probabilities sum to 1
        total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        assert abs(total - 1.0) < 0.001

        # Expected scores are reasonable
        assert 0.4 <= prediction.expected_home_score <= 3.5
        assert 0.4 <= prediction.expected_away_score <= 3.5


# =============================================================================
# XGBoost Model Tests
# =============================================================================


class TestXGBoostModel:
    """Test cases for XGBoost model."""

    @pytest.fixture
    def model(self) -> XGBoostModel:
        """Create an untrained XGBoost model."""
        return XGBoostModel()

    def test_initialization_untrained(self, model: XGBoostModel):
        """Test untrained model initialization."""
        assert model.model is None
        assert model.is_trained is False
        assert model.feature_importance == {}

    def test_feature_names(self, model: XGBoostModel):
        """Test feature names are defined."""
        assert len(XGBoostModel.FEATURE_NAMES) == 7
        assert "home_attack" in XGBoostModel.FEATURE_NAMES
        assert "recent_form_home" in XGBoostModel.FEATURE_NAMES

    def test_predict_fallback_untrained(self, model: XGBoostModel):
        """Test fallback prediction when model is untrained."""
        prediction = model.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
        )

        assert isinstance(prediction, XGBoostPrediction)

        # Probabilities sum to 1
        total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        assert abs(total - 1.0) < 0.001

        # Fallback has low confidence
        assert prediction.prediction_confidence < 0.7

    def test_fallback_prediction_balanced(self, model: XGBoostModel):
        """Test fallback prediction for balanced teams."""
        prediction = model._fallback_prediction(
            home_attack=1.5,
            home_defense=1.5,
            away_attack=1.5,
            away_defense=1.5,
        )

        # Balanced teams should have similar probabilities
        assert abs(prediction.home_win_prob - prediction.away_win_prob) < 0.2

    def test_fallback_prediction_strong_home(self, model: XGBoostModel):
        """Test fallback prediction for strong home team."""
        prediction = model._fallback_prediction(
            home_attack=3.0,
            home_defense=0.8,
            away_attack=0.8,
            away_defense=2.0,
        )

        # Strong home team should be favored
        assert prediction.home_win_prob > prediction.away_win_prob

    def test_predict_batch_untrained(self, model: XGBoostModel):
        """Test batch prediction when model is untrained."""
        features = np.array([
            [1.5, 1.2, 1.3, 1.4, 50.0, 50.0, 0.0],
            [2.0, 1.0, 1.0, 2.0, 60.0, 40.0, 0.1],
        ])

        predictions = model.predict_batch(features)

        assert predictions.shape == (2, 3)
        # Neutral predictions (1/3 each)
        assert np.allclose(predictions, np.ones((2, 3)) / 3)


# =============================================================================
# Ensemble Predictor Tests
# =============================================================================


class TestEnsemblePredictor:
    """Test cases for ensemble predictor."""

    @pytest.fixture
    def predictor(self) -> EnsemblePredictor:
        """Create a default ensemble predictor."""
        return EnsemblePredictor()

    def test_initialization(self, predictor: EnsemblePredictor):
        """Test initialization."""
        assert predictor.poisson is not None
        assert predictor.elo is not None
        assert predictor.xgboost_model is not None

    def test_weight_constants(self, predictor: EnsemblePredictor):
        """Test weight constants sum to 1."""
        total = (
            EnsemblePredictor.WEIGHT_POISSON
            + EnsemblePredictor.WEIGHT_ELO
            + EnsemblePredictor.WEIGHT_XG
            + EnsemblePredictor.WEIGHT_XGBOOST
        )
        assert total == 1.0

    def test_normalize_probs(self, predictor: EnsemblePredictor):
        """Test probability normalization."""
        home, draw, away = predictor._normalize_probs(0.5, 0.3, 0.2)
        assert abs(home + draw + away - 1.0) < 0.001

        # Edge case: all zeros
        home, draw, away = predictor._normalize_probs(0, 0, 0)
        assert abs(home + draw + away - 1.0) < 0.001

    def test_predict_basic(self, predictor: EnsemblePredictor):
        """Test basic prediction."""
        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
            home_elo=1500,
            away_elo=1480,
        )

        assert isinstance(prediction, EnsemblePrediction)

        # Probabilities sum to 1
        total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        assert abs(total - 1.0) < 0.001

        # All probabilities are valid
        assert 0 <= prediction.home_win_prob <= 1
        assert 0 <= prediction.draw_prob <= 1
        assert 0 <= prediction.away_win_prob <= 1

        # Confidence is valid
        assert 0.52 <= prediction.confidence <= 0.98

    def test_predict_with_xg(self, predictor: EnsemblePredictor):
        """Test prediction with xG data."""
        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
            home_elo=1500,
            away_elo=1480,
            home_xg_for=1.8,
            home_xg_against=1.0,
            away_xg_for=1.2,
            away_xg_against=1.5,
        )

        assert prediction.xg_contribution is not None

    def test_predict_recommended_bet(self, predictor: EnsemblePredictor):
        """Test recommended bet is valid."""
        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
            home_elo=1500,
            away_elo=1480,
        )

        assert prediction.recommended_bet in ["home", "draw", "away"]

    def test_predict_with_odds(self, predictor: EnsemblePredictor):
        """Test prediction with bookmaker odds."""
        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
            home_elo=1500,
            away_elo=1480,
            odds_home=2.0,
            odds_draw=3.5,
            odds_away=4.0,
        )

        # Value score should be calculated
        assert prediction.value_score is not None

    def test_apply_llm_adjustments(self, predictor: EnsemblePredictor):
        """Test LLM adjustments are applied."""
        adjustments = LLMAdjustments(
            injury_impact_home=-0.1,
            injury_impact_away=0.0,
            sentiment_home=0.05,
            sentiment_away=-0.02,
            reasoning="Test adjustments",
        )

        prediction = predictor.predict(
            home_attack=1.5,
            home_defense=1.2,
            away_attack=1.3,
            away_defense=1.4,
            home_elo=1500,
            away_elo=1480,
            llm_adjustments=adjustments,
        )

        assert prediction.llm_adjustments is not None
        assert prediction.llm_adjustments.reasoning == "Test adjustments"

    def test_calculate_confidence(self, predictor: EnsemblePredictor):
        """Test confidence calculation."""
        # High confidence case (one probability dominates)
        confidence_high = predictor._calculate_confidence(0.7, 0.2, 0.1)
        assert confidence_high > 0.7

        # Low confidence case (probabilities close)
        confidence_low = predictor._calculate_confidence(0.35, 0.35, 0.30)
        assert confidence_low < 0.7

    def test_model_agreement(self, predictor: EnsemblePredictor):
        """Test model agreement calculation."""
        # High agreement
        contributions = [
            (0.5, 0.3, 0.2, 0.25),
            (0.52, 0.28, 0.20, 0.25),
            (0.48, 0.32, 0.20, 0.25),
            (0.50, 0.30, 0.20, 0.25),
        ]
        agreement = predictor._calculate_model_agreement(contributions)
        assert agreement > 0.8

        # Low agreement
        contributions_disagree = [
            (0.6, 0.2, 0.2, 0.25),
            (0.3, 0.4, 0.3, 0.25),
            (0.2, 0.3, 0.5, 0.25),
            (0.5, 0.25, 0.25, 0.25),
        ]
        agreement_low = predictor._calculate_model_agreement(contributions_disagree)
        assert agreement_low < 0.8


# =============================================================================
# LLM Adjustments Validation Tests
# =============================================================================


class TestLLMAdjustments:
    """Test cases for LLM adjustment dataclass."""

    def test_defaults(self):
        """Test default values."""
        adj = LLMAdjustments()
        assert adj.injury_impact_home == 0.0
        assert adj.injury_impact_away == 0.0
        assert adj.sentiment_home == 0.0
        assert adj.sentiment_away == 0.0
        assert adj.tactical_edge == 0.0
        assert adj.reasoning == ""

    def test_total_home_adjustment(self):
        """Test total home adjustment calculation."""
        adj = LLMAdjustments(
            injury_impact_home=-0.1,  # Home injured (negative)
            injury_impact_away=-0.15,  # Away injured (helps home)
            sentiment_home=0.05,
            tactical_edge=0.02,
        )

        # Total = -0.1 - (-0.15) + 0.05 + 0.02 = 0.12
        assert abs(adj.total_home_adjustment - 0.12) < 0.001

    def test_total_away_adjustment(self):
        """Test total away adjustment calculation."""
        adj = LLMAdjustments(
            injury_impact_home=-0.1,
            injury_impact_away=-0.05,
            sentiment_away=0.03,
            tactical_edge=0.02,
        )

        # Total = -0.05 - (-0.1) + 0.03 - 0.02 = 0.06
        assert abs(adj.total_away_adjustment - 0.06) < 0.001


# =============================================================================
# Pydantic Validation Tests
# =============================================================================


class TestInjuryAnalysisValidation:
    """Test cases for InjuryAnalysis Pydantic model."""

    def test_valid_input(self):
        """Test validation with valid input."""
        data = {
            "player_name": "Mohamed Salah",
            "position": "forward",
            "impact_score": 0.85,
            "confidence": 0.9,
            "is_key_player": True,
            "expected_return": "3-4 weeks",
            "reasoning": "Key player injury",
        }
        analysis = InjuryAnalysis.model_validate(data)
        assert analysis.player_name == "Mohamed Salah"
        assert analysis.impact_score == 0.85

    def test_string_to_float_coercion(self):
        """Test string values are coerced to float."""
        data = {
            "impact_score": "0.75",
            "confidence": "0.8",
        }
        analysis = InjuryAnalysis.model_validate(data)
        assert analysis.impact_score == 0.75
        assert analysis.confidence == 0.8

    def test_invalid_string_defaults_to_zero(self):
        """Test invalid string defaults to 0.0."""
        data = {
            "impact_score": "high",
            "confidence": "medium",
        }
        analysis = InjuryAnalysis.model_validate(data)
        assert analysis.impact_score == 0.0
        assert analysis.confidence == 0.0

    def test_none_values(self):
        """Test None values are handled."""
        data = {
            "player_name": None,
            "impact_score": None,
            "confidence": None,
        }
        analysis = InjuryAnalysis.model_validate(data)
        assert analysis.player_name is None
        assert analysis.impact_score == 0.0
        assert analysis.confidence == 0.0

    def test_bool_coercion(self):
        """Test bool coercion from various formats."""
        assert InjuryAnalysis(is_key_player="true").is_key_player is True
        assert InjuryAnalysis(is_key_player="yes").is_key_player is True
        assert InjuryAnalysis(is_key_player="1").is_key_player is True
        assert InjuryAnalysis(is_key_player="false").is_key_player is False

    def test_validate_helper_function(self):
        """Test validate_injury_analysis helper."""
        raw = {"impact_score": "0.5", "confidence": 0.7}
        analysis = validate_injury_analysis(raw)
        assert isinstance(analysis, InjuryAnalysis)
        assert analysis.impact_score == 0.5


class TestSentimentAnalysisValidation:
    """Test cases for SentimentAnalysis Pydantic model."""

    def test_valid_input(self):
        """Test validation with valid input."""
        data = {
            "sentiment_score": 0.6,
            "confidence": 0.8,
            "morale_indicator": "positive",
            "key_factors": ["winning streak", "fans support"],
            "reasoning": "Team in good spirits",
        }
        analysis = SentimentAnalysis.model_validate(data)
        assert analysis.sentiment_score == 0.6
        assert analysis.morale_indicator == "positive"

    def test_morale_normalization(self):
        """Test morale indicator normalization."""
        assert SentimentAnalysis(morale_indicator="very_positive").morale_indicator == "very_positive"
        assert SentimentAnalysis(morale_indicator="Very Negative").morale_indicator == "very_negative"
        assert SentimentAnalysis(morale_indicator="bad").morale_indicator == "negative"
        assert SentimentAnalysis(morale_indicator="good").morale_indicator == "positive"
        assert SentimentAnalysis(morale_indicator="unknown").morale_indicator == "neutral"

    def test_sentiment_score_range(self):
        """Test sentiment score must be in range."""
        # Valid range
        analysis = SentimentAnalysis(sentiment_score=-0.5)
        assert analysis.sentiment_score == -0.5

        # Coercion from string
        analysis = SentimentAnalysis.model_validate({"sentiment_score": "0.5"})
        assert analysis.sentiment_score == 0.5


class TestFormAnalysisValidation:
    """Test cases for FormAnalysis Pydantic model."""

    def test_valid_input(self):
        """Test validation with valid input."""
        data = {
            "sentiment_adjustment": 0.08,
            "confidence": 0.75,
            "form_assessment": {
                "recent_performance": "good",
                "trend": "improving",
                "trend_strength": 0.7,
            },
            "reasoning": "Strong recent form",
        }
        analysis = FormAnalysis.model_validate(data)
        assert analysis.sentiment_adjustment == 0.08
        assert analysis.form_assessment.recent_performance == "good"

    def test_performance_normalization(self):
        """Test performance value normalization."""
        assessment = FormAssessment(recent_performance="excellent")
        assert assessment.recent_performance == "excellent"

        assessment = FormAssessment(recent_performance="great")
        assert assessment.recent_performance == "excellent"

        assessment = FormAssessment(recent_performance="bad")
        assert assessment.recent_performance == "poor"

    def test_trend_normalization(self):
        """Test trend value normalization."""
        assert FormAssessment(trend="improving").trend == "improving"
        assert FormAssessment(trend="rising").trend == "improving"
        assert FormAssessment(trend="falling").trend == "declining"
        assert FormAssessment(trend="unknown").trend == "stable"

    def test_empty_form_assessment(self):
        """Test empty form_assessment is handled."""
        analysis = FormAnalysis.model_validate({"form_assessment": None})
        assert analysis.form_assessment is not None
        assert analysis.form_assessment.recent_performance == "average"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full prediction pipeline."""

    def test_full_prediction_pipeline(self):
        """Test complete prediction with all models."""
        predictor = EnsemblePredictor()

        adjustments = LLMAdjustments(
            injury_impact_home=-0.05,
            sentiment_home=0.03,
            reasoning="Minor injury concern, positive sentiment",
        )

        prediction = predictor.predict(
            home_attack=1.8,
            home_defense=1.1,
            away_attack=1.4,
            away_defense=1.3,
            home_elo=1550,
            away_elo=1480,
            home_xg_for=1.9,
            home_xg_against=1.0,
            away_xg_for=1.3,
            away_xg_against=1.4,
            llm_adjustments=adjustments,
            odds_home=1.9,
            odds_draw=3.5,
            odds_away=4.2,
        )

        # Validate complete prediction
        assert isinstance(prediction, EnsemblePrediction)
        assert prediction.poisson_contribution is not None
        assert prediction.elo_contribution is not None
        assert prediction.xg_contribution is not None
        assert prediction.llm_adjustments is not None
        assert prediction.value_score is not None
        assert prediction.recommended_bet in ["home", "draw", "away"]
