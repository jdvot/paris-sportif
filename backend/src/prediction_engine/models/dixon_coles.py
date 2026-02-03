"""Dixon-Coles model for football match prediction.

The Dixon-Coles model (1997) improves upon basic Poisson by:
1. Correcting for underestimation of low scores (0-0, 1-1)
2. Using time-weighting so recent matches are more important
3. Modeling correlation between home and away goals

This is one of the most established statistical models in football analytics.

References:
- Dixon & Coles (1997): "Modelling Association Football Scores and Inefficiencies in the Football Betting Market"
- https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import poisson


@dataclass
class DixonColesPrediction:
    """Dixon-Coles model prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: tuple[int, int]
    score_probabilities: dict[tuple[int, int], float]


class DixonColesModel:
    """
    Dixon-Coles model for football predictions.

    Key improvements over basic Poisson:
    - Bias correction for low-scoring draws (0-0, 1-1, 1-0, 0-1)
    - Time-weighting to emphasize recent matches
    - Correlates home and away goals through lambda parameter
    """

    # Maximum goals to consider per team
    MAX_GOALS = 8

    # Home advantage factor
    HOME_ADVANTAGE = 1.15

    # Time decay parameter (higher = faster decay)
    # xi = 0.0015 means goals ~46 days ago weighted at ~70% of current (better for recent form)
    TIME_DECAY_XI = 0.0015

    def __init__(
        self,
        league_avg_goals: float = 2.75,
        home_advantage_factor: float = 1.15,
        time_decay_xi: float = 0.0015,
        rho: float = -0.065,  # Correlation parameter for low scores
    ):
        """
        Initialize Dixon-Coles model.

        Args:
            league_avg_goals: Average total goals per match
            home_advantage_factor: Multiplier for home team goal expectancy
            time_decay_xi: Time decay parameter (0 = no decay, higher = faster decay)
                          Default 0.0015 gives half-weight at ~46 days
            rho: Correlation parameter (-0.065 to -0.080 is typical for football)
        """
        self.league_avg_goals = league_avg_goals
        self.home_advantage = home_advantage_factor
        self.time_decay_xi = time_decay_xi
        self.rho = rho  # Negative values mean low scores are more likely

    def _bias_correction(
        self,
        home_goals: int,
        away_goals: int,
        lambda_home: float,
        lambda_away: float,
    ) -> float:
        """
        Apply Dixon-Coles bias correction for low scores.

        Corrects for the fact that 0-0, 1-1, 1-0, and 0-1 are more likely
        than standard Poisson predicts.

        Args:
            home_goals: Home team goals in this scenario
            away_goals: Away team goals in this scenario
            lambda_home: Expected goals for home team
            lambda_away: Expected goals for away team

        Returns:
            Correction factor (1.0 = no correction)
        """
        # Improved correction with bounds checking
        if home_goals == 0 and away_goals == 0:
            correction = 1 - lambda_home * lambda_away * self.rho
        elif home_goals == 0 and away_goals == 1:
            correction = 1 - lambda_home * self.rho
        elif home_goals == 1 and away_goals == 0:
            correction = 1 - lambda_away * self.rho
        elif home_goals == 1 and away_goals == 1:
            correction = 1 + lambda_home * lambda_away * self.rho
        else:
            correction = 1.0

        # Ensure correction factor stays reasonable (between 0.5 and 1.5)
        # This prevents extreme adjustments
        correction = np.clip(correction, 0.5, 1.5)
        return correction

    def calculate_expected_goals(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        time_weight: float = 1.0,
    ) -> tuple[float, float]:
        """
        Calculate expected goals for each team.

        Args:
            home_attack: Home team's attack strength (avg goals at home)
            home_defense: Home team's defense strength (avg goals conceded at home)
            away_attack: Away team's attack strength (avg goals away)
            away_defense: Away team's defense strength (avg goals conceded away)
            time_weight: Time weight factor (0-1, where 1 = full weight for current match)

        Returns:
            Tuple of (expected_home_goals, expected_away_goals)
        """
        league_avg_per_team = self.league_avg_goals / 2

        # Avoid division by zero
        if league_avg_per_team <= 0:
            league_avg_per_team = 1.375  # Default fallback

        # Smoothing to prevent extreme ratios
        smoothing = 0.1

        # Attack and defense strength relative to league average
        home_attack_strength = (
            home_attack / (league_avg_per_team + smoothing) if league_avg_per_team > 0 else 1.0
        )
        away_attack_strength = (
            away_attack / (league_avg_per_team + smoothing) if league_avg_per_team > 0 else 1.0
        )

        home_defense_strength = (
            home_defense / (league_avg_per_team + smoothing) if league_avg_per_team > 0 else 1.0
        )
        away_defense_strength = (
            away_defense / (league_avg_per_team + smoothing) if league_avg_per_team > 0 else 1.0
        )

        # Expected goals with improved time weighting
        # Time weight should never make predictions too uncertain
        safe_time_weight = max(0.5, min(1.0, time_weight))

        expected_home = (
            home_attack_strength
            * away_defense_strength
            * league_avg_per_team
            * self.home_advantage
            * safe_time_weight
        )

        expected_away = (
            away_attack_strength
            * home_defense_strength
            * league_avg_per_team
            * safe_time_weight
            / 1.05  # Penalty for away teams
        )

        # Improved clamping with better bounds
        expected_home = np.clip(expected_home, 0.3, 5.0)
        expected_away = np.clip(expected_away, 0.3, 5.0)

        return expected_home, expected_away

    def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        time_weight: float = 1.0,
    ) -> DixonColesPrediction:
        """
        Make a prediction using Dixon-Coles model.

        Args:
            home_attack: Home team avg goals scored at home
            home_defense: Home team avg goals conceded at home
            away_attack: Away team avg goals scored away
            away_defense: Away team avg goals conceded away
            time_weight: Time weight factor (0-1)

        Returns:
            DixonColesPrediction with probabilities
        """
        # Calculate expected goals
        lambda_home, lambda_away = self.calculate_expected_goals(
            home_attack, home_defense, away_attack, away_defense, time_weight
        )

        # Build score probability matrix with bias correction
        score_probs: dict[tuple[int, int], float] = {}
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        for home_goals in range(self.MAX_GOALS + 1):
            for away_goals in range(self.MAX_GOALS + 1):
                # Base Poisson probabilities
                base_prob = poisson.pmf(home_goals, lambda_home) * poisson.pmf(
                    away_goals, lambda_away
                )

                # Apply Dixon-Coles bias correction
                correction = self._bias_correction(home_goals, away_goals, lambda_home, lambda_away)
                prob = base_prob * correction

                score_probs[(home_goals, away_goals)] = prob

                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals < away_goals:
                    away_win_prob += prob
                else:
                    draw_prob += prob

        # Find most likely score
        most_likely = max(score_probs, key=score_probs.get)  # type: ignore

        # Normalize probabilities
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

        return DixonColesPrediction(
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            expected_home_goals=lambda_home,
            expected_away_goals=lambda_away,
            most_likely_score=most_likely,
            score_probabilities=score_probs,
        )

    def predict_with_xg(
        self,
        home_xg_for: float,
        home_xg_against: float,
        away_xg_for: float,
        away_xg_against: float,
        time_weight: float = 1.0,
    ) -> DixonColesPrediction:
        """
        Predict using xG (Expected Goals) data instead of actual goals.

        xG is more predictive than actual goals as it measures chance quality.

        Args:
            home_xg_for: Home team's avg xG created at home
            home_xg_against: Home team's avg xG conceded at home
            away_xg_for: Away team's avg xG created away
            away_xg_against: Away team's avg xG conceded away
            time_weight: Time weight factor
        """
        return self.predict(
            home_attack=home_xg_for,
            home_defense=home_xg_against,
            away_attack=away_xg_for,
            away_defense=away_xg_against,
            time_weight=time_weight,
        )

    def time_weight(self, days_since_match: float) -> float:
        """
        Calculate time weight for a historical match.

        Recent matches get higher weight. Formula: exp(-xi * t)
        where t is days since match and xi is decay parameter.

        Args:
            days_since_match: Days since the match was played

        Returns:
            Weight factor (0-1, where 1 = full weight)
        """
        return np.exp(-self.time_decay_xi * days_since_match)

    def weighted_team_stats(
        self,
        matches: list[dict],
        team_name: str,
        is_home: bool,
        stat_type: str = "goals",
    ) -> float:
        """
        Calculate weighted team statistics using time decay.

        Args:
            matches: List of match dicts with keys: date, goals_for, goals_against
            team_name: Team name to calculate for
            is_home: Whether calculating for home or away matches
            stat_type: 'goals' or 'xg'

        Returns:
            Time-weighted average statistic
        """
        if not matches:
            return 0.0

        from datetime import datetime

        today = datetime.now()
        total_weight = 0.0
        weighted_sum = 0.0

        for match in matches:
            match_date = datetime.fromisoformat(match["date"])
            days_ago = (today - match_date).days

            weight = self.time_weight(days_ago)
            total_weight += weight

            if stat_type == "goals":
                value = match["goals_for"] if is_home else match["goals_against"]
            else:  # xg
                value = match.get("xg_for", 0) if is_home else match.get("xg_against", 0)

            weighted_sum += value * weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0


# Default instance
dixon_coles_model = DixonColesModel()
