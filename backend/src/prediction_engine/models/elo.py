"""ELO Rating System for football teams.

The ELO system was originally developed for chess but works well for football.
It provides a relative strength rating that updates after each match.

Reference: https://www.eloratings.net/about
"""

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass
class ELOPrediction:
    """ELO-based prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    home_elo: float
    away_elo: float
    expected_home_score: float
    expected_away_score: float


class ELOSystem:
    """
    ELO Rating System adapted for football.

    Key differences from chess:
    - Accounts for draws (common in football)
    - Home advantage adjustment
    - Goal difference affects rating change magnitude
    """

    # Initial rating for new teams
    INITIAL_RATING = 1500.0

    # K-factor determines how much ratings change per match
    # Higher K = more volatile, lower K = more stable
    K_FACTOR = 20.0

    # Home advantage in ELO points (typically 50-100)
    HOME_ADVANTAGE = 100.0

    # Draw probability factor (higher = more draws expected)
    DRAW_FACTOR = 0.4

    def __init__(
        self,
        k_factor: float = 20.0,
        home_advantage: float = 100.0,
        draw_factor: float = 0.4,
    ):
        """
        Initialize ELO system.

        Args:
            k_factor: How much ratings change per match
            home_advantage: ELO points advantage for home team
            draw_factor: Factor affecting draw probability
        """
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.draw_factor = draw_factor

    def expected_score(
        self,
        rating_a: float,
        rating_b: float,
        is_a_home: bool = True,
    ) -> float:
        """
        Calculate expected score for team A.

        Uses logistic distribution (standard ELO formula).
        Result is between 0 and 1.

        Args:
            rating_a: Team A's ELO rating
            rating_b: Team B's ELO rating
            is_a_home: Whether team A is playing at home

        Returns:
            Expected score for team A (0 = loss, 0.5 = draw, 1 = win)
        """
        # Apply home advantage
        adjusted_a = rating_a + (self.home_advantage if is_a_home else 0)
        adjusted_b = rating_b + (0 if is_a_home else self.home_advantage)

        # Standard ELO formula
        return 1 / (1 + 10 ** ((adjusted_b - adjusted_a) / 400))

    def calculate_outcome_probabilities(
        self,
        home_rating: float,
        away_rating: float,
    ) -> Tuple[float, float, float]:
        """
        Calculate win/draw/loss probabilities.

        Football has three outcomes unlike chess (which rarely draws).
        We use the expected score to derive three-way probabilities.

        Args:
            home_rating: Home team's ELO rating
            away_rating: Away team's ELO rating

        Returns:
            Tuple of (home_win_prob, draw_prob, away_win_prob)
        """
        # Get expected score for home team
        exp_home = self.expected_score(home_rating, away_rating, is_a_home=True)

        # The draw probability is highest when teams are evenly matched
        # It decreases as the rating difference increases
        rating_diff = abs(home_rating + self.home_advantage - away_rating)

        # Draw probability peaks at ~25% for even teams, decreases with difference
        base_draw_prob = 0.25
        draw_reduction = min(0.20, rating_diff / 1000)  # Max 20% reduction
        draw_prob = max(0.10, base_draw_prob - draw_reduction)

        # Distribute remaining probability based on expected score
        remaining_prob = 1 - draw_prob
        home_win_prob = exp_home * remaining_prob
        away_win_prob = (1 - exp_home) * remaining_prob

        # Normalize
        total = home_win_prob + draw_prob + away_win_prob
        return (
            home_win_prob / total,
            draw_prob / total,
            away_win_prob / total,
        )

    def actual_score(
        self,
        result: Literal["home", "draw", "away"],
    ) -> Tuple[float, float]:
        """
        Convert match result to actual scores.

        Args:
            result: Match result from home team perspective

        Returns:
            Tuple of (home_score, away_score) where:
            - Win = 1.0
            - Draw = 0.5
            - Loss = 0.0
        """
        if result == "home":
            return 1.0, 0.0
        elif result == "away":
            return 0.0, 1.0
        else:
            return 0.5, 0.5

    def goal_difference_multiplier(self, goal_diff: int) -> float:
        """
        Calculate K-factor multiplier based on goal difference.

        Larger victories result in bigger rating changes.

        Args:
            goal_diff: Absolute goal difference

        Returns:
            Multiplier for K-factor (1.0 to ~1.75)
        """
        if goal_diff <= 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            # For 3+ goal differences
            return (11 + goal_diff) / 8

    def update_ratings(
        self,
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
    ) -> Tuple[float, float]:
        """
        Update ratings after a match.

        Args:
            home_rating: Home team's current rating
            away_rating: Away team's current rating
            home_goals: Goals scored by home team
            away_goals: Goals scored by away team

        Returns:
            Tuple of (new_home_rating, new_away_rating)
        """
        # Determine result
        if home_goals > away_goals:
            result: Literal["home", "draw", "away"] = "home"
        elif home_goals < away_goals:
            result = "away"
        else:
            result = "draw"

        # Get actual and expected scores
        actual_home, actual_away = self.actual_score(result)
        expected_home = self.expected_score(home_rating, away_rating, is_a_home=True)
        expected_away = 1 - expected_home

        # Goal difference multiplier
        goal_diff = abs(home_goals - away_goals)
        gd_mult = self.goal_difference_multiplier(goal_diff)

        # Calculate rating changes
        k = self.k_factor * gd_mult
        home_change = k * (actual_home - expected_home)
        away_change = k * (actual_away - expected_away)

        return (
            home_rating + home_change,
            away_rating + away_change,
        )

    def predict(
        self,
        home_rating: float,
        away_rating: float,
    ) -> ELOPrediction:
        """
        Make a prediction based on ELO ratings.

        Args:
            home_rating: Home team's ELO rating
            away_rating: Away team's ELO rating

        Returns:
            ELOPrediction with probabilities
        """
        home_prob, draw_prob, away_prob = self.calculate_outcome_probabilities(
            home_rating, away_rating
        )

        # Estimate expected goals based on rating difference
        # This is approximate - ELO doesn't directly predict goals
        rating_diff = (home_rating + self.home_advantage - away_rating) / 400

        # Base goals around 1.2-1.4, adjusted by rating difference
        base_goals = 1.3
        exp_home = base_goals + (rating_diff * 0.3)
        exp_away = base_goals - (rating_diff * 0.3)

        # Clamp to reasonable values
        exp_home = max(0.5, min(3.0, exp_home))
        exp_away = max(0.5, min(3.0, exp_away))

        return ELOPrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            home_elo=home_rating,
            away_elo=away_rating,
            expected_home_score=exp_home,
            expected_away_score=exp_away,
        )


# Default instance
elo_system = ELOSystem()
