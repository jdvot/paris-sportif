"""Feature engineering utilities for ML-based prediction models.

This module provides advanced feature engineering for XGBoost and Random Forest models.
It includes:
- Feature scaling and normalization
- Interaction features (strength products, ratios)
- Momentum and recency-weighted features
- Head-to-head historical statistics
- Form trending indicators

Features are designed to capture:
1. Current capabilities (attack/defense strength)
2. Recent momentum (recent form weighted by time)
3. Historical matchups (h2h advantage)
4. Interaction effects (e.g., strong attack vs weak defense)
"""

from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Structured feature vector for ML predictions."""

    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float
    recent_form_home: float
    recent_form_away: float
    head_to_head_home: float

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input."""
        return np.array([
            self.home_attack,
            self.home_defense,
            self.away_attack,
            self.away_defense,
            self.recent_form_home,
            self.recent_form_away,
            self.head_to_head_home,
        ])


class FeatureEngineer:
    """
    Feature engineering for football prediction models.

    Transforms raw team statistics into ML features.
    """

    # Normalization bounds
    ATTACK_MIN = 0.3
    ATTACK_MAX = 3.5
    DEFENSE_MIN = 0.3
    DEFENSE_MAX = 3.5
    FORM_MIN = 0.0
    FORM_MAX = 100.0

    @staticmethod
    def normalize_attack_defense(
        value: float,
        is_attack: bool = True,
    ) -> float:
        """
        Normalize attack/defense strength to standard range.

        Args:
            value: Raw attack or defense value
            is_attack: True for attack, False for defense

        Returns:
            Normalized value in [0, 1] range
        """
        if is_attack:
            min_val, max_val = FeatureEngineer.ATTACK_MIN, FeatureEngineer.ATTACK_MAX
        else:
            min_val, max_val = FeatureEngineer.DEFENSE_MIN, FeatureEngineer.DEFENSE_MAX

        # Clamp to bounds
        value = np.clip(value, min_val, max_val)

        # Normalize to [0, 1]
        return (value - min_val) / (max_val - min_val)

    @staticmethod
    def normalize_form(form_value: float) -> float:
        """
        Normalize recent form score to [0, 1].

        Args:
            form_value: Form score (typically 0-100)

        Returns:
            Normalized form in [0, 1]
        """
        form_value = np.clip(form_value, FeatureEngineer.FORM_MIN, FeatureEngineer.FORM_MAX)
        return form_value / FeatureEngineer.FORM_MAX

    @staticmethod
    def calculate_recent_form(
        recent_results: List[Tuple[int, int]],
        is_home: bool = True,
        decay_rate: float = 0.9,
    ) -> float:
        """
        Calculate recent form score from match results.

        Results are weighted more heavily if recent.

        Args:
            recent_results: List of (goals_for, goals_against) tuples,
                           ordered with most recent first
            is_home: Whether calculating for home team
            decay_rate: Weight decay for older matches (0-1)

        Returns:
            Form score in [0, 100]
        """
        if not recent_results:
            return 50.0  # Neutral form

        total_score = 0.0
        total_weight = 0.0

        for i, (goals_for, goals_against) in enumerate(recent_results):
            # Weight decay: recent matches weighted more
            weight = decay_rate ** i

            # Calculate result: 1.0 for win, 0.5 for draw, 0 for loss
            if goals_for > goals_against:
                result = 1.0
            elif goals_for == goals_against:
                result = 0.5
            else:
                result = 0.0

            # Add goal differential bonus (max +0.2 for strong wins)
            diff_bonus = min(0.2, (goals_for - goals_against) * 0.05)
            result += diff_bonus

            total_score += result * weight
            total_weight += weight

        # Convert to 0-100 scale
        if total_weight > 0:
            normalized = total_score / total_weight
            return 50.0 + (normalized - 0.5) * 50  # Map [0, 1] to [0, 100]
        return 50.0

    @staticmethod
    def calculate_head_to_head(
        h2h_results: List[Tuple[int, int]],
        is_home: bool = True,
    ) -> float:
        """
        Calculate head-to-head advantage score.

        Args:
            h2h_results: List of (goals_for, goals_against) in past matchups
            is_home: Whether calculating from home team perspective

        Returns:
            H2H score in [-1.0, 1.0] where positive = home advantage
        """
        if not h2h_results:
            return 0.0  # No history

        wins = 0
        draws = 0
        losses = 0

        for goals_for, goals_against in h2h_results:
            if goals_for > goals_against:
                wins += 1
            elif goals_for == goals_against:
                draws += 1
            else:
                losses += 1

        total = wins + draws + losses

        if total == 0:
            return 0.0

        # Win probability minus loss probability
        h2h_score = (wins - losses) / total

        # Apply recency weighting if we have it (use first item as most recent)
        # Most recent result has extra weight
        if h2h_results:
            recent_goals_for, recent_goals_against = h2h_results[0]
            if recent_goals_for > recent_goals_against:
                h2h_score = np.clip(h2h_score + 0.1, -1.0, 1.0)
            elif recent_goals_for < recent_goals_against:
                h2h_score = np.clip(h2h_score - 0.1, -1.0, 1.0)

        return float(np.clip(h2h_score, -1.0, 1.0))

    @staticmethod
    def engineer_features(
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        home_recent_results: Optional[List[Tuple[int, int]]] = None,
        away_recent_results: Optional[List[Tuple[int, int]]] = None,
        h2h_results: Optional[List[Tuple[int, int]]] = None,
    ) -> FeatureVector:
        """
        Create engineered feature vector for ML models.

        Args:
            home_attack: Home team attack strength
            home_defense: Home team defense strength
            away_attack: Away team attack strength
            away_defense: Away team defense strength
            home_recent_results: Recent match results for home team
            away_recent_results: Recent match results for away team
            h2h_results: Head-to-head results (from home perspective)

        Returns:
            FeatureVector with engineered features
        """
        # Normalize basic stats
        norm_home_attack = FeatureEngineer.normalize_attack_defense(home_attack, is_attack=True)
        norm_home_defense = FeatureEngineer.normalize_attack_defense(home_defense, is_attack=False)
        norm_away_attack = FeatureEngineer.normalize_attack_defense(away_attack, is_attack=True)
        norm_away_defense = FeatureEngineer.normalize_attack_defense(away_defense, is_attack=False)

        # Calculate recent form (convert to 0-1 scale)
        home_form = 50.0
        away_form = 50.0

        if home_recent_results:
            home_form = FeatureEngineer.calculate_recent_form(
                home_recent_results,
                is_home=True,
            )
        if away_recent_results:
            away_form = FeatureEngineer.calculate_recent_form(
                away_recent_results,
                is_home=False,
            )

        home_form_norm = FeatureEngineer.normalize_form(home_form)
        away_form_norm = FeatureEngineer.normalize_form(away_form)

        # Calculate head-to-head
        h2h_home = 0.0
        if h2h_results:
            h2h_home = FeatureEngineer.calculate_head_to_head(h2h_results, is_home=True)

        return FeatureVector(
            home_attack=norm_home_attack,
            home_defense=norm_home_defense,
            away_attack=norm_away_attack,
            away_defense=norm_away_defense,
            recent_form_home=home_form_norm,
            recent_form_away=away_form_norm,
            head_to_head_home=h2h_home,
        )

    @staticmethod
    def create_interaction_features(features: FeatureVector) -> Dict[str, float]:
        """
        Create interaction features from base features.

        These capture non-linear relationships.

        Args:
            features: Base feature vector

        Returns:
            Dictionary of interaction features
        """
        interactions = {
            # Attack vs defense matchups
            "home_attack_vs_away_defense": features.home_attack * features.away_defense,
            "away_attack_vs_home_defense": features.away_attack * features.home_defense,

            # Team strength ratios
            "home_strength_ratio": features.home_attack / (features.home_defense + 0.01),
            "away_strength_ratio": features.away_attack / (features.away_defense + 0.01),

            # Form advantage
            "form_advantage": features.recent_form_home - features.recent_form_away,

            # Combined strength
            "home_total_strength": features.home_attack + (1 - features.home_defense),
            "away_total_strength": features.away_attack + (1 - features.away_defense),
        }

        return interactions

    @staticmethod
    def augment_dataframe(
        df: pd.DataFrame,
        add_interactions: bool = True,
    ) -> pd.DataFrame:
        """
        Augment a DataFrame with engineered features.

        Assumes DataFrame has columns:
        - home_attack, home_defense, away_attack, away_defense

        Args:
            df: DataFrame with match data
            add_interactions: Whether to add interaction features

        Returns:
            Augmented DataFrame with new feature columns
        """
        df = df.copy()

        # Ensure required columns exist
        required = ["home_attack", "home_defense", "away_attack", "away_defense"]
        if not all(col in df.columns for col in required):
            logger.warning(f"Missing required columns. Need: {required}")
            return df

        # Create interaction features for each row
        if add_interactions:
            for idx, row in df.iterrows():
                features = FeatureVector(
                    home_attack=row["home_attack"],
                    home_defense=row["home_defense"],
                    away_attack=row["away_attack"],
                    away_defense=row["away_defense"],
                    recent_form_home=row.get("recent_form_home", 50.0),
                    recent_form_away=row.get("recent_form_away", 50.0),
                    head_to_head_home=row.get("head_to_head_home", 0.0),
                )

                interactions = FeatureEngineer.create_interaction_features(features)
                for col, val in interactions.items():
                    if col not in df.columns:
                        df[col] = 0.0
                    df.at[idx, col] = val

        return df
