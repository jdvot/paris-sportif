"""Tennis ensemble predictor with multi-model approach.

Combines:
- Surface-specific ELO (30%)
- Ranking Bradley-Terry (25%)
- Form/Momentum model (25%)
- Statistical baseline (20%)

Returns model_contributions, model_agreement, uncertainty, and multi-markets.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TennisModelContribution:
    """Individual model's contribution."""

    name: str
    player1_prob: float
    player2_prob: float
    weight: float
    confidence: float = 0.5


@dataclass
class TennisMultiMarkets:
    """Multi-market predictions for tennis."""

    over_2_5_sets: float = 0.5  # Probability match goes 3+ sets
    under_2_5_sets: float = 0.5
    set_handicap_minus_1_5: float = 0.5  # Favorite wins 2-0
    first_set_winner_p1: float = 0.5


@dataclass
class TennisEnsemblePrediction:
    """Final tennis ensemble prediction."""

    player1_prob: float
    player2_prob: float
    predicted_winner: int  # 1 or 2
    confidence: float
    model_contributions: list[TennisModelContribution] = field(default_factory=list)
    model_agreement: float = 0.0
    uncertainty: float = 0.0
    multi_markets: TennisMultiMarkets = field(default_factory=TennisMultiMarkets)
    value_score: float | None = None
    model_details: dict[str, Any] = field(default_factory=dict)


# Weights
W_ELO = 0.30
W_RANKING = 0.25
W_FORM = 0.25
W_STATISTICAL = 0.20


def _elo_model(p1_elo: float, p2_elo: float, surface: str) -> tuple[float, float]:
    """Surface-specific ELO probability."""
    elo_diff = p1_elo - p2_elo
    p1 = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
    # Surface specialist bonus
    if p1_elo > 1600 and p2_elo <= 1600:
        p1 += 0.03
    elif p2_elo > 1600 and p1_elo <= 1600:
        p1 -= 0.03
    p1 = max(0.05, min(0.95, p1))
    return p1, 1.0 - p1


def _ranking_model(p1_ranking: int | None, p2_ranking: int | None) -> tuple[float, float]:
    """Bradley-Terry model based on ATP/WTA rankings."""
    r1 = p1_ranking or 500
    r2 = p2_ranking or 500
    # Convert ranking to strength (lower ranking = stronger)
    # Use log scale: strength = log(max_rank / rank)
    max_rank = 1000
    s1 = math.log(max_rank / max(r1, 1))
    s2 = math.log(max_rank / max(r2, 1))
    p1 = s1 / (s1 + s2) if (s1 + s2) > 0 else 0.5
    # Top 10 vs outside 50 bonus
    if r1 <= 10 and r2 > 50:
        p1 += 0.05
    elif r2 <= 10 and r1 > 50:
        p1 -= 0.05
    p1 = max(0.05, min(0.95, p1))
    return p1, 1.0 - p1


def _form_model(p1_win_rate: float, p2_win_rate: float) -> tuple[float, float]:
    """Form/momentum model based on recent win rates."""
    if p1_win_rate <= 0 and p2_win_rate <= 0:
        return 0.5, 0.5
    diff = p1_win_rate - p2_win_rate
    # Sigmoid transformation for smoother probabilities
    p1 = 1.0 / (1.0 + math.exp(-diff * 3.0))
    p1 = max(0.05, min(0.95, p1))
    return p1, 1.0 - p1


def _statistical_model(
    p1_elo: float,
    p2_elo: float,
    p1_ranking: int | None,
    p2_ranking: int | None,
    p1_win_rate: float,
    p2_win_rate: float,
) -> tuple[float, float]:
    """Combined statistical baseline (simple average of signals)."""
    signals: list[float] = []
    # ELO signal
    elo_diff = p1_elo - p2_elo
    signals.append(1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0)))
    # Ranking signal
    r1 = p1_ranking or 200
    r2 = p2_ranking or 200
    if r1 + r2 > 0:
        signals.append(r2 / (r1 + r2))
    # Win rate signal
    if p1_win_rate > 0 or p2_win_rate > 0:
        total = p1_win_rate + p2_win_rate
        signals.append(p1_win_rate / total if total > 0 else 0.5)
    p1 = sum(signals) / len(signals) if signals else 0.5
    p1 = max(0.05, min(0.95, p1))
    return p1, 1.0 - p1


def _compute_multi_markets(p1_prob: float, p1_elo: float, p2_elo: float) -> TennisMultiMarkets:
    """Compute multi-market probabilities."""
    # Over 2.5 sets = match goes to 3 sets
    # Closer match = more likely to go 3 sets
    closeness = 1.0 - abs(p1_prob - 0.5) * 2.0  # 0 (one-sided) to 1 (even)
    over_2_5 = 0.30 + closeness * 0.40  # Range: 30% to 70%

    # Elo difference also impacts: big gap = less likely 3 sets
    elo_gap = abs(p1_elo - p2_elo)
    if elo_gap > 200:
        over_2_5 *= 0.8
    elif elo_gap < 50:
        over_2_5 = min(over_2_5 * 1.1, 0.75)

    over_2_5 = max(0.15, min(0.80, over_2_5))
    under_2_5 = 1.0 - over_2_5

    # Set handicap -1.5 (favorite wins 2-0) = under 2.5 sets AND favorite wins
    favorite_prob = max(p1_prob, 1.0 - p1_prob)
    handicap = under_2_5 * favorite_prob

    # First set winner ~ slightly correlated with match winner but less certain
    first_set_p1 = p1_prob * 0.85 + 0.5 * 0.15  # Regress toward 50%

    return TennisMultiMarkets(
        over_2_5_sets=round(over_2_5, 4),
        under_2_5_sets=round(under_2_5, 4),
        set_handicap_minus_1_5=round(handicap, 4),
        first_set_winner_p1=round(first_set_p1, 4),
    )


def predict_tennis_ensemble(
    player1_elo: float,
    player2_elo: float,
    player1_ranking: int | None = None,
    player2_ranking: int | None = None,
    player1_win_rate: float = 0.5,
    player2_win_rate: float = 0.5,
    surface: str = "hard",
    odds_player1: float | None = None,
    odds_player2: float | None = None,
) -> TennisEnsemblePrediction:
    """Run the tennis ensemble predictor.

    Returns prediction with model contributions, agreement, uncertainty,
    and multi-market probabilities.
    """
    # Run each model
    elo_p1, elo_p2 = _elo_model(player1_elo, player2_elo, surface)
    rank_p1, rank_p2 = _ranking_model(player1_ranking, player2_ranking)
    form_p1, form_p2 = _form_model(player1_win_rate, player2_win_rate)
    stat_p1, stat_p2 = _statistical_model(
        player1_elo,
        player2_elo,
        player1_ranking,
        player2_ranking,
        player1_win_rate,
        player2_win_rate,
    )

    contributions = [
        TennisModelContribution("Surface ELO", elo_p1, elo_p2, W_ELO, 0.7),
        TennisModelContribution("Ranking B-T", rank_p1, rank_p2, W_RANKING, 0.6),
        TennisModelContribution("Form/Momentum", form_p1, form_p2, W_FORM, 0.5),
        TennisModelContribution("Statistical", stat_p1, stat_p2, W_STATISTICAL, 0.5),
    ]

    # Weighted average
    p1_prob = sum(c.player1_prob * c.weight for c in contributions)
    p2_prob = sum(c.player2_prob * c.weight for c in contributions)

    # Normalize
    total = p1_prob + p2_prob
    if total > 0:
        p1_prob /= total
        p2_prob /= total
    else:
        p1_prob, p2_prob = 0.5, 0.5

    # Model agreement (how much models agree on the winner)
    winners = [1 if c.player1_prob > 0.5 else 2 for c in contributions]
    majority = max(winners.count(1), winners.count(2))
    model_agreement = majority / len(contributions)

    # Uncertainty (variance across models)
    probs = [c.player1_prob for c in contributions]
    mean_p = sum(probs) / len(probs)
    variance = sum((p - mean_p) ** 2 for p in probs) / len(probs)
    uncertainty = min(variance * 4.0, 1.0)  # Scale to 0-1

    # Confidence
    confidence = abs(p1_prob - 0.5) * 2.0 * model_agreement * (1.0 - uncertainty * 0.5)
    confidence = max(0.1, min(0.95, confidence))

    predicted_winner = 1 if p1_prob >= 0.5 else 2

    # Multi-markets
    multi_markets = _compute_multi_markets(p1_prob, player1_elo, player2_elo)

    # Value score (if odds available)
    value_score = None
    if odds_player1 and odds_player2:
        implied_p1 = 1.0 / odds_player1
        edge = p1_prob - implied_p1
        value_score = round(abs(edge) * confidence, 4)

    # Model details for storage
    model_details = {
        "model_contributions": [
            {"name": c.name, "p1": round(c.player1_prob, 4), "weight": c.weight}
            for c in contributions
        ],
        "model_agreement": round(model_agreement, 4),
        "uncertainty": round(uncertainty, 4),
        "multi_markets": {
            "over_2_5_sets": multi_markets.over_2_5_sets,
            "under_2_5_sets": multi_markets.under_2_5_sets,
            "set_handicap_minus_1_5": multi_markets.set_handicap_minus_1_5,
            "first_set_winner_p1": multi_markets.first_set_winner_p1,
        },
        "surface": surface,
    }

    logger.debug(
        f"Tennis ensemble: P1={p1_prob:.3f} P2={p2_prob:.3f} "
        f"conf={confidence:.3f} agreement={model_agreement:.2f}"
    )

    return TennisEnsemblePrediction(
        player1_prob=round(p1_prob, 4),
        player2_prob=round(p2_prob, 4),
        predicted_winner=predicted_winner,
        confidence=round(confidence, 4),
        model_contributions=contributions,
        model_agreement=round(model_agreement, 4),
        uncertainty=round(uncertainty, 4),
        multi_markets=multi_markets,
        value_score=value_score,
        model_details=model_details,
    )
