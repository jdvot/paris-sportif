"""Poisson distribution model for football match prediction.

The Poisson distribution models goal scoring as independent events.
It's one of the most established methods for predicting football scores.

Reference: https://dashee87.github.io/data%20science/football/r/predicting-football-results-with-statistical-modelling/
"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy.stats import poisson


@dataclass
class PoissonPrediction:
    """Poisson model prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: Tuple[int, int]
    score_probabilities: dict[Tuple[int, int], float]


class PoissonModel:
    """
    Poisson distribution model for football predictions.

    Uses historical goal averages to calculate expected goals (lambda)
    for each team, then uses Poisson distribution to estimate outcomes.
    """

    # Constants
    HOME_ADVANTAGE = 1.15  # Home teams score ~15% more on average
    MAX_GOALS = 8  # Maximum goals to consider per team

    def __init__(
        self,
        league_avg_goals: float = 2.75,  # Average total goals per match
        home_advantage_factor: float = 1.15,
    ):
        """
        Initialize Poisson model.

        Args:
            league_avg_goals: Average total goals per match in the league
            home_advantage_factor: Multiplier for home team goal expectancy
        """
        self.league_avg_goals = league_avg_goals
        self.home_advantage = home_advantage_factor

    def calculate_expected_goals(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
    ) -> Tuple[float, float]:
        """
        Calculate expected goals for each team.

        Args:
            home_attack: Home team's average goals scored (home matches)
            home_defense: Home team's average goals conceded (home matches)
            away_attack: Away team's average goals scored (away matches)
            away_defense: Away team's average goals conceded (away matches)

        Returns:
            Tuple of (expected_home_goals, expected_away_goals)
        """
        # League average per team (half of total)
        league_avg_per_team = self.league_avg_goals / 2

        # Attack and defense strength relative to league average
        home_attack_strength = home_attack / league_avg_per_team if league_avg_per_team > 0 else 1.0
        away_attack_strength = away_attack / league_avg_per_team if league_avg_per_team > 0 else 1.0

        home_defense_strength = home_defense / league_avg_per_team if league_avg_per_team > 0 else 1.0
        away_defense_strength = away_defense / league_avg_per_team if league_avg_per_team > 0 else 1.0

        # Expected goals
        # Home: home attack strength × away defense weakness × league avg × home advantage
        expected_home = (
            home_attack_strength
            * away_defense_strength
            * league_avg_per_team
            * self.home_advantage
        )

        # Away: away attack strength × home defense weakness × league avg
        expected_away = (
            away_attack_strength
            * home_defense_strength
            * league_avg_per_team
        )

        # Clamp to reasonable values
        expected_home = max(0.3, min(4.0, expected_home))
        expected_away = max(0.3, min(4.0, expected_away))

        return expected_home, expected_away

    def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
    ) -> PoissonPrediction:
        """
        Make a prediction using Poisson distribution.

        Args:
            home_attack: Home team avg goals scored at home
            home_defense: Home team avg goals conceded at home
            away_attack: Away team avg goals scored away
            away_defense: Away team avg goals conceded away

        Returns:
            PoissonPrediction with probabilities and expected scores
        """
        # Calculate expected goals
        exp_home, exp_away = self.calculate_expected_goals(
            home_attack, home_defense, away_attack, away_defense
        )

        # Build score probability matrix
        score_probs: dict[Tuple[int, int], float] = {}
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        for home_goals in range(self.MAX_GOALS + 1):
            for away_goals in range(self.MAX_GOALS + 1):
                # P(home_goals) × P(away_goals)
                prob = (
                    poisson.pmf(home_goals, exp_home)
                    * poisson.pmf(away_goals, exp_away)
                )
                score_probs[(home_goals, away_goals)] = prob

                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals < away_goals:
                    away_win_prob += prob
                else:
                    draw_prob += prob

        # Find most likely score
        most_likely = max(score_probs, key=score_probs.get)  # type: ignore

        # Normalize probabilities (they should sum to ~1 already)
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

        return PoissonPrediction(
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            expected_home_goals=exp_home,
            expected_away_goals=exp_away,
            most_likely_score=most_likely,
            score_probabilities=score_probs,
        )

    def predict_with_xg(
        self,
        home_xg_for: float,
        home_xg_against: float,
        away_xg_for: float,
        away_xg_against: float,
    ) -> PoissonPrediction:
        """
        Predict using xG (Expected Goals) data instead of actual goals.

        xG is more predictive than actual goals as it measures chance quality.

        Args:
            home_xg_for: Home team's avg xG created at home
            home_xg_against: Home team's avg xG conceded at home
            away_xg_for: Away team's avg xG created away
            away_xg_against: Away team's avg xG conceded away
        """
        return self.predict(
            home_attack=home_xg_for,
            home_defense=home_xg_against,
            away_attack=away_xg_for,
            away_defense=away_xg_against,
        )

    def over_under_probability(
        self,
        expected_home: float,
        expected_away: float,
        line: float = 2.5,
    ) -> Tuple[float, float]:
        """
        Calculate over/under probabilities for a goals line.

        Args:
            expected_home: Expected goals for home team
            expected_away: Expected goals for away team
            line: Goals line (e.g., 2.5)

        Returns:
            Tuple of (over_prob, under_prob)
        """
        over_prob = 0.0

        for home_goals in range(self.MAX_GOALS + 1):
            for away_goals in range(self.MAX_GOALS + 1):
                if home_goals + away_goals > line:
                    prob = (
                        poisson.pmf(home_goals, expected_home)
                        * poisson.pmf(away_goals, expected_away)
                    )
                    over_prob += prob

        return over_prob, 1 - over_prob

    def btts_probability(
        self,
        expected_home: float,
        expected_away: float,
    ) -> float:
        """
        Calculate Both Teams To Score probability.

        Args:
            expected_home: Expected goals for home team
            expected_away: Expected goals for away team

        Returns:
            Probability that both teams score
        """
        # P(home >= 1) × P(away >= 1)
        home_scores = 1 - poisson.pmf(0, expected_home)
        away_scores = 1 - poisson.pmf(0, expected_away)

        return home_scores * away_scores


# Default instance
poisson_model = PoissonModel()
