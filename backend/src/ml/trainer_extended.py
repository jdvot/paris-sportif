"""Extended ML Model Trainer with fatigue features.

Trains XGBoost and Random Forest models on historical match data
using the extended 19-feature set including fatigue metrics.

Run with: cd backend && uv run python -m src.ml.trainer_extended
"""

import json
import logging
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Paths
ML_DIR = Path(__file__).parent
DATA_DIR = ML_DIR / "data"
MODELS_DIR = ML_DIR / "trained_models"
HISTORICAL_DATA_FILE = DATA_DIR / "historical_matches.json"

# Feature set constants (must match model_loader.py)
FEATURE_SET_LEGACY = 7
FEATURE_SET_EXTENDED = 19

# Ensure directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class ExtendedFeatureEngineer:
    """Creates extended ML features including fatigue metrics."""

    # Congestion window for calculating fixture density
    CONGESTION_WINDOW_DAYS = 14

    def __init__(self) -> None:
        """Initialize feature engineering with team history tracking."""
        # Track team statistics over time
        self.team_goals_scored: defaultdict[Any, list[int]] = defaultdict(list)
        self.team_goals_conceded: defaultdict[Any, list[int]] = defaultdict(list)
        self.team_results: defaultdict[Any, list[int]] = defaultdict(list)
        self.head_to_head: defaultdict[Any, defaultdict[Any, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # Track match dates for fatigue calculation
        self.team_match_dates: defaultdict[Any, list[datetime]] = defaultdict(list)

    def reset(self) -> None:
        """Reset all tracked statistics."""
        self.team_goals_scored.clear()
        self.team_goals_conceded.clear()
        self.team_results.clear()
        self.head_to_head.clear()
        self.team_match_dates.clear()

    def calculate_form(self, results: list[int], last_n: int = 5) -> float:
        """Calculate team form from recent results (0-100)."""
        if not results:
            return 50.0
        recent = results[-last_n:]
        points = sum(3 if r == 0 else (1 if r == 1 else 0) for r in recent)
        max_points = len(recent) * 3
        return (points / max_points) * 100 if max_points > 0 else 50.0

    def calculate_attack_strength(self, goals_scored: list[int], last_n: int = 10) -> float:
        """Calculate attack strength from recent goals scored."""
        if not goals_scored:
            return 1.3
        recent = goals_scored[-last_n:]
        return sum(recent) / len(recent) if recent else 1.3

    def calculate_defense_strength(self, goals_conceded: list[int], last_n: int = 10) -> float:
        """Calculate defense strength from recent goals conceded."""
        if not goals_conceded:
            return 1.3
        recent = goals_conceded[-last_n:]
        return sum(recent) / len(recent) if recent else 1.3

    def calculate_h2h(self, team1_id: int, team2_id: int) -> float:
        """Calculate head-to-head advantage (0-1, 0.5 = neutral)."""
        h2h = self.head_to_head[team1_id][team2_id]
        if not h2h:
            return 0.5
        wins = sum(1 for r in h2h if r == 0)
        draws = sum(1 for r in h2h if r == 1)
        points = wins * 3 + draws
        max_points = len(h2h) * 3
        return points / max_points if max_points > 0 else 0.5

    def calculate_rest_days_score(
        self, team_id: int, match_date: datetime, optimal_rest: int = 5, max_rest: int = 14
    ) -> float:
        """
        Calculate rest days score for a team before a match.

        Returns:
            Score 0-1 (0=fatigued, 1=well-rested)
        """
        dates = self.team_match_dates[team_id]
        if not dates:
            return 0.5  # Neutral if no history

        # Find last match before this date
        past_matches = [d for d in dates if d < match_date]
        if not past_matches:
            return 0.5

        last_match = max(past_matches)
        rest_days = (match_date - last_match).days

        # Normalize: 0-2 days = fatigued, 5+ days = well rested
        if rest_days <= 2:
            return 0.2  # Very fatigued
        elif rest_days <= 3:
            return 0.4
        elif rest_days <= 4:
            return 0.6
        elif rest_days <= optimal_rest:
            return 0.8
        elif rest_days <= max_rest:
            return 1.0  # Well rested
        else:
            return 0.9  # Too long without match (slight negative)

    def calculate_congestion_score(self, team_id: int, match_date: datetime) -> float:
        """
        Calculate fixture congestion score.

        Returns:
            Score 0-1 (0=congested, 1=light schedule)
        """
        dates = self.team_match_dates[team_id]
        if not dates:
            return 0.5

        # Count matches in the window before this date
        window_start = match_date - timedelta(days=self.CONGESTION_WINDOW_DAYS)
        matches_in_window = sum(1 for d in dates if window_start <= d < match_date)

        # Normalize: 0-1 matches = light, 5+ = very congested
        if matches_in_window <= 1:
            return 1.0
        elif matches_in_window == 2:
            return 0.8
        elif matches_in_window == 3:
            return 0.6
        elif matches_in_window == 4:
            return 0.4
        else:
            return 0.2  # Very congested

    def create_features(
        self, home_team_id: int, away_team_id: int, match_date: datetime | None = None
    ) -> np.ndarray:
        """
        Create extended feature vector (19 features).

        Base features (7):
            0. home_attack
            1. home_defense
            2. away_attack
            3. away_defense
            4. home_form (normalized 0-1)
            5. away_form (normalized 0-1)
            6. h2h_advantage

        Fatigue features (4):
            7. home_rest_days_score
            8. home_congestion_score
            9. away_rest_days_score
            10. away_congestion_score

        Interaction features (8):
            11. attack_vs_defense_home (home_attack - away_defense)
            12. attack_vs_defense_away (away_attack - home_defense)
            13. form_differential (home_form - away_form)
            14. home_attack_form (home_attack * home_form)
            15. away_attack_form (away_attack * away_form)
            16. fatigue_advantage (home_fatigue - away_fatigue)
            17. home_attack_fatigue (home_attack * home_fatigue)
            18. away_attack_fatigue (away_attack * away_fatigue)
        """
        # Base features
        home_attack = self.calculate_attack_strength(self.team_goals_scored[home_team_id])
        home_defense = self.calculate_defense_strength(self.team_goals_conceded[home_team_id])
        away_attack = self.calculate_attack_strength(self.team_goals_scored[away_team_id])
        away_defense = self.calculate_defense_strength(self.team_goals_conceded[away_team_id])
        home_form = self.calculate_form(self.team_results[home_team_id]) / 100.0
        away_form = self.calculate_form(self.team_results[away_team_id]) / 100.0
        h2h = self.calculate_h2h(home_team_id, away_team_id)

        # Fatigue features
        if match_date:
            home_rest = self.calculate_rest_days_score(home_team_id, match_date)
            home_cong = self.calculate_congestion_score(home_team_id, match_date)
            away_rest = self.calculate_rest_days_score(away_team_id, match_date)
            away_cong = self.calculate_congestion_score(away_team_id, match_date)
        else:
            home_rest = home_cong = away_rest = away_cong = 0.5

        # Combined fatigue scores
        home_fatigue = (home_rest + home_cong) / 2
        away_fatigue = (away_rest + away_cong) / 2

        # Interaction features
        attack_vs_defense_home = home_attack - away_defense
        attack_vs_defense_away = away_attack - home_defense
        form_differential = home_form - away_form
        home_attack_form = home_attack * home_form
        away_attack_form = away_attack * away_form
        fatigue_advantage = home_fatigue - away_fatigue
        home_attack_fatigue = home_attack * home_fatigue
        away_attack_fatigue = away_attack * away_fatigue

        return np.array(
            [
                # Base (7)
                home_attack,
                home_defense,
                away_attack,
                away_defense,
                home_form,
                away_form,
                h2h,
                # Fatigue (4)
                home_rest,
                home_cong,
                away_rest,
                away_cong,
                # Interactions (8)
                attack_vs_defense_home,
                attack_vs_defense_away,
                form_differential,
                home_attack_form,
                away_attack_form,
                fatigue_advantage,
                home_attack_fatigue,
                away_attack_fatigue,
            ]
        )

    def update_after_match(
        self,
        home_team_id: int,
        away_team_id: int,
        home_goals: int,
        away_goals: int,
        result: int,
        match_date: datetime,
    ) -> None:
        """Update team statistics after a match."""
        # Update goals
        self.team_goals_scored[home_team_id].append(home_goals)
        self.team_goals_conceded[home_team_id].append(away_goals)
        self.team_goals_scored[away_team_id].append(away_goals)
        self.team_goals_conceded[away_team_id].append(home_goals)

        # Update results
        self.team_results[home_team_id].append(result)
        away_result = 2 if result == 0 else (0 if result == 2 else 1)
        self.team_results[away_team_id].append(away_result)

        # Update H2H
        self.head_to_head[home_team_id][away_team_id].append(result)
        self.head_to_head[away_team_id][home_team_id].append(away_result)

        # Update match dates for fatigue tracking
        self.team_match_dates[home_team_id].append(match_date)
        self.team_match_dates[away_team_id].append(match_date)

    @staticmethod
    def get_feature_names() -> list[str]:
        """Get feature names for interpretability."""
        return [
            # Base
            "home_attack",
            "home_defense",
            "away_attack",
            "away_defense",
            "home_form",
            "away_form",
            "h2h",
            # Fatigue
            "home_rest_days",
            "home_congestion",
            "away_rest_days",
            "away_congestion",
            # Interactions
            "attack_vs_defense_home",
            "attack_vs_defense_away",
            "form_differential",
            "home_attack_form",
            "away_attack_form",
            "fatigue_advantage",
            "home_attack_fatigue",
            "away_attack_fatigue",
        ]


class ExtendedMLTrainer:
    """Trains ML models with extended 19-feature set."""

    def __init__(self) -> None:
        """Initialize trainer."""
        self.feature_engineer = ExtendedFeatureEngineer()
        self.xgb_model: Any = None
        self.rf_model: Any = None

    def load_historical_data(self) -> dict[str, Any] | None:
        """Load historical match data."""
        if not HISTORICAL_DATA_FILE.exists():
            logger.error(f"No historical data found at {HISTORICAL_DATA_FILE}")
            logger.info("Run: cd backend && uv run python -m src.ml.data_collector")
            return None

        with open(HISTORICAL_DATA_FILE, encoding="utf-8") as f:
            return json.load(f)

    def prepare_training_data(
        self, matches: list[dict[str, Any]], min_history: int = 5
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data with extended features.

        Processes matches chronologically to avoid data leakage.
        """
        # Sort by date
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

            # Parse match date
            try:
                match_date = datetime.fromisoformat(match["date"].replace("Z", "+00:00"))
                match_date = match_date.replace(tzinfo=None)
            except (ValueError, AttributeError):
                continue

            # Only create training example if both teams have enough history
            if (
                team_match_count[home_id] >= min_history
                and team_match_count[away_id] >= min_history
            ):
                # Create features BEFORE updating stats
                feature_vec = self.feature_engineer.create_features(home_id, away_id, match_date)
                features.append(feature_vec)
                labels.append(result)

            # Update stats AFTER creating features
            self.feature_engineer.update_after_match(
                home_id, away_id, home_goals, away_goals, result, match_date
            )
            team_match_count[home_id] += 1
            team_match_count[away_id] += 1

        logger.info(
            f"Prepared {len(features)} training samples with {FEATURE_SET_EXTENDED} features"
        )
        return np.array(features), np.array(labels)

    def train_xgboost(self, X: np.ndarray, y: np.ndarray) -> bool:
        """Train XGBoost model with extended features."""
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost not installed. Run: pip install xgboost")
            return False

        logger.info(f"Training XGBoost model ({X.shape[1]} features)...")

        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Optimized parameters for extended features
        self.xgb_model = xgb.XGBClassifier(
            max_depth=7,  # Slightly deeper for more features
            learning_rate=0.08,
            n_estimators=300,
            objective="multi:softprob",
            num_class=3,
            random_state=42,
            subsample=0.8,
            colsample_bytree=0.7,  # Feature sampling
            min_child_weight=2,
            eval_metric="mlogloss",
            early_stopping_rounds=30,
            reg_alpha=0.1,  # L1 regularization
            reg_lambda=1.0,  # L2 regularization
        )

        # Train with early stopping
        self.xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=True)

        # Evaluate
        val_accuracy = self.xgb_model.score(X_val, y_val)
        logger.info(f"XGBoost validation accuracy: {val_accuracy:.4f}")

        # Log feature importance
        self._log_feature_importance(self.xgb_model, "XGBoost")

        return True

    def train_random_forest(self, X: np.ndarray, y: np.ndarray) -> bool:
        """Train Random Forest model with extended features."""
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            logger.error("scikit-learn not installed")
            return False

        logger.info(f"Training Random Forest model ({X.shape[1]} features)...")

        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Optimized parameters
        self.rf_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_split=8,
            min_samples_leaf=4,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )

        self.rf_model.fit(X_train, y_train)

        # Evaluate
        val_accuracy = self.rf_model.score(X_val, y_val)
        logger.info(f"Random Forest validation accuracy: {val_accuracy:.4f}")

        # Log feature importance
        self._log_feature_importance(self.rf_model, "Random Forest")

        return True

    def _log_feature_importance(self, model: Any, model_name: str) -> None:
        """Log feature importance for interpretability."""
        try:
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                feature_names = ExtendedFeatureEngineer.get_feature_names()

                # Sort by importance
                indices = np.argsort(importances)[::-1]

                logger.info(f"\n{model_name} Feature Importance:")
                logger.info("-" * 40)
                for i in range(min(10, len(indices))):  # Top 10
                    idx = indices[i]
                    logger.info(f"  {feature_names[idx]}: {importances[idx]:.4f}")
        except Exception as e:
            logger.warning(f"Could not log feature importance: {e}")

    def save_models(self) -> dict[str, Path]:
        """Save trained models with feature count metadata."""
        paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.xgb_model is not None:
            xgb_path = MODELS_DIR / f"xgboost_extended_{timestamp}.pkl"
            with open(xgb_path, "wb") as f:
                pickle.dump(self.xgb_model, f)
            # Also save as latest
            latest_xgb = MODELS_DIR / "xgboost_latest.pkl"
            with open(latest_xgb, "wb") as f:
                pickle.dump(self.xgb_model, f)
            paths["xgboost"] = xgb_path
            logger.info(f"XGBoost model saved to {xgb_path}")

        if self.rf_model is not None:
            rf_path = MODELS_DIR / f"random_forest_extended_{timestamp}.pkl"
            with open(rf_path, "wb") as f:
                pickle.dump(self.rf_model, f)
            # Also save as latest
            latest_rf = MODELS_DIR / "random_forest_latest.pkl"
            with open(latest_rf, "wb") as f:
                pickle.dump(self.rf_model, f)
            paths["random_forest"] = rf_path
            logger.info(f"Random Forest model saved to {rf_path}")

        # Save feature engineer state with feature count
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
                    "team_match_dates": {
                        k: [d.isoformat() for d in v]
                        for k, v in self.feature_engineer.team_match_dates.items()
                    },
                    # Important: Store feature count for model_loader
                    "feature_count": FEATURE_SET_EXTENDED,
                    "feature_names": ExtendedFeatureEngineer.get_feature_names(),
                    "trained_at": datetime.now().isoformat(),
                },
                f,
            )
        paths["feature_engineer"] = fe_path
        logger.info(f"Feature engineer state saved (feature_count={FEATURE_SET_EXTENDED})")

        return paths

    def train_all(self) -> bool:
        """Complete training pipeline."""
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
        logger.info(f"Class distribution: Home={counts[0]}, Draw={counts[1]}, Away={counts[2]}")

        # Train models
        xgb_success = self.train_xgboost(X, y)
        rf_success = self.train_random_forest(X, y)

        if xgb_success or rf_success:
            self.save_models()
            logger.info("\n" + "=" * 50)
            logger.info("TRAINING COMPLETE")
            logger.info(f"Feature set: EXTENDED ({FEATURE_SET_EXTENDED} features)")
            logger.info("Models saved to: src/ml/trained_models/")
            logger.info("=" * 50)
            return True

        return False


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models with extended features")
    parser.add_argument("--data-file", help="Path to historical data file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    trainer = ExtendedMLTrainer()

    if args.data_file:
        global HISTORICAL_DATA_FILE
        HISTORICAL_DATA_FILE = Path(args.data_file)

    success = trainer.train_all()

    if success:
        logger.info("Training completed successfully!")
        logger.info("Run tests: cd backend && uv run pytest tests/test_models.py -v -k ModelLoader")
    else:
        logger.error("Training failed. Check logs for details.")
        exit(1)


if __name__ == "__main__":
    main()
