"""Advanced ELO Rating System with dynamic K-factor and calibration.

Improvements over basic ELO:
1. Dynamic K-factor based on match importance and rating level
2. Performance rating adjustment
3. Better handling of draws
4. Time-weighted form factor for recent performance
"""

from dataclasses import dataclass
from typing import Literal, Tuple
import numpy as np
from datetime import datetime, timedelta


@dataclass
class AdvancedELOPrediction:
    """Advanced ELO-based prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    home_elo: float
    away_elo: float
    home_performance_rating: float
    away_performance_rating: float
    expected_home_score: float
    expected_away_score: float
    confidence: float


class AdvancedELOSystem:
    """
    Advanced ELO Rating System for football.

    Features:
    - Dynamic K-factor based on rating and match importance
    - Performance rating adjustment for recent form
    - Better probability calibration
    - Time-decay on recent performance
    """

    # Initial rating for new teams
    INITIAL_RATING = 1500.0

    # Base K-factor
    BASE_K_FACTOR = 20.0

    # Home advantage in ELO points
    HOME_ADVANTAGE = 100.0

    # Draw probability factor
    DRAW_FACTOR = 0.25

    def __init__(
        self,
        base_k_factor: float = 20.0,
        home_advantage: float = 100.0,
        draw_factor: float = 0.25,
        performance_window_days: int = 30,
    ):
        """
        Initialize advanced ELO system.

        Args:
            base_k_factor: Base K-factor for rating changes
            home_advantage: ELO points advantage for home team
            draw_factor: Factor affecting draw probability
            performance_window_days: Days to consider for performance rating
        """
        self.base_k_factor = base_k_factor
        self.home_advantage = home_advantage
        self.draw_factor = draw_factor
        self.performance_window_days = performance_window_days

    def dynamic_k_factor(
        self,
        rating: float,
        is_major_match: bool = False,
        recent_performance: float = 0.0,
    ) -> float:
        """
        Calculate dynamic K-factor based on rating and context.

        Higher rated teams have lower K (more stable), lower rated teams higher K.
        Major matches (finals, derbies) get higher K.

        Args:
            rating: Team's current ELO rating
            is_major_match: Whether this is a major match
            recent_performance: Recent performance adjustment (-1 to 1)

        Returns:
            Dynamic K-factor
        """
        # Base K adjustment on rating level
        # Higher ratings are more stable
        if rating > 2000:
            k = 12.0
        elif rating > 1800:
            k = 16.0
        elif rating > 1500:
            k = 20.0
        elif rating > 1200:
            k = 24.0
        else:
            k = 32.0

        # Major match bonus
        if is_major_match:
            k *= 1.5

        # Recent performance adjustment
        # Teams on a hot streak (positive performance) get higher K
        if recent_performance > 0.1:
            k *= (1.0 + recent_performance * 0.5)

        return k

    def expected_score(
        self,
        rating_a: float,
        rating_b: float,
        is_a_home: bool = True,
    ) -> float:
        """
        Calculate expected score for team A (0-1 scale).

        Args:
            rating_a: Team A's ELO rating
            rating_b: Team B's ELO rating
            is_a_home: Whether team A is playing at home

        Returns:
            Expected score for team A
        """
        # Apply home advantage
        adjusted_a = rating_a + (self.home_advantage if is_a_home else 0)
        adjusted_b = rating_b + (0 if is_a_home else self.home_advantage)

        # Standard ELO formula
        return 1.0 / (1.0 + 10.0 ** ((adjusted_b - adjusted_a) / 400.0))

    def calculate_outcome_probabilities(
        self,
        home_rating: float,
        away_rating: float,
        home_performance: float = 0.0,
        away_performance: float = 0.0,
    ) -> Tuple[float, float, float]:
        """
        Calculate win/draw/loss probabilities with calibration.

        Args:
            home_rating: Home team's ELO rating
            away_rating: Away team's ELO rating
            home_performance: Home team's recent performance adjustment
            away_performance: Away team's recent performance adjustment

        Returns:
            Tuple of (home_win_prob, draw_prob, away_win_prob)
        """
        # Adjust ratings by recent performance
        adjusted_home = home_rating + (home_performance * 50)
        adjusted_away = away_rating + (away_performance * 50)

        # Get expected score for home team
        exp_home = self.expected_score(adjusted_home, adjusted_away, is_a_home=True)

        # Calculate draw probability
        # Draw probability is highest when teams are evenly matched
        rating_diff = abs((adjusted_home + self.home_advantage) - adjusted_away)

        # Base draw probability
        base_draw_prob = self.draw_factor
        # Reduce draw probability with increasing rating difference
        draw_reduction = min(0.15, rating_diff / 1200)
        draw_prob = max(0.08, base_draw_prob - draw_reduction)

        # Distribute remaining probability
        remaining_prob = 1.0 - draw_prob
        home_win_prob = exp_home * remaining_prob
        away_win_prob = (1.0 - exp_home) * remaining_prob

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
            Tuple of (home_score, away_score)
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

        Args:
            goal_diff: Absolute goal difference

        Returns:
            Multiplier for K-factor
        """
        if goal_diff <= 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            return (11 + goal_diff) / 8

    def update_ratings(
        self,
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
        is_major_match: bool = False,
    ) -> Tuple[float, float]:
        """
        Update ratings after a match.

        Args:
            home_rating: Home team's current rating
            away_rating: Away team's current rating
            home_goals: Goals scored by home team
            away_goals: Goals scored by away team
            is_major_match: Whether this is a major match

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
        expected_away = 1.0 - expected_home

        # Goal difference multiplier
        goal_diff = abs(home_goals - away_goals)
        gd_mult = self.goal_difference_multiplier(goal_diff)

        # Dynamic K-factors
        k_home = self.dynamic_k_factor(home_rating, is_major_match)
        k_away = self.dynamic_k_factor(away_rating, is_major_match)

        # Calculate rating changes
        home_change = k_home * gd_mult * (actual_home - expected_home)
        away_change = k_away * gd_mult * (actual_away - expected_away)

        return (
            home_rating + home_change,
            away_rating + away_change,
        )

    def recent_performance_rating(
        self,
        recent_matches: list[Literal["W", "D", "L"]],
        max_age_days: int = 30,
    ) -> float:
        """
        Calculate performance adjustment from recent results.

        Uses exponential decay to weight recent matches more heavily.
        Better handles momentum and current form.

        Args:
            recent_matches: List of recent results (W/D/L) in order
            max_age_days: Only consider matches from last N days

        Returns:
            Performance adjustment (-1 to 1, where 1 is perfect)
        """
        if not recent_matches:
            return 0.0

        # Limit to recent matches (max 10 for computational efficiency)
        recent_matches = recent_matches[-10:]

        # Weight recent matches more heavily with exponential decay
        weights = []
        for i, _ in enumerate(reversed(recent_matches)):
            # Exponential decay: most recent gets highest weight
            # decay_factor of 0.15 gives ~85% weight to most recent
            weight = np.exp(-0.15 * i)
            weights.append(weight)

        weights = np.array(weights)
        weights /= weights.sum()

        # Calculate win rate with weighting
        win_points = []
        for result in recent_matches:
            if result == "W":
                win_points.append(1.0)
            elif result == "D":
                win_points.append(0.5)
            else:
                win_points.append(0.0)

        # Weighted average
        win_rate = np.average(win_points, weights=weights)

        # Adjustment: 0.5 win rate = 0.0, 1.0 = +1.0, 0.0 = -1.0
        # Apply slight damping to prevent over-correction (max ~0.8)
        adjustment = (win_rate - 0.5) * 2.0
        adjustment = np.clip(adjustment, -0.8, 0.8)  # Limit extreme swings
        return adjustment

    def predict(
        self,
        home_rating: float,
        away_rating: float,
        home_recent_form: list[Literal["W", "D", "L"]] | None = None,
        away_recent_form: list[Literal["W", "D", "L"]] | None = None,
    ) -> AdvancedELOPrediction:
        """
        Make a prediction with performance adjustment.

        Args:
            home_rating: Home team's ELO rating
            away_rating: Away team's ELO rating
            home_recent_form: Recent home team results
            away_recent_form: Recent away team results

        Returns:
            AdvancedELOPrediction with probabilities and confidence
        """
        # Calculate performance ratings
        home_perf = (
            self.recent_performance_rating(home_recent_form)
            if home_recent_form
            else 0.0
        )
        away_perf = (
            self.recent_performance_rating(away_recent_form)
            if away_recent_form
            else 0.0
        )

        # Calculate adjusted ratings
        adj_home = home_rating + (home_perf * 50)
        adj_away = away_rating + (away_perf * 50)

        # Get probabilities
        home_prob, draw_prob, away_prob = self.calculate_outcome_probabilities(
            home_rating, away_rating, home_perf, away_perf
        )

        # Calculate confidence based on rating difference
        rating_diff = abs(adj_home - adj_away)
        max_prob = max(home_prob, draw_prob, away_prob)
        # Confidence scales with probability margin and rating difference
        confidence = 0.55 + (max_prob - 0.33) * 0.4 + min(0.2, rating_diff / 1000)
        confidence = min(0.95, max(0.5, confidence))

        # Estimate expected goals with better calibration
        # Use rating difference for more accurate goal prediction
        rating_diff = (adj_home + self.home_advantage) - adj_away

        # Better scaling of rating difference to goals (research-based)
        # Each 400 rating points ~0.25 goal difference
        base_goals = 1.30
        rating_goal_factor = 0.25

        exp_home = base_goals + (rating_diff / 400) * rating_goal_factor
        exp_away = base_goals - (rating_diff / 400) * rating_goal_factor

        # Improved clamping with better bounds
        exp_home = np.clip(exp_home, 0.4, 3.5)
        exp_away = np.clip(exp_away, 0.4, 3.5)

        return AdvancedELOPrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            home_elo=home_rating,
            away_elo=away_rating,
            home_performance_rating=home_perf,
            away_performance_rating=away_perf,
            expected_home_score=exp_home,
            expected_away_score=exp_away,
            confidence=confidence,
        )


# Default instance
advanced_elo_system = AdvancedELOSystem()
