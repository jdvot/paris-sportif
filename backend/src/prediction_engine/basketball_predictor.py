"""Basketball prediction engine using ELO + offensive/defensive ratings.

No draw in NBA — binary outcome only (home or away wins).
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# NBA home advantage is ~60% historically → ~75 ELO points
_HOME_ADV_ELO = 75.0

# Back-to-back penalty
_B2B_PENALTY = 0.03  # -3% win probability

# Average NBA team score (for expected total estimation)
_AVG_TEAM_SCORE = 112.0


@dataclass
class BasketballPrediction:
    """Result of a basketball prediction."""

    home_prob: float
    away_prob: float
    confidence: float
    predicted_winner: str  # "home" or "away"
    expected_home_score: float
    expected_away_score: float
    explanation: str


def predict_basketball(
    home_elo: float,
    away_elo: float,
    home_off_rating: float | None,
    home_def_rating: float | None,
    away_off_rating: float | None,
    away_def_rating: float | None,
    home_pace: float | None,
    away_pace: float | None,
    is_back_to_back_home: bool,
    is_back_to_back_away: bool,
    home_win_rate: float,
    away_win_rate: float,
) -> BasketballPrediction:
    """Predict an NBA game using ELO + offensive/defensive ratings.

    Args:
        home_elo: Home team ELO rating
        away_elo: Away team ELO rating
        home_off_rating: Home offensive rating (points per 100 possessions)
        home_def_rating: Home defensive rating (points allowed per 100 possessions)
        away_off_rating: Away offensive rating
        away_def_rating: Away defensive rating
        home_pace: Home team pace (possessions per game)
        away_pace: Away team pace
        is_back_to_back_home: Home team playing back-to-back
        is_back_to_back_away: Away team playing back-to-back
        home_win_rate: Home team season win rate (0-1)
        away_win_rate: Away team season win rate (0-1)

    Returns:
        BasketballPrediction with probabilities and expected scores
    """
    # Base ELO probability with home advantage
    elo_diff = home_elo - away_elo + _HOME_ADV_ELO
    home_prob = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))

    # Net rating adjustment (offensive - defensive, normalized)
    ratings = [home_off_rating, home_def_rating, away_off_rating, away_def_rating]
    if all(v is not None for v in ratings):
        home_net = (home_off_rating or 0) - (home_def_rating or 0)
        away_net = (away_off_rating or 0) - (away_def_rating or 0)
        net_diff = home_net - away_net
        # Convert net rating diff to probability adjustment (10 net rating ≈ 5%)
        rating_adj = net_diff * 0.005
        home_prob += rating_adj

    # Back-to-back penalty
    if is_back_to_back_home:
        home_prob -= _B2B_PENALTY
    if is_back_to_back_away:
        home_prob += _B2B_PENALTY

    # Win rate form factor (small weight)
    if home_win_rate > 0 and away_win_rate > 0:
        form_diff = (home_win_rate - away_win_rate) * 0.05
        home_prob += form_diff

    # Clamp
    home_prob = max(0.05, min(0.95, home_prob))
    away_prob = 1.0 - home_prob

    # Confidence: based on how decisive the prediction is
    confidence = abs(home_prob - 0.5) * 2.0

    predicted_winner = "home" if home_prob >= 0.5 else "away"

    # Expected score estimation
    avg_pace = _AVG_TEAM_SCORE
    if home_pace is not None and away_pace is not None:
        avg_pace = (home_pace + away_pace) / 2.0

    pace_factor = avg_pace / 100.0 if avg_pace > 0 else 1.0

    if home_off_rating is not None and away_def_rating is not None:
        expected_home_score = (home_off_rating + away_def_rating) / 2.0 * pace_factor
    else:
        expected_home_score = _AVG_TEAM_SCORE

    if away_off_rating is not None and home_def_rating is not None:
        expected_away_score = (away_off_rating + home_def_rating) / 2.0 * pace_factor
    else:
        expected_away_score = _AVG_TEAM_SCORE

    # B2B impact on expected score
    if is_back_to_back_home:
        expected_home_score *= 0.97
    if is_back_to_back_away:
        expected_away_score *= 0.97

    # Build explanation
    b2b_parts: list[str] = []
    if is_back_to_back_home:
        b2b_parts.append("domicile en back-to-back")
    if is_back_to_back_away:
        b2b_parts.append("extérieur en back-to-back")
    b2b_str = f" ({', '.join(b2b_parts)})" if b2b_parts else ""

    winner_label = "domicile" if predicted_winner == "home" else "extérieur"
    winner_prob = home_prob if predicted_winner == "home" else away_prob

    explanation = (
        f"Équipe {winner_label} favorite ({winner_prob:.0%}). "
        f"ELO: {home_elo:.0f} vs {away_elo:.0f} (avantage domicile +{_HOME_ADV_ELO:.0f}). "
        f"Score attendu: {expected_home_score:.0f}-{expected_away_score:.0f}."
        f"{b2b_str}"
    )

    logger.debug(
        f"NBA prediction: home={home_prob:.3f} away={away_prob:.3f} conf={confidence:.3f} "
        f"(ELO {home_elo:.0f} vs {away_elo:.0f})"
    )

    return BasketballPrediction(
        home_prob=round(home_prob, 4),
        away_prob=round(away_prob, 4),
        confidence=round(confidence, 4),
        predicted_winner=predicted_winner,
        expected_home_score=round(expected_home_score, 1),
        expected_away_score=round(expected_away_score, 1),
        explanation=explanation,
    )
