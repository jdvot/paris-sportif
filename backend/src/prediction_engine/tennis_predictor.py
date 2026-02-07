"""Tennis prediction engine using surface-specific ELO.

No draw in tennis — binary outcome only (player 1 or player 2 wins).
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ELO threshold for surface specialist bonus
_SURFACE_SPECIALIST_ELO = 1600
_SPECIALIST_BONUS = 0.03  # +3% win probability

# Ranking tier bonus (top 10 vs outside top 50)
_TOP_10_VS_OUTSIDE_50_BONUS = 0.05  # +5%


@dataclass
class TennisPrediction:
    """Result of a tennis prediction."""

    player1_prob: float
    player2_prob: float
    confidence: float
    predicted_winner: int  # 1 or 2
    explanation: str


def predict_tennis(
    player1_elo: float,
    player2_elo: float,
    player1_ranking: int | None,
    player2_ranking: int | None,
    player1_win_rate: float,
    player2_win_rate: float,
    surface: str,
) -> TennisPrediction:
    """Predict a tennis match outcome using surface-specific ELO.

    Args:
        player1_elo: Player 1 ELO on the match surface
        player2_elo: Player 2 ELO on the match surface
        player1_ranking: Player 1 ATP/WTA ranking (or None)
        player2_ranking: Player 2 ATP/WTA ranking (or None)
        player1_win_rate: Player 1 win% YTD (0-1)
        player2_win_rate: Player 2 win% YTD (0-1)
        surface: Surface type (hard/clay/grass/indoor)

    Returns:
        TennisPrediction with probabilities and explanation
    """
    # Base ELO probability
    elo_diff = player1_elo - player2_elo
    p1_prob = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))

    # Ranking bonus: top 10 vs outside top 50
    if player1_ranking and player2_ranking:
        if player1_ranking <= 10 and player2_ranking > 50:
            p1_prob += _TOP_10_VS_OUTSIDE_50_BONUS
        elif player2_ranking <= 10 and player1_ranking > 50:
            p1_prob -= _TOP_10_VS_OUTSIDE_50_BONUS

    # Surface specialist bonus
    if player1_elo > _SURFACE_SPECIALIST_ELO and player2_elo <= _SURFACE_SPECIALIST_ELO:
        p1_prob += _SPECIALIST_BONUS
    elif player2_elo > _SURFACE_SPECIALIST_ELO and player1_elo <= _SURFACE_SPECIALIST_ELO:
        p1_prob -= _SPECIALIST_BONUS

    # Win rate factor (small adjustment based on form)
    if player1_win_rate > 0 and player2_win_rate > 0:
        form_diff = (player1_win_rate - player2_win_rate) * 0.1
        p1_prob += form_diff

    # Clamp to valid range
    p1_prob = max(0.05, min(0.95, p1_prob))
    p2_prob = 1.0 - p1_prob

    # Confidence: how asymmetric the prediction is (0 at 50/50, 1 at 100/0)
    confidence = abs(p1_prob - 0.5) * 2.0

    predicted_winner = 1 if p1_prob >= 0.5 else 2
    winner_prob = p1_prob if predicted_winner == 1 else p2_prob

    # Build explanation
    p1_rank_str = f"#{player1_ranking}" if player1_ranking else "non classé"
    p2_rank_str = f"#{player2_ranking}" if player2_ranking else "non classé"

    explanation = (
        f"Joueur {'1' if predicted_winner == 1 else '2'} favori "
        f"({winner_prob:.0%}) avec un ELO {surface} de "
        f"{player1_elo if predicted_winner == 1 else player2_elo:.0f}, "
        f"classé {p1_rank_str if predicted_winner == 1 else p2_rank_str} mondial. "
        f"Win rate YTD: {player1_win_rate:.0%} vs {player2_win_rate:.0%}."
    )

    logger.debug(
        f"Tennis prediction: P1={p1_prob:.3f} P2={p2_prob:.3f} conf={confidence:.3f} "
        f"(ELO {player1_elo:.0f} vs {player2_elo:.0f} on {surface})"
    )

    return TennisPrediction(
        player1_prob=round(p1_prob, 4),
        player2_prob=round(p2_prob, 4),
        confidence=round(confidence, 4),
        predicted_winner=predicted_winner,
        explanation=explanation,
    )
