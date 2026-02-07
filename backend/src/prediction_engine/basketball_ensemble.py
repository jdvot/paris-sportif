"""Basketball (NBA) ensemble predictor with multi-model approach.

Combines:
- ELO + Home advantage (25%)
- Net Rating model (30%)
- Poisson Score model (25%)
- Form/Momentum model (20%)

Returns model_contributions, model_agreement, uncertainty, and multi-markets.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Constants
_HOME_ADV_ELO = 75.0
_B2B_PENALTY = 0.03
_AVG_TEAM_SCORE = 112.0


@dataclass
class NBAModelContribution:
    """Individual model's contribution."""

    name: str
    home_prob: float
    away_prob: float
    weight: float
    confidence: float = 0.5


@dataclass
class NBAMultiMarkets:
    """Multi-market predictions for NBA."""

    over_210_5: float = 0.5
    under_210_5: float = 0.5
    over_220_5: float = 0.5
    under_220_5: float = 0.5
    spread_home_minus_5_5: float = 0.5  # Home wins by 6+
    spread_home_minus_9_5: float = 0.5  # Home wins by 10+


@dataclass
class NBAEnsemblePrediction:
    """Final NBA ensemble prediction."""

    home_prob: float
    away_prob: float
    predicted_winner: str  # "home" or "away"
    confidence: float
    expected_home_score: float
    expected_away_score: float
    expected_total: float
    model_contributions: list[NBAModelContribution] = field(default_factory=list)
    model_agreement: float = 0.0
    uncertainty: float = 0.0
    multi_markets: NBAMultiMarkets = field(default_factory=NBAMultiMarkets)
    value_score: float | None = None
    model_details: dict[str, Any] = field(default_factory=dict)


# Weights
W_ELO = 0.25
W_NET_RATING = 0.30
W_POISSON = 0.25
W_FORM = 0.20


def _elo_model(
    home_elo: float,
    away_elo: float,
    b2b_home: bool,
    b2b_away: bool,
) -> tuple[float, float]:
    """ELO model with home advantage and B2B penalty."""
    elo_diff = home_elo - away_elo + _HOME_ADV_ELO
    home_p = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
    if b2b_home:
        home_p -= _B2B_PENALTY
    if b2b_away:
        home_p += _B2B_PENALTY
    home_p = max(0.05, min(0.95, home_p))
    return home_p, 1.0 - home_p


def _net_rating_model(
    home_off: float | None,
    home_def: float | None,
    away_off: float | None,
    away_def: float | None,
    home_elo: float,
    away_elo: float,
) -> tuple[float, float]:
    """Net rating model using offensive/defensive ratings."""
    if all(v is not None for v in [home_off, home_def, away_off, away_def]):
        home_net = (home_off or 0) - (home_def or 0)
        away_net = (away_off or 0) - (away_def or 0)
        net_diff = home_net - away_net
        # Add small home advantage (~3 points in net rating)
        net_diff += 3.0
        # Convert to probability: ~10 net rating diff ≈ 75% win prob
        home_p = 1.0 / (1.0 + math.exp(-net_diff / 10.0))
    else:
        # Fallback to ELO
        elo_diff = home_elo - away_elo + _HOME_ADV_ELO
        home_p = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
    home_p = max(0.05, min(0.95, home_p))
    return home_p, 1.0 - home_p


def _poisson_score_model(
    home_off: float | None,
    home_def: float | None,
    away_off: float | None,
    away_def: float | None,
    home_pace: float | None,
    away_pace: float | None,
) -> tuple[float, float, float, float]:
    """Poisson-based score model. Returns (home_prob, away_prob, exp_home, exp_away)."""
    # Expected scores
    avg_pace = _AVG_TEAM_SCORE
    if home_pace is not None and away_pace is not None:
        avg_pace = (home_pace + away_pace) / 2.0
    pace_factor = avg_pace / 100.0 if avg_pace > 0 else 1.0

    if home_off is not None and away_def is not None:
        exp_home = (home_off + away_def) / 2.0 * pace_factor
    else:
        exp_home = _AVG_TEAM_SCORE

    if away_off is not None and home_def is not None:
        exp_away = (away_off + home_def) / 2.0 * pace_factor
    else:
        exp_away = _AVG_TEAM_SCORE

    # Home advantage adjustment
    exp_home *= 1.015
    exp_away *= 0.985

    # Win probability from expected score difference
    score_diff = exp_home - exp_away
    # NBA: ~12 point standard deviation in score differential
    home_p = 1.0 / (1.0 + math.exp(-score_diff / 12.0))
    home_p = max(0.05, min(0.95, home_p))
    return home_p, 1.0 - home_p, exp_home, exp_away


def _form_model(home_wr: float, away_wr: float) -> tuple[float, float]:
    """Form/momentum model based on win rates."""
    if home_wr <= 0 and away_wr <= 0:
        return 0.5, 0.5
    diff = home_wr - away_wr
    # Small home bonus
    diff += 0.05
    home_p = 1.0 / (1.0 + math.exp(-diff * 3.0))
    home_p = max(0.05, min(0.95, home_p))
    return home_p, 1.0 - home_p


def _compute_multi_markets(exp_home: float, exp_away: float, home_prob: float) -> NBAMultiMarkets:
    """Compute multi-market probabilities for NBA."""
    exp_total = exp_home + exp_away
    exp_diff = exp_home - exp_away

    # Over/Under using normal approximation (std dev ~22 for NBA totals)
    std_total = 22.0
    over_210_5 = 1.0 / (1.0 + math.exp(-(exp_total - 210.5) / (std_total * 0.6)))
    over_220_5 = 1.0 / (1.0 + math.exp(-(exp_total - 220.5) / (std_total * 0.6)))

    # Point spread (std dev ~12 for NBA point differential)
    std_diff = 12.0
    spread_5_5 = 1.0 / (1.0 + math.exp(-(exp_diff - 5.5) / (std_diff * 0.6)))
    spread_9_5 = 1.0 / (1.0 + math.exp(-(exp_diff - 9.5) / (std_diff * 0.6)))

    return NBAMultiMarkets(
        over_210_5=round(max(0.05, min(0.95, over_210_5)), 4),
        under_210_5=round(max(0.05, min(0.95, 1.0 - over_210_5)), 4),
        over_220_5=round(max(0.05, min(0.95, over_220_5)), 4),
        under_220_5=round(max(0.05, min(0.95, 1.0 - over_220_5)), 4),
        spread_home_minus_5_5=round(max(0.05, min(0.95, spread_5_5)), 4),
        spread_home_minus_9_5=round(max(0.05, min(0.95, spread_9_5)), 4),
    )


def predict_nba_ensemble(
    home_elo: float,
    away_elo: float,
    home_off_rating: float | None = None,
    home_def_rating: float | None = None,
    away_off_rating: float | None = None,
    away_def_rating: float | None = None,
    home_pace: float | None = None,
    away_pace: float | None = None,
    is_back_to_back_home: bool = False,
    is_back_to_back_away: bool = False,
    home_win_rate: float = 0.5,
    away_win_rate: float = 0.5,
    odds_home: float | None = None,
    odds_away: float | None = None,
) -> NBAEnsemblePrediction:
    """Run the NBA ensemble predictor.

    Returns prediction with model contributions, agreement, uncertainty,
    expected scores, and multi-market probabilities.
    """
    # Run each model
    elo_h, elo_a = _elo_model(home_elo, away_elo, is_back_to_back_home, is_back_to_back_away)
    net_h, net_a = _net_rating_model(
        home_off_rating,
        home_def_rating,
        away_off_rating,
        away_def_rating,
        home_elo,
        away_elo,
    )
    poisson_h, poisson_a, exp_home, exp_away = _poisson_score_model(
        home_off_rating,
        home_def_rating,
        away_off_rating,
        away_def_rating,
        home_pace,
        away_pace,
    )
    form_h, form_a = _form_model(home_win_rate, away_win_rate)

    # B2B adjustments to expected scores
    if is_back_to_back_home:
        exp_home *= 0.97
    if is_back_to_back_away:
        exp_away *= 0.97

    contributions = [
        NBAModelContribution("ELO + Home", elo_h, elo_a, W_ELO, 0.6),
        NBAModelContribution("Net Rating", net_h, net_a, W_NET_RATING, 0.7),
        NBAModelContribution("Poisson Score", poisson_h, poisson_a, W_POISSON, 0.6),
        NBAModelContribution("Form/Momentum", form_h, form_a, W_FORM, 0.5),
    ]

    # Weighted average
    home_prob = sum(c.home_prob * c.weight for c in contributions)
    away_prob = sum(c.away_prob * c.weight for c in contributions)

    # Normalize
    total = home_prob + away_prob
    if total > 0:
        home_prob /= total
        away_prob /= total
    else:
        home_prob, away_prob = 0.5, 0.5

    # Model agreement
    winners = ["home" if c.home_prob > 0.5 else "away" for c in contributions]
    majority = max(winners.count("home"), winners.count("away"))
    model_agreement = majority / len(contributions)

    # Uncertainty
    probs = [c.home_prob for c in contributions]
    mean_p = sum(probs) / len(probs)
    variance = sum((p - mean_p) ** 2 for p in probs) / len(probs)
    uncertainty = min(variance * 4.0, 1.0)

    # Confidence
    confidence = abs(home_prob - 0.5) * 2.0 * model_agreement * (1.0 - uncertainty * 0.5)
    confidence = max(0.1, min(0.95, confidence))

    predicted_winner = "home" if home_prob >= 0.5 else "away"
    expected_total = exp_home + exp_away

    # Multi-markets
    multi_markets = _compute_multi_markets(exp_home, exp_away, home_prob)

    # Value score
    value_score = None
    if odds_home and odds_away:
        implied_h = 1.0 / odds_home
        edge = home_prob - implied_h
        value_score = round(abs(edge) * confidence, 4)

    # Model details for JSON storage
    model_details = {
        "model_contributions": [
            {"name": c.name, "home": round(c.home_prob, 4), "weight": c.weight}
            for c in contributions
        ],
        "model_agreement": round(model_agreement, 4),
        "uncertainty": round(uncertainty, 4),
        "expected_scores": {
            "home": round(exp_home, 1),
            "away": round(exp_away, 1),
            "total": round(expected_total, 1),
        },
        "multi_markets": {
            "over_210_5": multi_markets.over_210_5,
            "under_210_5": multi_markets.under_210_5,
            "over_220_5": multi_markets.over_220_5,
            "under_220_5": multi_markets.under_220_5,
            "spread_home_minus_5_5": multi_markets.spread_home_minus_5_5,
            "spread_home_minus_9_5": multi_markets.spread_home_minus_9_5,
        },
        "b2b": {
            "home": is_back_to_back_home,
            "away": is_back_to_back_away,
        },
    }

    logger.debug(
        f"NBA ensemble: home={home_prob:.3f} away={away_prob:.3f} "
        f"conf={confidence:.3f} total={expected_total:.1f}"
    )

    return NBAEnsemblePrediction(
        home_prob=round(home_prob, 4),
        away_prob=round(away_prob, 4),
        predicted_winner=predicted_winner,
        confidence=round(confidence, 4),
        expected_home_score=round(exp_home, 1),
        expected_away_score=round(exp_away, 1),
        expected_total=round(expected_total, 1),
        model_contributions=contributions,
        model_agreement=round(model_agreement, 4),
        uncertainty=round(uncertainty, 4),
        multi_markets=multi_markets,
        value_score=value_score,
        model_details=model_details,
    )
