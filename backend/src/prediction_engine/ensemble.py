"""Ensemble model combining multiple prediction methods.

Combines Poisson, ELO, xG, and XGBoost predictions with optional LLM adjustments.
"""

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from src.prediction_engine.models.poisson import PoissonModel, PoissonPrediction
from src.prediction_engine.models.elo import ELOSystem, ELOPrediction


@dataclass
class LLMAdjustments:
    """Adjustments derived from LLM analysis."""

    injury_impact_home: float = 0.0  # -0.3 to 0.0
    injury_impact_away: float = 0.0  # -0.3 to 0.0
    sentiment_home: float = 0.0  # -0.1 to 0.1
    sentiment_away: float = 0.0  # -0.1 to 0.1
    tactical_edge: float = 0.0  # -0.05 to 0.05
    reasoning: str = ""

    @property
    def total_home_adjustment(self) -> float:
        """Total adjustment for home team."""
        return (
            self.injury_impact_home
            - self.injury_impact_away  # Opponent injury helps
            + self.sentiment_home
            + self.tactical_edge
        )

    @property
    def total_away_adjustment(self) -> float:
        """Total adjustment for away team."""
        return (
            self.injury_impact_away
            - self.injury_impact_home
            + self.sentiment_away
            - self.tactical_edge
        )


@dataclass
class ModelContribution:
    """Individual model's contribution."""

    home_prob: float
    draw_prob: float
    away_prob: float
    weight: float


@dataclass
class EnsemblePrediction:
    """Final ensemble prediction."""

    # Final probabilities
    home_win_prob: float
    draw_prob: float
    away_win_prob: float

    # Recommended bet
    recommended_bet: Literal["home", "draw", "away"]
    confidence: float

    # Value score (vs bookmaker odds)
    value_score: Optional[float] = None

    # Model contributions
    poisson_contribution: Optional[ModelContribution] = None
    elo_contribution: Optional[ModelContribution] = None
    xg_contribution: Optional[ModelContribution] = None
    xgboost_contribution: Optional[ModelContribution] = None

    # LLM adjustments applied
    llm_adjustments: Optional[LLMAdjustments] = None

    # Expected goals
    expected_home_goals: float = 0.0
    expected_away_goals: float = 0.0


class EnsemblePredictor:
    """
    Ensemble predictor combining multiple models.

    Model weights (default):
    - Poisson: 25%
    - ELO: 15%
    - xG Model: 25%
    - XGBoost: 35%

    LLM adjustments are applied as multiplicative factors on log-odds,
    bounded to ±0.5 to prevent runaway influence.
    """

    # Default model weights
    WEIGHT_POISSON = 0.25
    WEIGHT_ELO = 0.15
    WEIGHT_XG = 0.25
    WEIGHT_XGBOOST = 0.35

    # Maximum LLM adjustment
    MAX_LLM_ADJUSTMENT = 0.5

    def __init__(
        self,
        poisson_model: Optional[PoissonModel] = None,
        elo_system: Optional[ELOSystem] = None,
    ):
        """Initialize ensemble with component models."""
        self.poisson = poisson_model or PoissonModel()
        self.elo = elo_system or ELOSystem()

        # XGBoost model would be loaded here
        self.xgboost_model = None

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

    def _apply_llm_adjustments(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        adjustments: LLMAdjustments,
    ) -> tuple[float, float, float]:
        """
        Apply LLM adjustments to probabilities.

        Uses log-odds transformation for proper adjustment application.
        """
        # Clamp probabilities to avoid log(0)
        eps = 1e-6
        home_prob = max(eps, min(1 - eps, home_prob))
        draw_prob = max(eps, min(1 - eps, draw_prob))
        away_prob = max(eps, min(1 - eps, away_prob))

        # Convert to log-odds (logit)
        home_logit = np.log(home_prob / (1 - home_prob))
        draw_logit = np.log(draw_prob / (1 - draw_prob))
        away_logit = np.log(away_prob / (1 - away_prob))

        # Calculate adjustments
        home_adj = adjustments.total_home_adjustment
        away_adj = adjustments.total_away_adjustment

        # Clamp adjustments
        home_adj = np.clip(home_adj, -self.MAX_LLM_ADJUSTMENT, self.MAX_LLM_ADJUSTMENT)
        away_adj = np.clip(away_adj, -self.MAX_LLM_ADJUSTMENT, self.MAX_LLM_ADJUSTMENT)

        # Apply adjustments to log-odds
        home_logit += home_adj
        away_logit += away_adj
        # Draw logit slightly decreases when teams get stronger/weaker
        draw_logit -= abs(home_adj - away_adj) * 0.5

        # Convert back to probabilities (sigmoid)
        home_prob = 1 / (1 + np.exp(-home_logit))
        draw_prob = 1 / (1 + np.exp(-draw_logit))
        away_prob = 1 / (1 + np.exp(-away_logit))

        # Normalize to sum to 1
        return self._normalize_probs(home_prob, draw_prob, away_prob)

    def _calculate_value(
        self,
        prob: float,
        odds: Optional[float],
    ) -> Optional[float]:
        """
        Calculate value score vs bookmaker odds.

        Value = (our_prob × odds) - 1
        Positive value = potential edge
        """
        if odds is None or odds <= 1:
            return None

        # Implied probability from odds
        implied_prob = 1 / odds

        # Value score
        value = (prob * odds) - 1

        return value

    def _calculate_confidence(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
    ) -> float:
        """
        Calculate prediction confidence.

        Based on probability margin and consistency.
        """
        probs = [home_prob, draw_prob, away_prob]
        max_prob = max(probs)
        second_prob = sorted(probs)[-2]

        # Margin between top prediction and second
        margin = max_prob - second_prob

        # Confidence scales with margin
        # 0% margin = 50% confidence, 30%+ margin = 90%+ confidence
        confidence = 0.5 + (margin * 1.5)
        confidence = min(0.95, max(0.5, confidence))

        return confidence

    def predict(
        self,
        # Team stats for Poisson
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        # ELO ratings
        home_elo: float,
        away_elo: float,
        # Optional xG data
        home_xg_for: Optional[float] = None,
        home_xg_against: Optional[float] = None,
        away_xg_for: Optional[float] = None,
        away_xg_against: Optional[float] = None,
        # Optional XGBoost features (would come from feature builder)
        xgboost_probs: Optional[tuple[float, float, float]] = None,
        # LLM adjustments
        llm_adjustments: Optional[LLMAdjustments] = None,
        # Bookmaker odds for value calculation
        odds_home: Optional[float] = None,
        odds_draw: Optional[float] = None,
        odds_away: Optional[float] = None,
    ) -> EnsemblePrediction:
        """
        Make ensemble prediction combining all models.

        Args:
            home_attack: Home team avg goals scored at home
            home_defense: Home team avg goals conceded at home
            away_attack: Away team avg goals scored away
            away_defense: Away team avg goals conceded away
            home_elo: Home team ELO rating
            away_elo: Away team ELO rating
            home_xg_for: Home team avg xG for (optional)
            home_xg_against: Home team avg xG against (optional)
            away_xg_for: Away team avg xG for (optional)
            away_xg_against: Away team avg xG against (optional)
            xgboost_probs: XGBoost model predictions (optional)
            llm_adjustments: LLM-derived adjustments (optional)
            odds_home: Bookmaker odds for home win
            odds_draw: Bookmaker odds for draw
            odds_away: Bookmaker odds for away win

        Returns:
            EnsemblePrediction with combined probabilities
        """
        contributions: list[tuple[float, float, float, float]] = []

        # 1. Poisson model
        poisson_pred = self.poisson.predict(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
        )
        contributions.append((
            poisson_pred.home_win_prob,
            poisson_pred.draw_prob,
            poisson_pred.away_win_prob,
            self.WEIGHT_POISSON,
        ))
        poisson_contrib = ModelContribution(
            home_prob=poisson_pred.home_win_prob,
            draw_prob=poisson_pred.draw_prob,
            away_prob=poisson_pred.away_win_prob,
            weight=self.WEIGHT_POISSON,
        )

        # 2. ELO model
        elo_pred = self.elo.predict(home_elo, away_elo)
        contributions.append((
            elo_pred.home_win_prob,
            elo_pred.draw_prob,
            elo_pred.away_win_prob,
            self.WEIGHT_ELO,
        ))
        elo_contrib = ModelContribution(
            home_prob=elo_pred.home_win_prob,
            draw_prob=elo_pred.draw_prob,
            away_prob=elo_pred.away_win_prob,
            weight=self.WEIGHT_ELO,
        )

        # 3. xG model (if data available)
        xg_contrib = None
        if all([home_xg_for, home_xg_against, away_xg_for, away_xg_against]):
            xg_pred = self.poisson.predict_with_xg(
                home_xg_for=home_xg_for,  # type: ignore
                home_xg_against=home_xg_against,  # type: ignore
                away_xg_for=away_xg_for,  # type: ignore
                away_xg_against=away_xg_against,  # type: ignore
            )
            contributions.append((
                xg_pred.home_win_prob,
                xg_pred.draw_prob,
                xg_pred.away_win_prob,
                self.WEIGHT_XG,
            ))
            xg_contrib = ModelContribution(
                home_prob=xg_pred.home_win_prob,
                draw_prob=xg_pred.draw_prob,
                away_prob=xg_pred.away_win_prob,
                weight=self.WEIGHT_XG,
            )

        # 4. XGBoost model (if available)
        xgboost_contrib = None
        if xgboost_probs:
            contributions.append((
                xgboost_probs[0],
                xgboost_probs[1],
                xgboost_probs[2],
                self.WEIGHT_XGBOOST,
            ))
            xgboost_contrib = ModelContribution(
                home_prob=xgboost_probs[0],
                draw_prob=xgboost_probs[1],
                away_prob=xgboost_probs[2],
                weight=self.WEIGHT_XGBOOST,
            )

        # Weighted average
        total_weight = sum(c[3] for c in contributions)
        home_prob = sum(c[0] * c[3] for c in contributions) / total_weight
        draw_prob = sum(c[1] * c[3] for c in contributions) / total_weight
        away_prob = sum(c[2] * c[3] for c in contributions) / total_weight

        # Normalize
        home_prob, draw_prob, away_prob = self._normalize_probs(
            home_prob, draw_prob, away_prob
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
        confidence = self._calculate_confidence(home_prob, draw_prob, away_prob)

        # Calculate value if odds available
        value_score = None
        if recommended_bet == "home" and odds_home:
            value_score = self._calculate_value(home_prob, odds_home)
        elif recommended_bet == "draw" and odds_draw:
            value_score = self._calculate_value(draw_prob, odds_draw)
        elif recommended_bet == "away" and odds_away:
            value_score = self._calculate_value(away_prob, odds_away)

        # Expected goals from Poisson
        exp_home = poisson_pred.expected_home_goals
        exp_away = poisson_pred.expected_away_goals

        return EnsemblePrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            recommended_bet=recommended_bet,  # type: ignore
            confidence=confidence,
            value_score=value_score,
            poisson_contribution=poisson_contrib,
            elo_contribution=elo_contrib,
            xg_contribution=xg_contrib,
            xgboost_contribution=xgboost_contrib,
            llm_adjustments=llm_adjustments,
            expected_home_goals=exp_home,
            expected_away_goals=exp_away,
        )


# Default instance
ensemble_predictor = EnsemblePredictor()
