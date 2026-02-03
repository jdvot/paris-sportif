"""ML Model Trainer for football predictions.

Trains XGBoost and Random Forest models on historical match data.
Creates features from match statistics and team performance.
"""

import json
import logging
import pickle
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Paths
ML_DIR = Path(__file__).parent
DATA_DIR = ML_DIR / "data"
MODELS_DIR = ML_DIR / "trained_models"
HISTORICAL_DATA_FILE = DATA_DIR / "historical_matches.json"

# Ensure directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class FeatureEngineer:
    """Creates ML features from match and team data."""

    def __init__(self) -> None:
        """Initialize feature engineering with team history tracking."""
        # Track team statistics over time
        self.team_goals_scored: defaultdict[Any, list[int]] = defaultdict(list)
        self.team_goals_conceded: defaultdict[Any, list[int]] = defaultdict(list)
        self.team_results: defaultdict[Any, list[int]] = defaultdict(list)
        self.head_to_head: defaultdict[Any, defaultdict[Any, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def reset(self) -> None:
        """Reset all tracked statistics."""
        self.team_goals_scored.clear()
        self.team_goals_conceded.clear()
        self.team_results.clear()
        self.head_to_head.clear()

    def calculate_form(self, results: list[int], last_n: int = 5) -> float:
        """
        Calculate team form from recent results.

        Args:
            results: List of results (0=win, 1=draw, 2=loss for home team)
            last_n: Number of recent matches to consider

        Returns:
            Form score 0-100
        """
        if not results:
            return 50.0  # Neutral form

        recent = results[-last_n:]
        # Points: win=3, draw=1, loss=0
        points = sum(3 if r == 0 else (1 if r == 1 else 0) for r in recent)
        max_points = len(recent) * 3
        return (points / max_points) * 100 if max_points > 0 else 50.0

    def calculate_attack_strength(self, goals_scored: list[int], last_n: int = 10) -> float:
        """Calculate attack strength from recent goals scored."""
        if not goals_scored:
            return 1.3  # League average
        recent = goals_scored[-last_n:]
        return sum(recent) / len(recent) if recent else 1.3

    def calculate_defense_strength(self, goals_conceded: list[int], last_n: int = 10) -> float:
        """Calculate defense strength from recent goals conceded."""
        if not goals_conceded:
            return 1.3  # League average
        recent = goals_conceded[-last_n:]
        return sum(recent) / len(recent) if recent else 1.3

    def calculate_h2h(self, team1_id: int, team2_id: int) -> float:
        """
        Calculate head-to-head advantage for team1 vs team2.

        Returns:
            Value between 0-1 (0.5 = neutral, >0.5 = team1 advantage)
        """
        h2h = self.head_to_head[team1_id][team2_id]
        if not h2h:
            return 0.5  # Neutral

        wins = sum(1 for r in h2h if r == 0)
        draws = sum(1 for r in h2h if r == 1)
        # Points percentage
        points = wins * 3 + draws
        max_points = len(h2h) * 3
        return points / max_points if max_points > 0 else 0.5

    def create_features(
        self, home_team_id: int, away_team_id: int, use_current_state: bool = True
    ) -> np.ndarray:
        """
        Create feature vector for a match.

        Features:
        0. home_attack - Home team attack strength
        1. home_defense - Home team defense strength (lower is better)
        2. away_attack - Away team attack strength
        3. away_defense - Away team defense strength
        4. home_form - Home team recent form (0-100)
        5. away_form - Away team recent form (0-100)
        6. h2h_advantage - Head-to-head advantage for home team

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            use_current_state: Use current team stats

        Returns:
            Feature vector as numpy array
        """
        home_attack = self.calculate_attack_strength(self.team_goals_scored[home_team_id])
        home_defense = self.calculate_defense_strength(self.team_goals_conceded[home_team_id])
        away_attack = self.calculate_attack_strength(self.team_goals_scored[away_team_id])
        away_defense = self.calculate_defense_strength(self.team_goals_conceded[away_team_id])

        # Calculate form (need to track results per team correctly)
        home_form = self.calculate_form(self.team_results[home_team_id])
        away_form = self.calculate_form(self.team_results[away_team_id])

        # Head-to-head
        h2h = self.calculate_h2h(home_team_id, away_team_id)

        return np.array(
            [
                home_attack,
                home_defense,
                away_attack,
                away_defense,
                home_form / 100.0,  # Normalize to 0-1
                away_form / 100.0,
                h2h,
            ]
        )

    def update_after_match(
        self, home_team_id: int, away_team_id: int, home_goals: int, away_goals: int, result: int
    ) -> None:
        """
        Update team statistics after a match.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_goals: Goals scored by home team
            away_goals: Goals scored by away team
            result: 0=home win, 1=draw, 2=away win
        """
        # Home team stats
        self.team_goals_scored[home_team_id].append(home_goals)
        self.team_goals_conceded[home_team_id].append(away_goals)
        self.team_results[home_team_id].append(result)

        # Away team stats (invert result)
        self.team_goals_scored[away_team_id].append(away_goals)
        self.team_goals_conceded[away_team_id].append(home_goals)
        away_result = 2 if result == 0 else (0 if result == 2 else 1)
        self.team_results[away_team_id].append(away_result)

        # H2H
        self.head_to_head[home_team_id][away_team_id].append(result)
        self.head_to_head[away_team_id][home_team_id].append(away_result)


class MLTrainer:
    """Trains XGBoost and Random Forest models."""

    def __init__(self) -> None:
        """Initialize trainer."""
        self.feature_engineer = FeatureEngineer()
        self.xgb_model: Any = None
        self.rf_model: Any = None

    def load_historical_data(self) -> dict[str, Any] | None:
        """Load historical match data."""
        if not HISTORICAL_DATA_FILE.exists():
            logger.error(f"No historical data found at {HISTORICAL_DATA_FILE}")
            logger.info("Run data_collector.py first to collect data")
            return None

        with open(HISTORICAL_DATA_FILE, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def prepare_training_data(
        self, matches: list[dict[str, Any]], min_history: int = 5
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from historical matches.

        Processes matches chronologically, using only past data to create
        features for each match (no data leakage).

        Args:
            matches: List of match dictionaries
            min_history: Minimum matches per team before including in training

        Returns:
            Tuple of (features, labels) numpy arrays
        """
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x["date"])

        features = []
        labels = []
        team_match_count: defaultdict[Any, int] = defaultdict(int)

        self.feature_engineer.reset()

        for match in sorted_matches:
            home_id = match["home_team"]["id"]
            away_id = match["away_team"]["id"]
            result = match["result"]
            home_goals = match["score"]["home"]
            away_goals = match["score"]["away"]

            # Only create training example if both teams have enough history
            if (
                team_match_count[home_id] >= min_history
                and team_match_count[away_id] >= min_history
            ):

                # Create features BEFORE updating stats (no data leakage)
                feature_vec = self.feature_engineer.create_features(home_id, away_id)
                features.append(feature_vec)
                labels.append(result)

            # Update stats AFTER creating features
            self.feature_engineer.update_after_match(
                home_id, away_id, home_goals, away_goals, result
            )
            team_match_count[home_id] += 1
            team_match_count[away_id] += 1

        logger.info(f"Prepared {len(features)} training samples")
        return np.array(features), np.array(labels)

    def train_xgboost(self, X: np.ndarray, y: np.ndarray) -> bool:
        """
        Train XGBoost model.

        Args:
            X: Feature matrix
            y: Labels

        Returns:
            True if training successful
        """
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost not installed. Run: pip install xgboost")
            return False

        logger.info("Training XGBoost model...")

        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Create model with optimized parameters
        self.xgb_model = xgb.XGBClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=200,
            objective="multi:softprob",
            num_class=3,
            random_state=42,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            eval_metric="mlogloss",
            early_stopping_rounds=20,
        )

        # Train with early stopping
        self.xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=True)

        # Evaluate
        val_accuracy = self.xgb_model.score(X_val, y_val)
        logger.info(f"XGBoost validation accuracy: {val_accuracy:.4f}")

        return True

    def train_random_forest(self, X: np.ndarray, y: np.ndarray) -> bool:
        """
        Train Random Forest model.

        Args:
            X: Feature matrix
            y: Labels

        Returns:
            True if training successful
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            logger.error("scikit-learn not installed. Run: pip install scikit-learn")
            return False

        logger.info("Training Random Forest model...")

        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Create model
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,  # Use all cores
            class_weight="balanced",
        )

        # Train
        self.rf_model.fit(X_train, y_train)

        # Evaluate
        val_accuracy = self.rf_model.score(X_val, y_val)
        logger.info(f"Random Forest validation accuracy: {val_accuracy:.4f}")

        return True

    def save_models(self) -> dict[str, Path]:
        """
        Save trained models to disk.

        Returns:
            Dictionary with model paths
        """
        paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.xgb_model is not None:
            xgb_path = MODELS_DIR / f"xgboost_{timestamp}.pkl"
            with open(xgb_path, "wb") as f:
                pickle.dump(self.xgb_model, f)
            # Also save as latest
            latest_xgb = MODELS_DIR / "xgboost_latest.pkl"
            with open(latest_xgb, "wb") as f:
                pickle.dump(self.xgb_model, f)
            paths["xgboost"] = xgb_path
            logger.info(f"XGBoost model saved to {xgb_path}")

        if self.rf_model is not None:
            rf_path = MODELS_DIR / f"random_forest_{timestamp}.pkl"
            with open(rf_path, "wb") as f:
                pickle.dump(self.rf_model, f)
            # Also save as latest
            latest_rf = MODELS_DIR / "random_forest_latest.pkl"
            with open(latest_rf, "wb") as f:
                pickle.dump(self.rf_model, f)
            paths["random_forest"] = rf_path
            logger.info(f"Random Forest model saved to {rf_path}")

        # Save feature engineer state for inference
        fe_path = MODELS_DIR / "feature_engineer_state.pkl"
        with open(fe_path, "wb") as f:
            pickle.dump(
                {
                    "team_goals_scored": dict(self.feature_engineer.team_goals_scored),
                    "team_goals_conceded": dict(self.feature_engineer.team_goals_conceded),
                    "team_results": dict(self.feature_engineer.team_results),
                    "head_to_head": {
                        k: dict(v) for k, v in self.feature_engineer.head_to_head.items()
                    },
                },
                f,
            )
        paths["feature_engineer"] = fe_path
        logger.info(f"Feature engineer state saved to {fe_path}")

        return paths

    def train_all(self) -> bool:
        """
        Complete training pipeline.

        Returns:
            True if training successful
        """
        # Load data
        data = self.load_historical_data()
        if not data:
            return False

        matches = data.get("matches", [])
        if not matches:
            logger.error("No matches in historical data")
            return False

        logger.info(f"Loaded {len(matches)} historical matches")

        # Prepare training data
        X, y = self.prepare_training_data(matches)
        if len(X) == 0:
            logger.error("No training samples generated")
            return False

        # Log class distribution
        unique, counts = np.unique(y, return_counts=True)
        logger.info(
            f"Class distribution: Home Win={counts[0]}, Draw={counts[1]}, Away Win={counts[2]}"
        )

        # Train models
        xgb_success = self.train_xgboost(X, y)
        rf_success = self.train_random_forest(X, y)

        if xgb_success or rf_success:
            self.save_models()
            return True

        return False


def train_models_cli() -> None:
    """Command-line interface for training."""
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models")
    parser.add_argument("--data-file", help="Path to historical data file")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    trainer = MLTrainer()

    if args.data_file:
        global HISTORICAL_DATA_FILE
        HISTORICAL_DATA_FILE = Path(args.data_file)

    success = trainer.train_all()

    if success:
        logger.info("Training completed successfully!")
    else:
        logger.error("Training failed")
        exit(1)


if __name__ == "__main__":
    train_models_cli()
