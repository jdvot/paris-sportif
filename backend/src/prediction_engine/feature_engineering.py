"""Feature engineering utilities for ML-based prediction models.

This module provides advanced feature engineering for XGBoost and Random Forest models.
It includes:
- Feature scaling and normalization
- Interaction features (strength products, ratios)
- Momentum and recency-weighted features
- Head-to-head historical statistics
- Form trending indicators
- Fatigue and fixture congestion metrics

Features are designed to capture:
1. Current capabilities (attack/defense strength)
2. Recent momentum (recent form weighted by time)
3. Historical matchups (h2h advantage)
4. Interaction effects (e.g., strong attack vs weak defense)
5. Physical fatigue from fixture congestion
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Structured feature vector for ML predictions.

    Contains 7 base features, 4 fatigue features, and 7 computed interaction features.
    Interaction features capture non-linear relationships like attack vs defense matchups.
    Fatigue features capture physical readiness based on fixture schedule.
    """

    # Base features (7)
    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float
    recent_form_home: float
    recent_form_away: float
    head_to_head_home: float

    # Fatigue features (4) - normalized to [0, 1]
    home_rest_days: float = 0.5  # 0=fatigued (<=2 days), 1=well-rested (>=7 days)
    away_rest_days: float = 0.5
    home_fixture_congestion: float = 0.5  # 0=congested (5+ matches/14 days), 1=light schedule
    away_fixture_congestion: float = 0.5

    # Interaction features (computed, with defaults for backwards compatibility)
    home_attack_vs_away_defense: float = 0.0
    away_attack_vs_home_defense: float = 0.0
    home_strength_ratio: float = 1.0
    away_strength_ratio: float = 1.0
    form_advantage: float = 0.0
    home_total_strength: float = 0.5
    away_total_strength: float = 0.5
    fatigue_advantage: float = 0.0  # Positive = home team more rested

    def compute_interactions(self) -> "FeatureVector":
        """Compute interaction features from base features.

        Returns a new FeatureVector with interaction features populated.
        """
        eps = 0.01  # Avoid division by zero

        # Compute fatigue advantage: combines rest days and fixture congestion
        home_fatigue_score = (self.home_rest_days + self.home_fixture_congestion) / 2
        away_fatigue_score = (self.away_rest_days + self.away_fixture_congestion) / 2
        fatigue_adv = home_fatigue_score - away_fatigue_score

        return FeatureVector(
            # Copy base features
            home_attack=self.home_attack,
            home_defense=self.home_defense,
            away_attack=self.away_attack,
            away_defense=self.away_defense,
            recent_form_home=self.recent_form_home,
            recent_form_away=self.recent_form_away,
            head_to_head_home=self.head_to_head_home,
            # Copy fatigue features
            home_rest_days=self.home_rest_days,
            away_rest_days=self.away_rest_days,
            home_fixture_congestion=self.home_fixture_congestion,
            away_fixture_congestion=self.away_fixture_congestion,
            # Compute interaction features
            home_attack_vs_away_defense=self.home_attack * self.away_defense,
            away_attack_vs_home_defense=self.away_attack * self.home_defense,
            home_strength_ratio=self.home_attack / (self.home_defense + eps),
            away_strength_ratio=self.away_attack / (self.away_defense + eps),
            form_advantage=self.recent_form_home - self.recent_form_away,
            home_total_strength=self.home_attack + (1 - self.home_defense),
            away_total_strength=self.away_attack + (1 - self.away_defense),
            fatigue_advantage=fatigue_adv,
        )

    def to_array(
        self,
        include_interactions: bool = False,
        include_fatigue: bool = True,
    ) -> np.ndarray:
        """Convert to numpy array for model input.

        Args:
            include_interactions: If True, include 8 interaction features.
            include_fatigue: If True, include 4 fatigue features.

        Returns:
            numpy array with features in consistent order.
        """
        base_features = [
            self.home_attack,
            self.home_defense,
            self.away_attack,
            self.away_defense,
            self.recent_form_home,
            self.recent_form_away,
            self.head_to_head_home,
        ]

        fatigue_features = [
            self.home_rest_days,
            self.away_rest_days,
            self.home_fixture_congestion,
            self.away_fixture_congestion,
        ]

        interaction_features = [
            self.home_attack_vs_away_defense,
            self.away_attack_vs_home_defense,
            self.home_strength_ratio,
            self.away_strength_ratio,
            self.form_advantage,
            self.home_total_strength,
            self.away_total_strength,
            self.fatigue_advantage,
        ]

        result = base_features
        if include_fatigue:
            result = result + fatigue_features
        if include_interactions:
            result = result + interaction_features

        return np.array(result)

    @classmethod
    def get_feature_names(
        cls,
        include_interactions: bool = False,
        include_fatigue: bool = True,
    ) -> list[str]:
        """Get ordered list of feature names.

        Args:
            include_interactions: If True, include interaction feature names.
            include_fatigue: If True, include fatigue feature names.
        """
        base_names = [
            "home_attack",
            "home_defense",
            "away_attack",
            "away_defense",
            "recent_form_home",
            "recent_form_away",
            "head_to_head_home",
        ]

        fatigue_names = [
            "home_rest_days",
            "away_rest_days",
            "home_fixture_congestion",
            "away_fixture_congestion",
        ]

        interaction_names = [
            "home_attack_vs_away_defense",
            "away_attack_vs_home_defense",
            "home_strength_ratio",
            "away_strength_ratio",
            "form_advantage",
            "home_total_strength",
            "away_total_strength",
            "fatigue_advantage",
        ]

        result = base_names
        if include_fatigue:
            result = result + fatigue_names
        if include_interactions:
            result = result + interaction_names

        return result


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

    # Fatigue thresholds
    REST_DAYS_MIN = 2  # Minimum rest (fatigued)
    REST_DAYS_MAX = 7  # Maximum useful rest
    CONGESTION_WINDOW_DAYS = 14  # Window for fixture congestion
    CONGESTION_MAX_MATCHES = 5  # Matches in window considered congested

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
    def calculate_rest_days(
        last_match_date: datetime | str | None,
        current_match_date: datetime | str | None = None,
    ) -> float:
        """
        Calculate normalized rest days score.

        More rest = higher score (better physical condition).

        Args:
            last_match_date: Date of team's last match
            current_match_date: Date of upcoming match (defaults to now)

        Returns:
            Normalized rest score in [0, 1] where:
            - 0.0 = very fatigued (<=2 days rest)
            - 0.5 = moderate (4-5 days)
            - 1.0 = well-rested (>=7 days)
        """
        if last_match_date is None:
            return 0.5  # Unknown, assume average

        if isinstance(last_match_date, str):
            try:
                last_match_date = datetime.fromisoformat(last_match_date.replace("Z", "+00:00"))
            except ValueError:
                return 0.5

        if current_match_date is None:
            current_match_date = datetime.now()
        elif isinstance(current_match_date, str):
            try:
                current_match_date = datetime.fromisoformat(
                    current_match_date.replace("Z", "+00:00")
                )
            except ValueError:
                current_match_date = datetime.now()

        # Handle timezone-naive comparison
        if last_match_date.tzinfo is not None and current_match_date.tzinfo is None:
            last_match_date = last_match_date.replace(tzinfo=None)
        elif current_match_date.tzinfo is not None and last_match_date.tzinfo is None:
            current_match_date = current_match_date.replace(tzinfo=None)

        days_rest = (current_match_date - last_match_date).days

        # Clamp and normalize
        days_rest = np.clip(
            days_rest,
            FeatureEngineer.REST_DAYS_MIN,
            FeatureEngineer.REST_DAYS_MAX,
        )

        return (days_rest - FeatureEngineer.REST_DAYS_MIN) / (
            FeatureEngineer.REST_DAYS_MAX - FeatureEngineer.REST_DAYS_MIN
        )

    @staticmethod
    def calculate_fixture_congestion(
        recent_match_dates: list[datetime | str] | None,
        current_match_date: datetime | str | None = None,
        window_days: int | None = None,
    ) -> float:
        """
        Calculate fixture congestion score.

        Fewer matches in the window = higher score (less fatigue).

        Args:
            recent_match_dates: List of recent match dates for the team
            current_match_date: Date of upcoming match
            window_days: Days to look back (default: CONGESTION_WINDOW_DAYS)

        Returns:
            Normalized congestion score in [0, 1] where:
            - 0.0 = very congested (5+ matches in 14 days)
            - 0.5 = moderate (2-3 matches)
            - 1.0 = light schedule (0-1 matches)
        """
        if not recent_match_dates:
            return 0.5  # Unknown, assume average

        if window_days is None:
            window_days = FeatureEngineer.CONGESTION_WINDOW_DAYS

        if current_match_date is None:
            current_match_date = datetime.now()
        elif isinstance(current_match_date, str):
            try:
                current_match_date = datetime.fromisoformat(
                    current_match_date.replace("Z", "+00:00")
                )
            except ValueError:
                current_match_date = datetime.now()

        # Make current_match_date timezone-naive for consistent comparisons
        if current_match_date.tzinfo is not None:
            current_match_date = current_match_date.replace(tzinfo=None)

        window_start = current_match_date - timedelta(days=window_days)

        # Count matches in the window
        matches_in_window = 0
        for match_date in recent_match_dates:
            if isinstance(match_date, str):
                try:
                    match_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                except ValueError:
                    continue

            # Make match_date timezone-naive for comparison
            if match_date.tzinfo is not None:
                match_date = match_date.replace(tzinfo=None)

            if window_start <= match_date < current_match_date:
                matches_in_window += 1

        # Normalize: 0 matches = 1.0, CONGESTION_MAX_MATCHES+ = 0.0
        congestion_score = 1.0 - (matches_in_window / FeatureEngineer.CONGESTION_MAX_MATCHES)
        return float(np.clip(congestion_score, 0.0, 1.0))

    @staticmethod
    def calculate_recent_form(
        recent_results: list[tuple[int, int]],
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
            weight = decay_rate**i

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
        h2h_results: list[tuple[int, int]],
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
        home_recent_results: list[tuple[int, int]] | None = None,
        away_recent_results: list[tuple[int, int]] | None = None,
        h2h_results: list[tuple[int, int]] | None = None,
        # Fatigue parameters
        home_last_match_date: datetime | str | None = None,
        away_last_match_date: datetime | str | None = None,
        home_recent_match_dates: list[datetime | str] | None = None,
        away_recent_match_dates: list[datetime | str] | None = None,
        current_match_date: datetime | str | None = None,
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
            home_last_match_date: Date of home team's last match (for rest days)
            away_last_match_date: Date of away team's last match (for rest days)
            home_recent_match_dates: List of home team's recent match dates (for congestion)
            away_recent_match_dates: List of away team's recent match dates (for congestion)
            current_match_date: Date of the upcoming match

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

        # Calculate fatigue features
        home_rest = FeatureEngineer.calculate_rest_days(
            home_last_match_date,
            current_match_date,
        )
        away_rest = FeatureEngineer.calculate_rest_days(
            away_last_match_date,
            current_match_date,
        )
        home_congestion = FeatureEngineer.calculate_fixture_congestion(
            home_recent_match_dates,
            current_match_date,
        )
        away_congestion = FeatureEngineer.calculate_fixture_congestion(
            away_recent_match_dates,
            current_match_date,
        )

        base_features = FeatureVector(
            home_attack=norm_home_attack,
            home_defense=norm_home_defense,
            away_attack=norm_away_attack,
            away_defense=norm_away_defense,
            recent_form_home=home_form_norm,
            recent_form_away=away_form_norm,
            head_to_head_home=h2h_home,
            home_rest_days=home_rest,
            away_rest_days=away_rest,
            home_fixture_congestion=home_congestion,
            away_fixture_congestion=away_congestion,
        )

        # Compute interaction features automatically
        return base_features.compute_interactions()

    @staticmethod
    def create_interaction_features(features: FeatureVector) -> dict[str, float]:
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
        add_fatigue: bool = True,
    ) -> pd.DataFrame:
        """
        Augment a DataFrame with engineered features.

        Assumes DataFrame has columns:
        - home_attack, home_defense, away_attack, away_defense

        Optional columns for fatigue (if add_fatigue=True):
        - home_last_match_date, away_last_match_date (for rest days)
        - match_date (current match date for calculations)

        Args:
            df: DataFrame with match data
            add_interactions: Whether to add interaction features
            add_fatigue: Whether to add fatigue features

        Returns:
            Augmented DataFrame with new feature columns
        """
        df = df.copy()

        # Ensure required columns exist
        required = ["home_attack", "home_defense", "away_attack", "away_defense"]
        if not all(col in df.columns for col in required):
            logger.warning(f"Missing required columns. Need: {required}")
            return df

        # Create interaction and fatigue features for each row
        for idx, row in df.iterrows():
            # Get fatigue data if available
            home_rest = 0.5
            away_rest = 0.5
            home_congestion = 0.5
            away_congestion = 0.5

            if add_fatigue:
                current_date = row.get("match_date")
                home_last = row.get("home_last_match_date")
                away_last = row.get("away_last_match_date")

                if home_last is not None:
                    home_rest = FeatureEngineer.calculate_rest_days(home_last, current_date)
                if away_last is not None:
                    away_rest = FeatureEngineer.calculate_rest_days(away_last, current_date)

                # Note: For congestion, we'd need a list of recent match dates per team
                # which typically isn't in a simple DataFrame row. Use defaults.

            features = FeatureVector(
                home_attack=row["home_attack"],
                home_defense=row["home_defense"],
                away_attack=row["away_attack"],
                away_defense=row["away_defense"],
                recent_form_home=row.get("recent_form_home", 50.0),
                recent_form_away=row.get("recent_form_away", 50.0),
                head_to_head_home=row.get("head_to_head_home", 0.0),
                home_rest_days=home_rest,
                away_rest_days=away_rest,
                home_fixture_congestion=home_congestion,
                away_fixture_congestion=away_congestion,
            )

            if add_fatigue:
                # Add fatigue features
                df.at[idx, "home_rest_days"] = home_rest
                df.at[idx, "away_rest_days"] = away_rest
                df.at[idx, "home_fixture_congestion"] = home_congestion
                df.at[idx, "away_fixture_congestion"] = away_congestion

                # Calculate fatigue advantage
                home_fatigue_score = (home_rest + home_congestion) / 2
                away_fatigue_score = (away_rest + away_congestion) / 2
                df.at[idx, "fatigue_advantage"] = home_fatigue_score - away_fatigue_score

            if add_interactions:
                interactions = FeatureEngineer.create_interaction_features(features)
                for col, val in interactions.items():
                    if col not in df.columns:
                        df[col] = 0.0
                    df.at[idx, col] = val

        return df
