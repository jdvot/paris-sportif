"""Multi-markets prediction module.

Calculates probabilities for various betting markets:
- Over/Under (1.5, 2.5, 3.5 goals)
- BTTS (Both Teams To Score)
- Double Chance (1X, X2, 12)
- Correct Score (top probabilities)

Uses Poisson distribution for goal-based markets.
"""

import math
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OverUnderPrediction:
    """Over/Under market prediction."""

    line: float  # 1.5, 2.5, 3.5, etc.
    over_prob: float
    under_prob: float
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    over_value: Optional[float] = None  # Value vs bookmaker
    under_value: Optional[float] = None
    recommended: str = "over"  # "over" or "under"


@dataclass
class BTTSPrediction:
    """Both Teams To Score prediction."""

    yes_prob: float
    no_prob: float
    yes_odds: Optional[float] = None
    no_odds: Optional[float] = None
    yes_value: Optional[float] = None
    no_value: Optional[float] = None
    recommended: str = "yes"  # "yes" or "no"


@dataclass
class DoubleChancePrediction:
    """Double Chance market prediction."""

    home_or_draw_prob: float  # 1X
    away_or_draw_prob: float  # X2
    home_or_away_prob: float  # 12 (no draw)
    home_or_draw_odds: Optional[float] = None
    away_or_draw_odds: Optional[float] = None
    home_or_away_odds: Optional[float] = None
    recommended: str = "1X"  # "1X", "X2", or "12"


@dataclass
class CorrectScorePrediction:
    """Correct Score prediction with top probabilities."""

    scores: dict[str, float]  # {"1-0": 0.12, "2-1": 0.10, ...}
    most_likely: str  # e.g., "1-1"
    most_likely_prob: float


@dataclass
class MultiMarketsPrediction:
    """Complete multi-markets prediction."""

    # Over/Under markets
    over_under_15: OverUnderPrediction
    over_under_25: OverUnderPrediction
    over_under_35: OverUnderPrediction

    # BTTS
    btts: BTTSPrediction

    # Double Chance
    double_chance: DoubleChancePrediction

    # Correct Score (top 5)
    correct_score: CorrectScorePrediction

    # Expected goals
    expected_home_goals: float
    expected_away_goals: float
    expected_total_goals: float


def _poisson_prob(k: int, lambda_val: float) -> float:
    """Calculate Poisson probability P(X = k) = (λ^k * e^-λ) / k!"""
    if lambda_val <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)


def _calculate_score_matrix(
    home_goals_exp: float,
    away_goals_exp: float,
    max_goals: int = 7,
) -> list[list[float]]:
    """
    Calculate probability matrix for all score combinations.

    Returns a matrix where matrix[home][away] = probability of that score.
    """
    matrix = []
    for home in range(max_goals + 1):
        row = []
        for away in range(max_goals + 1):
            prob = _poisson_prob(home, home_goals_exp) * _poisson_prob(away, away_goals_exp)
            row.append(prob)
        matrix.append(row)
    return matrix


def _calculate_over_under(
    score_matrix: list[list[float]],
    line: float,
) -> OverUnderPrediction:
    """Calculate Over/Under probabilities from score matrix."""
    max_goals = len(score_matrix) - 1
    over_prob = 0.0
    under_prob = 0.0

    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            total = home + away
            prob = score_matrix[home][away]
            if total > line:
                over_prob += prob
            elif total < line:
                under_prob += prob
            # Exactly on the line would be push (we ignore for simplicity)

    # Normalize
    total_prob = over_prob + under_prob
    if total_prob > 0:
        over_prob = over_prob / total_prob
        under_prob = under_prob / total_prob
    else:
        over_prob = 0.5
        under_prob = 0.5

    recommended = "over" if over_prob > under_prob else "under"

    return OverUnderPrediction(
        line=line,
        over_prob=round(over_prob, 4),
        under_prob=round(under_prob, 4),
        recommended=recommended,
    )


def _calculate_btts(score_matrix: list[list[float]]) -> BTTSPrediction:
    """Calculate Both Teams To Score probabilities."""
    max_goals = len(score_matrix) - 1
    yes_prob = 0.0
    no_prob = 0.0

    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            prob = score_matrix[home][away]
            if home > 0 and away > 0:
                yes_prob += prob
            else:
                no_prob += prob

    # Normalize
    total = yes_prob + no_prob
    if total > 0:
        yes_prob = yes_prob / total
        no_prob = no_prob / total
    else:
        yes_prob = 0.5
        no_prob = 0.5

    recommended = "yes" if yes_prob > no_prob else "no"

    return BTTSPrediction(
        yes_prob=round(yes_prob, 4),
        no_prob=round(no_prob, 4),
        recommended=recommended,
    )


def _calculate_double_chance(
    home_prob: float,
    draw_prob: float,
    away_prob: float,
) -> DoubleChancePrediction:
    """Calculate Double Chance probabilities."""
    # 1X = Home or Draw
    home_or_draw = home_prob + draw_prob
    # X2 = Draw or Away
    away_or_draw = draw_prob + away_prob
    # 12 = Home or Away (no draw)
    home_or_away = home_prob + away_prob

    # Determine recommended
    probs = {
        "1X": home_or_draw,
        "X2": away_or_draw,
        "12": home_or_away,
    }
    recommended = max(probs, key=probs.get)  # type: ignore

    return DoubleChancePrediction(
        home_or_draw_prob=round(home_or_draw, 4),
        away_or_draw_prob=round(away_or_draw, 4),
        home_or_away_prob=round(home_or_away, 4),
        recommended=recommended,
    )


def _calculate_correct_score(
    score_matrix: list[list[float]],
    top_n: int = 6,
) -> CorrectScorePrediction:
    """Calculate top N most likely correct scores."""
    max_goals = len(score_matrix) - 1

    # Build list of (score, probability)
    scores = []
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            score_str = f"{home}-{away}"
            prob = score_matrix[home][away]
            scores.append((score_str, prob))

    # Sort by probability descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Take top N
    top_scores = {score: round(prob, 4) for score, prob in scores[:top_n]}
    most_likely = scores[0][0]
    most_likely_prob = round(scores[0][1], 4)

    return CorrectScorePrediction(
        scores=top_scores,
        most_likely=most_likely,
        most_likely_prob=most_likely_prob,
    )


def _calculate_value(prob: float, odds: Optional[float]) -> Optional[float]:
    """Calculate value score: (prob * odds) - 1."""
    if odds is None or odds <= 1:
        return None
    value = (prob * odds) - 1
    return round(value, 4)


def _estimate_fair_odds(prob: float) -> Optional[float]:
    """Estimate fair odds from probability with 5% margin."""
    if prob <= 0 or prob >= 1:
        return None
    # Fair odds = 1/prob, with 5% bookmaker margin
    fair_odds = 1 / prob * 0.95
    return round(fair_odds, 2)


class MultiMarketsPredictor:
    """
    Multi-markets prediction calculator.

    Uses expected goals (from Poisson/Dixon-Coles) to calculate
    probabilities for various betting markets.
    """

    def predict(
        self,
        expected_home_goals: float,
        expected_away_goals: float,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        # Optional bookmaker odds for value calculation
        odds_over_25: Optional[float] = None,
        odds_under_25: Optional[float] = None,
        odds_btts_yes: Optional[float] = None,
        odds_btts_no: Optional[float] = None,
    ) -> MultiMarketsPrediction:
        """
        Calculate multi-markets predictions.

        Args:
            expected_home_goals: Expected goals for home team
            expected_away_goals: Expected goals for away team
            home_win_prob: Probability of home win (1X2)
            draw_prob: Probability of draw (1X2)
            away_win_prob: Probability of away win (1X2)
            odds_*: Optional bookmaker odds for value calculation

        Returns:
            MultiMarketsPrediction with all market predictions
        """
        # Ensure reasonable expected goals
        exp_home = max(0.1, min(5.0, expected_home_goals))
        exp_away = max(0.1, min(5.0, expected_away_goals))

        # Calculate score matrix
        score_matrix = _calculate_score_matrix(exp_home, exp_away)

        # Over/Under markets
        ou_15 = _calculate_over_under(score_matrix, 1.5)
        ou_25 = _calculate_over_under(score_matrix, 2.5)
        ou_35 = _calculate_over_under(score_matrix, 3.5)

        # Add odds and value if available
        if odds_over_25:
            ou_25.over_odds = odds_over_25
            ou_25.over_value = _calculate_value(ou_25.over_prob, odds_over_25)
        else:
            ou_25.over_odds = _estimate_fair_odds(ou_25.over_prob)

        if odds_under_25:
            ou_25.under_odds = odds_under_25
            ou_25.under_value = _calculate_value(ou_25.under_prob, odds_under_25)
        else:
            ou_25.under_odds = _estimate_fair_odds(ou_25.under_prob)

        # Estimate odds for other O/U lines
        ou_15.over_odds = _estimate_fair_odds(ou_15.over_prob)
        ou_15.under_odds = _estimate_fair_odds(ou_15.under_prob)
        ou_35.over_odds = _estimate_fair_odds(ou_35.over_prob)
        ou_35.under_odds = _estimate_fair_odds(ou_35.under_prob)

        # BTTS
        btts = _calculate_btts(score_matrix)
        if odds_btts_yes:
            btts.yes_odds = odds_btts_yes
            btts.yes_value = _calculate_value(btts.yes_prob, odds_btts_yes)
        else:
            btts.yes_odds = _estimate_fair_odds(btts.yes_prob)

        if odds_btts_no:
            btts.no_odds = odds_btts_no
            btts.no_value = _calculate_value(btts.no_prob, odds_btts_no)
        else:
            btts.no_odds = _estimate_fair_odds(btts.no_prob)

        # Double Chance
        double_chance = _calculate_double_chance(home_win_prob, draw_prob, away_win_prob)
        double_chance.home_or_draw_odds = _estimate_fair_odds(double_chance.home_or_draw_prob)
        double_chance.away_or_draw_odds = _estimate_fair_odds(double_chance.away_or_draw_prob)
        double_chance.home_or_away_odds = _estimate_fair_odds(double_chance.home_or_away_prob)

        # Correct Score
        correct_score = _calculate_correct_score(score_matrix)

        return MultiMarketsPrediction(
            over_under_15=ou_15,
            over_under_25=ou_25,
            over_under_35=ou_35,
            btts=btts,
            double_chance=double_chance,
            correct_score=correct_score,
            expected_home_goals=round(exp_home, 2),
            expected_away_goals=round(exp_away, 2),
            expected_total_goals=round(exp_home + exp_away, 2),
        )


# Default instance
multi_markets_predictor = MultiMarketsPredictor()


def get_multi_markets_prediction(
    expected_home_goals: float,
    expected_away_goals: float,
    home_win_prob: float,
    draw_prob: float,
    away_win_prob: float,
    odds_over_25: Optional[float] = None,
    odds_under_25: Optional[float] = None,
    odds_btts_yes: Optional[float] = None,
    odds_btts_no: Optional[float] = None,
) -> MultiMarketsPrediction:
    """Convenience function to get multi-markets prediction."""
    return multi_markets_predictor.predict(
        expected_home_goals=expected_home_goals,
        expected_away_goals=expected_away_goals,
        home_win_prob=home_win_prob,
        draw_prob=draw_prob,
        away_win_prob=away_win_prob,
        odds_over_25=odds_over_25,
        odds_under_25=odds_under_25,
        odds_btts_yes=odds_btts_yes,
        odds_btts_no=odds_btts_no,
    )
