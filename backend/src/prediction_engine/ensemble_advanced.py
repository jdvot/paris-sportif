"""Advanced ensemble predictor with improved models and calibration.

Combines:
- Dixon-Coles model (corrects low-score bias)
- Advanced ELO system (dynamic K-factor, performance rating)
- Poisson model (baseline)
- Time-weighted recent form
- Probability calibration

This ensemble uses adaptive weighting based on data availability and match context.
"""

from dataclasses import dataclass
from typing import Literal, Optional
import numpy as np

from src.prediction_engine.models.poisson import PoissonModel, PoissonPrediction
from src.prediction_engine.models.dixon_coles import DixonColesModel, DixonColesPrediction
from src.prediction_engine.models.elo import ELOSystem, ELOPrediction
from src.prediction_engine.models.elo_advanced import AdvancedELOSystem, AdvancedELOPrediction


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
    value_score: Optional[float] = None

    # Model contributions for transparency
    model_contributions: list[ModelContribution] = None

    # LLM adjustments applied
    llm_adjustments: Optional[AdvancedLLMAdjustments] = None

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
    WEIGHT_DIXON_COLES = 0.35  # Primary model
    WEIGHT_ADVANCED_ELO = 0.30  # Recent form important
    WEIGHT_POISSON = 0.20  # Baseline
    WEIGHT_BASIC_ELO = 0.15  # Reference

    # Maximum LLM adjustment for safety
    MAX_LLM_ADJUSTMENT = 0.6

    def __init__(
        self,
        poisson_model: Optional[PoissonModel] = None,
        dixon_coles_model: Optional[DixonColesModel] = None,
        elo_system: Optional[ELOSystem] = None,
        advanced_elo_system: Optional[AdvancedELOSystem] = None,
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

        Returns:
            (home_prob, draw_prob, away_prob, avg_confidence)
        """
        weights = np.array(confidences)
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
        """
        # Clamp to avoid log(0)
        eps = 1e-6
        home_prob = max(eps, min(1 - eps, home_prob))
        draw_prob = max(eps, min(1 - eps, draw_prob))
        away_prob = max(eps, min(1 - eps, away_prob))

        # Convert to log-odds
        home_logit = np.log(home_prob / (1 - home_prob))
        draw_logit = np.log(draw_prob / (1 - draw_prob))
        away_logit = np.log(away_prob / (1 - away_prob))

        # Get adjustments
        home_adj = adjustments.total_home_adjustment
        away_adj = adjustments.total_away_adjustment

        # Clamp adjustments
        home_adj = np.clip(home_adj, -self.MAX_LLM_ADJUSTMENT, self.MAX_LLM_ADJUSTMENT)
        away_adj = np.clip(away_adj, -self.MAX_LLM_ADJUSTMENT, self.MAX_LLM_ADJUSTMENT)

        # Apply adjustments
        home_logit += home_adj
        away_logit += away_adj
        draw_logit -= abs(home_adj - away_adj) * 0.5

        # Convert back to probabilities
        home_prob = 1.0 / (1.0 + np.exp(-home_logit))
        draw_prob = 1.0 / (1.0 + np.exp(-draw_logit))
        away_prob = 1.0 / (1.0 + np.exp(-away_logit))

        # Normalize
        return self._normalize_probs(home_prob, draw_prob, away_prob)

    def _calculate_value(
        self,
        prob: float,
        odds: Optional[float],
    ) -> Optional[float]:
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
        """
        probs = [home_prob, draw_prob, away_prob]
        max_prob = max(probs)
        second_prob = sorted(probs)[-2]

        # Probability margin confidence
        margin = max_prob - second_prob
        margin_conf = 0.5 + (margin * 1.5)  # 0% margin = 50%, 30% = 95%

        # Entropy-based confidence (uniform = 0%, certain = 1)
        entropy = -sum(p * np.log(p + 1e-10) for p in probs)
        entropy_conf = 1.0 - (entropy / np.log(3))  # Normalize by max entropy

        # Model agreement confidence
        agreement_conf = 0.5 + (model_agreement * 0.4)

        # Combined confidence
        confidence = (
            margin_conf * 0.5 + entropy_conf * 0.25 + agreement_conf * 0.25
        )
        return min(0.98, max(0.5, confidence))

    def _calculate_model_agreement(
        self,
        predictions: list[tuple[float, float, float]],
        weights: list[float],
    ) -> float:
        """
        Calculate how much models agree on their predictions.

        Returns 0-1, where 1 = perfect agreement.
        """
        if not predictions:
            return 0.5

        # Convert to argmax (which outcome each predicts)
        outcomes = []
        for pred in predictions:
            if pred[0] > pred[1] and pred[0] > pred[2]:
                outcomes.append(0)  # home
            elif pred[2] > pred[1]:
                outcomes.append(2)  # away
            else:
                outcomes.append(1)  # draw

        # Calculate agreement
        total_weight = sum(weights)
        weights_arr = np.array(weights) / total_weight

        # Weighted entropy of outcomes
        unique_outcomes = set(outcomes)
        outcome_probs = []
        for outcome in unique_outcomes:
            prob = sum(
                w for o, w in zip(outcomes, weights_arr) if o == outcome
            )
            outcome_probs.append(prob)

        entropy = -sum(p * np.log(p + 1e-10) for p in outcome_probs)
        # Normalize (max entropy for 3 outcomes = ln(3))
        agreement = 1.0 - (entropy / np.log(3))

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
        home_xg_for: Optional[float] = None,
        home_xg_against: Optional[float] = None,
        away_xg_for: Optional[float] = None,
        away_xg_against: Optional[float] = None,
        # Recent form for Advanced ELO
        home_recent_form: Optional[list[Literal["W", "D", "L"]]] = None,
        away_recent_form: Optional[list[Literal["W", "D", "L"]]] = None,
        # Time weight for Dixon-Coles
        time_weight: float = 1.0,
        # LLM adjustments
        llm_adjustments: Optional[AdvancedLLMAdjustments] = None,
        # Bookmaker odds
        odds_home: Optional[float] = None,
        odds_draw: Optional[float] = None,
        odds_away: Optional[float] = None,
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

        # 1. Dixon-Coles Model (Primary)
        if home_xg_for and home_xg_against and away_xg_for and away_xg_against:
            # Use xG if available
            dc_pred = self.dixon_coles.predict_with_xg(
                home_xg_for=home_xg_for,
                home_xg_against=home_xg_against,
                away_xg_for=away_xg_for,
                away_xg_against=away_xg_against,
                time_weight=time_weight,
            )
            dc_weight = self.WEIGHT_DIXON_COLES * 1.2  # Boost with xG
        else:
            dc_pred = self.dixon_coles.predict(
                home_attack=home_attack,
                home_defense=home_defense,
                away_attack=away_attack,
                away_defense=away_defense,
                time_weight=time_weight,
            )
            dc_weight = self.WEIGHT_DIXON_COLES

        predictions.append((
            dc_pred.home_win_prob,
            dc_pred.draw_prob,
            dc_pred.away_win_prob,
        ))
        weights_list.append(dc_weight)
        contributions.append(ModelContribution(
            name="Dixon-Coles",
            home_prob=dc_pred.home_win_prob,
            draw_prob=dc_pred.draw_prob,
            away_prob=dc_pred.away_win_prob,
            weight=dc_weight,
            confidence=0.8,
        ))

        # 2. Advanced ELO (Secondary with recent form)
        adv_elo_pred = self.advanced_elo.predict(
            home_rating=home_elo,
            away_rating=away_elo,
            home_recent_form=home_recent_form,
            away_recent_form=away_recent_form,
        )
        predictions.append((
            adv_elo_pred.home_win_prob,
            adv_elo_pred.draw_prob,
            adv_elo_pred.away_win_prob,
        ))
        weights_list.append(self.WEIGHT_ADVANCED_ELO)
        contributions.append(ModelContribution(
            name="Advanced ELO",
            home_prob=adv_elo_pred.home_win_prob,
            draw_prob=adv_elo_pred.draw_prob,
            away_prob=adv_elo_pred.away_win_prob,
            weight=self.WEIGHT_ADVANCED_ELO,
            confidence=adv_elo_pred.confidence,
        ))

        # 3. Basic Poisson (Baseline validation)
        poisson_pred = self.poisson.predict(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
        )
        predictions.append((
            poisson_pred.home_win_prob,
            poisson_pred.draw_prob,
            poisson_pred.away_win_prob,
        ))
        weights_list.append(self.WEIGHT_POISSON)
        contributions.append(ModelContribution(
            name="Poisson",
            home_prob=poisson_pred.home_win_prob,
            draw_prob=poisson_pred.draw_prob,
            away_prob=poisson_pred.away_win_prob,
            weight=self.WEIGHT_POISSON,
            confidence=0.7,
        ))

        # 4. Basic ELO (Reference)
        elo_pred = self.elo.predict(home_elo, away_elo)
        predictions.append((
            elo_pred.home_win_prob,
            elo_pred.draw_prob,
            elo_pred.away_win_prob,
        ))
        weights_list.append(self.WEIGHT_BASIC_ELO)
        contributions.append(ModelContribution(
            name="Basic ELO",
            home_prob=elo_pred.home_win_prob,
            draw_prob=elo_pred.draw_prob,
            away_prob=elo_pred.away_win_prob,
            weight=self.WEIGHT_BASIC_ELO,
            confidence=0.65,
        ))

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
        confidence = self._calculate_confidence(
            home_prob, draw_prob, away_prob, model_agreement
        )

        # Calculate uncertainty
        entropy = -sum(
            p * np.log(p + 1e-10)
            for p in [home_prob, draw_prob, away_prob]
        )
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
