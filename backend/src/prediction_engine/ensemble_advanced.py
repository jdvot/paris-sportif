"""Advanced ensemble predictor with improved models and calibration.

Combines:
- Dixon-Coles model (corrects low-score bias)
- Advanced ELO system (dynamic K-factor, performance rating)
- Poisson model (baseline)
- XGBoost ML model (trained on historical data)
- Random Forest ML model (trained on historical data)
- Time-weighted recent form
- Probability calibration

This ensemble uses adaptive weighting based on data availability and match context.
"""

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np

from src.prediction_engine.models.dixon_coles import DixonColesModel
from src.prediction_engine.models.elo import ELOSystem
from src.prediction_engine.models.elo_advanced import AdvancedELOSystem
from src.prediction_engine.models.poisson import PoissonModel

logger = logging.getLogger(__name__)

# Try to import HuggingFace ML client (remote inference)
try:
    from src.ml.huggingface_client import get_hf_ml_client

    HF_ML_AVAILABLE = True
except ImportError:
    HF_ML_AVAILABLE = False
    logger.warning("HuggingFace ML client not available")


@dataclass
class AdvancedLLMAdjustments:
    """Advanced LLM adjustments with better calibration."""

    injury_impact_home: float = 0.0  # -0.3 to 0.0
    injury_impact_away: float = 0.0  # -0.3 to 0.0
    sentiment_home: float = 0.0  # -0.1 to 0.1
    sentiment_away: float = 0.0  # -0.1 to 0.1
    tactical_edge: float = 0.0  # -0.05 to 0.05
    motivation_factor: float = 0.0  # -0.15 to 0.15 (extra motivation/pressure)
    reasoning: str = ""

    @property
    def total_home_adjustment(self) -> float:
        """Total adjustment for home team."""
        return (
            self.injury_impact_home
            - self.injury_impact_away
            + self.sentiment_home
            + self.tactical_edge
            + self.motivation_factor
        )

    @property
    def total_away_adjustment(self) -> float:
        """Total adjustment for away team."""
        return (
            self.injury_impact_away
            - self.injury_impact_home
            + self.sentiment_away
            - self.tactical_edge
            + self.motivation_factor
        )


@dataclass
class ModelContribution:
    """Individual model's contribution."""

    name: str
    home_prob: float
    draw_prob: float
    away_prob: float
    weight: float
    confidence: float = 0.5


@dataclass
class AdvancedEnsemblePrediction:
    """Final advanced ensemble prediction."""

    # Final probabilities
    home_win_prob: float
    draw_prob: float
    away_win_prob: float

    # Recommended bet and confidence
    recommended_bet: Literal["home", "draw", "away"]
    confidence: float
    calibration_score: float  # 0-1, how well calibrated the probabilities are

    # Value score (vs bookmaker odds)
    value_score: float | None = None

    # Model contributions for transparency
    model_contributions: list[ModelContribution] | None = None

    # LLM adjustments applied
    llm_adjustments: AdvancedLLMAdjustments | None = None

    # Expected goals
    expected_home_goals: float = 0.0
    expected_away_goals: float = 0.0

    # Additional metrics
    model_agreement: float = 0.0  # How much models agree (0-1)
    uncertainty: float = 0.0  # Prediction uncertainty (0-1)


class AdvancedEnsemblePredictor:
    """
    Advanced ensemble predictor with multiple statistical models.

    Model Architecture:
    1. Dixon-Coles: Primary model, handles low-score bias & time decay
    2. Advanced ELO: Secondary, adapts to recent form & K-factor
    3. Poisson: Baseline for validation
    4. Basic ELO: Reference model

    Weighting Strategy:
    - Adaptive based on data availability
    - Higher weight for models with xG data
    - Performance-based calibration
    """

    # Base model weights (can be adjusted based on data availability)
    # Improved weights based on empirical model performance
    # When ML models are trained, they get higher weights
    WEIGHT_DIXON_COLES = 0.30  # Primary statistical model
    WEIGHT_ADVANCED_ELO = 0.25  # Recent form
    WEIGHT_POISSON = 0.10  # Baseline validation
    WEIGHT_BASIC_ELO = 0.05  # Reference model
    WEIGHT_XGBOOST = 0.20  # ML model (when trained)
    WEIGHT_RANDOM_FOREST = 0.10  # ML model (when trained)

    # Weights when ML not available (fallback to statistical models)
    WEIGHT_DIXON_COLES_NO_ML = 0.40
    WEIGHT_ADVANCED_ELO_NO_ML = 0.35
    WEIGHT_POISSON_NO_ML = 0.15
    WEIGHT_BASIC_ELO_NO_ML = 0.10

    # Maximum LLM adjustment for safety
    MAX_LLM_ADJUSTMENT = 0.5

    def __init__(
        self,
        poisson_model: PoissonModel | None = None,
        dixon_coles_model: DixonColesModel | None = None,
        elo_system: ELOSystem | None = None,
        advanced_elo_system: AdvancedELOSystem | None = None,
    ):
        """Initialize ensemble with component models."""
        self.poisson = poisson_model or PoissonModel()
        self.dixon_coles = dixon_coles_model or DixonColesModel()
        self.elo = elo_system or ELOSystem()
        self.advanced_elo = advanced_elo_system or AdvancedELOSystem()

    def _normalize_probs(
        self,
        home: float,
        draw: float,
        away: float,
    ) -> tuple[float, float, float]:
        """Normalize probabilities to sum to 1."""
        total = home + draw + away
        if total == 0:
            return 0.33, 0.34, 0.33
        return home / total, draw / total, away / total

    def _calibrate_probabilities(
        self,
        probs: list[tuple[float, float, float]],
        confidences: list[float],
    ) -> tuple[float, float, float, float]:
        """
        Calibrate probabilities using confidence scores.

        Higher confidence models pull probabilities toward their prediction.
        Uses softmax weighting for better probability scaling.

        Returns:
            (home_prob, draw_prob, away_prob, avg_confidence)
        """
        # Use softmax weighting for better confidence scaling
        # This is more stable than direct normalization
        confidences_array = np.array(confidences)

        # Apply softmax to convert confidences to weights
        # Subtract max for numerical stability
        confidences_centered = confidences_array - np.max(confidences_array)
        weights = np.exp(confidences_centered)
        weights = weights / weights.sum()

        home_weighted = sum(p[0] * w for p, w in zip(probs, weights))
        draw_weighted = sum(p[1] * w for p, w in zip(probs, weights))
        away_weighted = sum(p[2] * w for p, w in zip(probs, weights))

        home_prob, draw_prob, away_prob = self._normalize_probs(
            home_weighted, draw_weighted, away_weighted
        )

        avg_confidence = float(np.mean(confidences))

        return home_prob, draw_prob, away_prob, avg_confidence

    def _apply_llm_adjustments(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        adjustments: AdvancedLLMAdjustments,
    ) -> tuple[float, float, float]:
        """
        Apply LLM adjustments using log-odds transformation.

        Safer and more mathematically sound than linear adjustments.
        Uses conservative scaling to prevent over-adjustment.
        """
        # Clamp to avoid log(0)
        eps = 1e-6
        home_prob = np.clip(home_prob, eps, 1 - eps)
        draw_prob = np.clip(draw_prob, eps, 1 - eps)
        away_prob = np.clip(away_prob, eps, 1 - eps)

        # Convert to log-odds
        home_logit = np.log(home_prob / (1 - home_prob))
        draw_logit = np.log(draw_prob / (1 - draw_prob))
        away_logit = np.log(away_prob / (1 - away_prob))

        # Get adjustments
        home_adj = adjustments.total_home_adjustment
        away_adj = adjustments.total_away_adjustment

        # Clamp adjustments more conservatively
        home_adj = np.clip(
            home_adj, -self.MAX_LLM_ADJUSTMENT * 0.75, self.MAX_LLM_ADJUSTMENT * 0.75
        )
        away_adj = np.clip(
            away_adj, -self.MAX_LLM_ADJUSTMENT * 0.75, self.MAX_LLM_ADJUSTMENT * 0.75
        )

        # Apply adjustments to log-odds directly
        # Note: Adjustments are already calibrated in adjustments.py (score * confidence * 0.1)
        # No additional scaling needed to avoid double-dampening
        home_logit += home_adj
        away_logit += away_adj
        # Draw logit adjustment (reduces draw probability when teams differ more)
        draw_logit -= abs(home_adj - away_adj) * 0.3

        # Convert back to probabilities
        home_prob = 1.0 / (1.0 + np.exp(-home_logit))
        draw_prob = 1.0 / (1.0 + np.exp(-draw_logit))
        away_prob = 1.0 / (1.0 + np.exp(-away_logit))

        # Normalize
        return self._normalize_probs(home_prob, draw_prob, away_prob)

    def _calculate_value(
        self,
        prob: float,
        odds: float | None,
    ) -> float | None:
        """
        Calculate value score vs bookmaker odds.

        Value = (prob × odds) - 1
        Positive = potential edge
        """
        if odds is None or odds <= 1:
            return None

        value = (prob * odds) - 1
        return max(-1.0, min(1.0, value))  # Clamp to [-1, 1]

    def _calculate_confidence(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        model_agreement: float = 0.5,
    ) -> float:
        """
        Calculate prediction confidence.

        Based on probability margin, entropy, and model agreement.
        Better calibrated with multiple factors.
        """
        probs = [home_prob, draw_prob, away_prob]
        max_prob = max(probs)
        second_prob = sorted(probs)[-2]

        # Probability margin confidence
        # Scale: 0% margin = 0.52, 30%+ margin = 0.95
        margin = max_prob - second_prob
        margin_conf = 0.52 + (margin * 1.43)

        # Entropy-based confidence (uniform = 0%, certain = 1)
        # Measures how spread out the probabilities are
        entropy = -sum(p * np.log(p + 1e-10) for p in probs)
        entropy_conf = 1.0 - (entropy / np.log(3))  # Normalize by max entropy

        # Model agreement confidence
        # Higher agreement = higher confidence in ensemble prediction
        agreement_conf = 0.50 + (model_agreement * 0.40)  # 0.5 to 0.9

        # Combined confidence with better weighting
        # 50% from margin (most important), 25% each from entropy and agreement
        confidence = margin_conf * 0.50 + entropy_conf * 0.25 + agreement_conf * 0.25

        # Better calibrated range: 0.52 to 0.98
        return float(np.clip(confidence, 0.52, 0.98))

    def _calculate_model_agreement(
        self,
        predictions: list[tuple[float, float, float]],
        weights: list[float],
    ) -> float:
        """
        Calculate how much models agree on their predictions.

        Uses both argmax agreement and probability variance.
        Returns 0-1, where 1 = perfect agreement.
        """
        if not predictions:
            return 0.5

        # Argmax-based agreement (which outcome each model predicts)
        outcomes = []
        for pred in predictions:
            if pred[0] > pred[1] and pred[0] > pred[2]:
                outcomes.append(0)  # home
            elif pred[2] > pred[1]:
                outcomes.append(2)  # away
            else:
                outcomes.append(1)  # draw

        # Calculate weighted outcome distribution
        total_weight = sum(weights)
        weights_arr = np.array(weights) / total_weight

        # Weighted entropy of outcomes
        unique_outcomes = set(outcomes)
        outcome_probs = []
        for outcome in unique_outcomes:
            prob = sum(w for o, w in zip(outcomes, weights_arr) if o == outcome)
            outcome_probs.append(prob)

        entropy = -sum(p * np.log(p + 1e-10) for p in outcome_probs)
        # Normalize (max entropy for 3 outcomes = ln(3))
        argmax_agreement = 1.0 - (entropy / np.log(3))

        # Probability variance agreement
        # Calculate variance in predictions across models
        home_probs = np.array([p[0] for p in predictions])
        draw_probs = np.array([p[1] for p in predictions])
        away_probs = np.array([p[2] for p in predictions])

        # Weighted variance
        home_var = np.average(
            (home_probs - np.average(home_probs, weights=weights_arr)) ** 2, weights=weights_arr
        )
        draw_var = np.average(
            (draw_probs - np.average(draw_probs, weights=weights_arr)) ** 2, weights=weights_arr
        )
        away_var = np.average(
            (away_probs - np.average(away_probs, weights=weights_arr)) ** 2, weights=weights_arr
        )

        avg_variance = (home_var + draw_var + away_var) / 3.0
        # Convert variance to agreement (lower variance = higher agreement)
        # Variance ranges from 0 to ~0.08, so normalize by 0.1
        variance_agreement = 1.0 - min(1.0, avg_variance / 0.1)

        # Combined agreement: 60% from argmax, 40% from variance
        agreement = (argmax_agreement * 0.6) + (variance_agreement * 0.4)

        return float(np.clip(agreement, 0.0, 1.0))

    def predict(
        self,
        # Team stats for Poisson/Dixon-Coles
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        # ELO ratings
        home_elo: float,
        away_elo: float,
        # Optional xG data (improves predictions significantly)
        home_xg_for: float | None = None,
        home_xg_against: float | None = None,
        away_xg_for: float | None = None,
        away_xg_against: float | None = None,
        # Recent form for Advanced ELO
        home_recent_form: list[Literal["W", "D", "L"]] | None = None,
        away_recent_form: list[Literal["W", "D", "L"]] | None = None,
        # Time weight for Dixon-Coles
        time_weight: float = 1.0,
        # LLM adjustments
        llm_adjustments: AdvancedLLMAdjustments | None = None,
        # Bookmaker odds
        odds_home: float | None = None,
        odds_draw: float | None = None,
        odds_away: float | None = None,
        # Team IDs for ML models
        home_team_id: int | None = None,
        away_team_id: int | None = None,
        # Form scores for ML (0-100)
        home_form_score: float = 50.0,
        away_form_score: float = 50.0,
        # Fatigue scores for extended ML features (0=fatigued, 1=rested)
        home_rest_days: float = 0.5,
        home_congestion: float = 0.5,
        away_rest_days: float = 0.5,
        away_congestion: float = 0.5,
    ) -> AdvancedEnsemblePrediction:
        """
        Make advanced ensemble prediction.

        Args:
            home_attack, home_defense, away_attack, away_defense: Team stats
            home_elo, away_elo: ELO ratings
            home_xg_for, home_xg_against, away_xg_for, away_xg_against: xG data
            home_recent_form, away_recent_form: Recent match results
            time_weight: Time weight for Dixon-Coles (0-1)
            llm_adjustments: LLM-derived adjustments
            odds_home, odds_draw, odds_away: Bookmaker odds

        Returns:
            AdvancedEnsemblePrediction with combined probabilities
        """
        contributions: list[ModelContribution] = []
        predictions: list[tuple[float, float, float]] = []
        weights_list: list[float] = []

        # Check if HuggingFace ML service is available
        hf_client = get_hf_ml_client() if HF_ML_AVAILABLE else None
        ml_available = hf_client is not None and hf_client.is_available()

        # Determine weights based on ML availability
        if ml_available:
            dc_base_weight = self.WEIGHT_DIXON_COLES
            elo_adv_weight = self.WEIGHT_ADVANCED_ELO
            poisson_weight = self.WEIGHT_POISSON
            basic_elo_weight = self.WEIGHT_BASIC_ELO
        else:
            dc_base_weight = self.WEIGHT_DIXON_COLES_NO_ML
            elo_adv_weight = self.WEIGHT_ADVANCED_ELO_NO_ML
            poisson_weight = self.WEIGHT_POISSON_NO_ML
            basic_elo_weight = self.WEIGHT_BASIC_ELO_NO_ML

        # 1. Dixon-Coles Model (Primary)
        # Check if xG data is available and meaningful
        has_xg_data = all(
            [
                home_xg_for and home_xg_for > 0,
                home_xg_against and home_xg_against > 0,
                away_xg_for and away_xg_for > 0,
                away_xg_against and away_xg_against > 0,
            ]
        )

        if has_xg_data:
            # Use xG if available - more predictive than actual goals
            dc_pred = self.dixon_coles.predict_with_xg(
                home_xg_for=home_xg_for,  # type: ignore
                home_xg_against=home_xg_against,  # type: ignore
                away_xg_for=away_xg_for,  # type: ignore
                away_xg_against=away_xg_against,  # type: ignore
                time_weight=time_weight,
            )
            # Boost weight when using xG data (25% increase - more conservative than before)
            dc_weight = dc_base_weight * 1.25
        else:
            dc_pred = self.dixon_coles.predict(
                home_attack=home_attack,
                home_defense=home_defense,
                away_attack=away_attack,
                away_defense=away_defense,
                time_weight=time_weight,
            )
            dc_weight = dc_base_weight

        predictions.append(
            (
                dc_pred.home_win_prob,
                dc_pred.draw_prob,
                dc_pred.away_win_prob,
            )
        )
        weights_list.append(dc_weight)
        contributions.append(
            ModelContribution(
                name="Dixon-Coles",
                home_prob=dc_pred.home_win_prob,
                draw_prob=dc_pred.draw_prob,
                away_prob=dc_pred.away_win_prob,
                weight=dc_weight,
                confidence=0.8,
            )
        )

        # 2. Advanced ELO (Secondary with recent form)
        adv_elo_pred = self.advanced_elo.predict(
            home_rating=home_elo,
            away_rating=away_elo,
            home_recent_form=home_recent_form,
            away_recent_form=away_recent_form,
        )
        predictions.append(
            (
                adv_elo_pred.home_win_prob,
                adv_elo_pred.draw_prob,
                adv_elo_pred.away_win_prob,
            )
        )
        weights_list.append(elo_adv_weight)
        contributions.append(
            ModelContribution(
                name="Advanced ELO",
                home_prob=adv_elo_pred.home_win_prob,
                draw_prob=adv_elo_pred.draw_prob,
                away_prob=adv_elo_pred.away_win_prob,
                weight=self.WEIGHT_ADVANCED_ELO,
                confidence=adv_elo_pred.confidence,
            )
        )

        # 3. Basic Poisson (Baseline validation)
        poisson_pred = self.poisson.predict(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
        )
        predictions.append(
            (
                poisson_pred.home_win_prob,
                poisson_pred.draw_prob,
                poisson_pred.away_win_prob,
            )
        )
        weights_list.append(poisson_weight)
        contributions.append(
            ModelContribution(
                name="Poisson",
                home_prob=poisson_pred.home_win_prob,
                draw_prob=poisson_pred.draw_prob,
                away_prob=poisson_pred.away_win_prob,
                weight=self.WEIGHT_POISSON,
                confidence=0.7,
            )
        )

        # 4. Basic ELO (Reference)
        elo_pred = self.elo.predict(home_elo, away_elo)
        predictions.append(
            (
                elo_pred.home_win_prob,
                elo_pred.draw_prob,
                elo_pred.away_win_prob,
            )
        )
        weights_list.append(basic_elo_weight)
        contributions.append(
            ModelContribution(
                name="Basic ELO",
                home_prob=elo_pred.home_win_prob,
                draw_prob=elo_pred.draw_prob,
                away_prob=elo_pred.away_win_prob,
                weight=basic_elo_weight,
                confidence=0.65,
            )
        )

        # 5. ML Models (XGBoost & Random Forest) - via HuggingFace service
        if ml_available and hf_client is not None:
            try:
                # Call HuggingFace ML service
                ml_result = hf_client.predict_sync(
                    home_attack=home_attack,
                    home_defense=home_defense,
                    away_attack=away_attack,
                    away_defense=away_defense,
                    home_elo=home_elo,
                    away_elo=away_elo,
                    home_form=home_form_score / 100.0,  # Convert 0-100 to 0-1
                    away_form=away_form_score / 100.0,
                    home_rest_days=home_rest_days * 7.0,  # Convert to days
                    away_rest_days=away_rest_days * 7.0,
                    home_fixture_congestion=home_congestion,
                    away_fixture_congestion=away_congestion,
                )

                if ml_result and "ensemble" in ml_result:
                    ensemble = ml_result["ensemble"]
                    # ML ensemble prediction
                    predictions.append(
                        (
                            ensemble["home_win"],
                            ensemble["draw"],
                            ensemble["away_win"],
                        )
                    )
                    ml_weight = self.WEIGHT_XGBOOST + self.WEIGHT_RANDOM_FOREST
                    weights_list.append(ml_weight)
                    contributions.append(
                        ModelContribution(
                            name="ML (HuggingFace)",
                            home_prob=ensemble["home_win"],
                            draw_prob=ensemble["draw"],
                            away_prob=ensemble["away_win"],
                            weight=ml_weight,
                            confidence=ml_result.get("confidence", 0.7),
                        )
                    )
                    logger.info("ML prediction added from HuggingFace service")
            except Exception as e:
                logger.warning(f"HuggingFace ML prediction failed: {e}")

        # Calculate model agreement
        model_agreement = self._calculate_model_agreement(predictions, weights_list)

        # Calibrate probabilities using confidence scores
        confidences = [c.confidence for c in contributions]
        home_prob, draw_prob, away_prob, avg_confidence = self._calibrate_probabilities(
            predictions, confidences
        )

        # Apply LLM adjustments if available
        if llm_adjustments:
            home_prob, draw_prob, away_prob = self._apply_llm_adjustments(
                home_prob, draw_prob, away_prob, llm_adjustments
            )

        # Determine recommended bet
        probs = {"home": home_prob, "draw": draw_prob, "away": away_prob}
        recommended_bet = max(probs, key=probs.get)  # type: ignore

        # Calculate confidence
        confidence = self._calculate_confidence(home_prob, draw_prob, away_prob, model_agreement)

        # Calculate uncertainty
        entropy = -sum(p * np.log(p + 1e-10) for p in [home_prob, draw_prob, away_prob])
        uncertainty = entropy / np.log(3)  # Normalize to [0, 1]

        # Calibration score (how well distributed probabilities are)
        calibration = 1.0 - uncertainty * 0.3  # Account for entropy

        # Calculate value if odds available
        value_score = None
        if recommended_bet == "home" and odds_home:
            value_score = self._calculate_value(home_prob, odds_home)
        elif recommended_bet == "draw" and odds_draw:
            value_score = self._calculate_value(draw_prob, odds_draw)
        elif recommended_bet == "away" and odds_away:
            value_score = self._calculate_value(away_prob, odds_away)

        # Expected goals
        exp_home = dc_pred.expected_home_goals
        exp_away = dc_pred.expected_away_goals

        return AdvancedEnsemblePrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            recommended_bet=recommended_bet,  # type: ignore
            confidence=confidence,
            calibration_score=calibration,
            value_score=value_score,
            model_contributions=contributions,
            llm_adjustments=llm_adjustments,
            expected_home_goals=exp_home,
            expected_away_goals=exp_away,
            model_agreement=model_agreement,
            uncertainty=uncertainty,
        )


# Default instance
advanced_ensemble_predictor = AdvancedEnsemblePredictor()
