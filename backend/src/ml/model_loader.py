"""Model loader for trained ML models.

Loads trained XGBoost and Random Forest models for inference.
Provides a unified interface for predictions.

Supports two feature sets:
- Legacy (7 features): attack/defense/form/h2h
- Extended (19 features): + fatigue + interaction features
"""

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Feature set versions
FEATURE_SET_LEGACY = 7
FEATURE_SET_EXTENDED = 19

ML_DIR = Path(__file__).parent
MODELS_DIR = ML_DIR / "trained_models"


class TrainedModelLoader:
    """Loads and manages trained ML models."""

    _instance = None
    _initialized = False

    def __new__(cls) -> "TrainedModelLoader":
        """Singleton pattern for model loading."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize model loader."""
        if TrainedModelLoader._initialized:
            return

        self.xgb_model: Any = None
        self.rf_model: Any = None
        self.feature_state: Any = None
        self._load_models()
        TrainedModelLoader._initialized = True

    def _load_models(self) -> None:
        """Load trained models from disk."""
        # Load XGBoost
        xgb_path = MODELS_DIR / "xgboost_latest.pkl"
        if xgb_path.exists():
            try:
                with open(xgb_path, "rb") as f:
                    self.xgb_model = pickle.load(f)
                logger.info("XGBoost model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load XGBoost model: {e}")

        # Load Random Forest
        rf_path = MODELS_DIR / "random_forest_latest.pkl"
        if rf_path.exists():
            try:
                with open(rf_path, "rb") as f:
                    self.rf_model = pickle.load(f)
                logger.info("Random Forest model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Random Forest model: {e}")

        # Load feature engineer state
        fe_path = MODELS_DIR / "feature_engineer_state.pkl"
        if fe_path.exists():
            try:
                with open(fe_path, "rb") as f:
                    self.feature_state = pickle.load(f)
                logger.info("Feature engineer state loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load feature state: {e}")

    def reload_models(self) -> None:
        """Reload models from disk (useful after retraining)."""
        TrainedModelLoader._initialized = False
        self.xgb_model = None
        self.rf_model = None
        self.feature_state = None
        self._load_models()
        TrainedModelLoader._initialized = True

    def is_trained(self) -> bool:
        """Check if at least one model is trained."""
        return self.xgb_model is not None or self.rf_model is not None

    def has_team_data(self, team_id: int) -> bool:
        """Check if we have historical data for a team."""
        if not self.feature_state:
            return False
        return team_id in self.feature_state.get("team_goals_scored", {})

    def get_team_stats(self, team_id: int) -> dict[str, Any] | None:
        """Get historical stats for a team."""
        if not self.feature_state or not self.has_team_data(team_id):
            return None

        goals_scored = self.feature_state["team_goals_scored"].get(team_id, [])
        goals_conceded = self.feature_state["team_goals_conceded"].get(team_id, [])
        results = self.feature_state["team_results"].get(team_id, [])

        if not goals_scored:
            return None

        # Calculate attack/defense strength
        recent_scored = goals_scored[-10:] if goals_scored else []
        recent_conceded = goals_conceded[-10:] if goals_conceded else []
        recent_results = results[-5:] if results else []

        attack = sum(recent_scored) / len(recent_scored) if recent_scored else 1.3
        defense = sum(recent_conceded) / len(recent_conceded) if recent_conceded else 1.3

        # Form calculation
        form_points = sum(3 if r == 0 else (1 if r == 1 else 0) for r in recent_results)
        max_points = len(recent_results) * 3
        form = (form_points / max_points * 100) if max_points > 0 else 50

        return {
            "attack_strength": attack,
            "defense_strength": defense,
            "form": form,
            "matches_played": len(goals_scored),
        }

    def _get_expected_feature_count(self) -> int:
        """Detect expected feature count from loaded model."""
        # Try XGBoost first
        if self.xgb_model is not None:
            try:
                if hasattr(self.xgb_model, "n_features_in_"):
                    return int(self.xgb_model.n_features_in_)
            except Exception:
                pass

        # Try Random Forest
        if self.rf_model is not None:
            try:
                if hasattr(self.rf_model, "n_features_in_"):
                    return int(self.rf_model.n_features_in_)
            except Exception:
                pass

        # Check feature state for version info
        if self.feature_state and "feature_count" in self.feature_state:
            return int(self.feature_state["feature_count"])

        # Default to legacy
        return FEATURE_SET_LEGACY

    def create_features(
        self,
        home_team_id: int,
        away_team_id: int,
        home_attack: float = 1.3,
        home_defense: float = 1.3,
        away_attack: float = 1.3,
        away_defense: float = 1.3,
        home_form: float = 50.0,
        away_form: float = 50.0,
        # Fatigue features (for extended feature set)
        home_rest_days: float = 0.5,
        home_congestion: float = 0.5,
        away_rest_days: float = 0.5,
        away_congestion: float = 0.5,
    ) -> np.ndarray:
        """
        Create feature vector for prediction.

        Uses historical data if available, otherwise uses provided values.
        Automatically detects if model expects legacy (7) or extended (19) features.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_attack: Home team attack strength
            home_defense: Home team defense strength
            away_attack: Away team attack strength
            away_defense: Away team defense strength
            home_form: Home team form (0-100)
            away_form: Away team form (0-100)
            home_rest_days: Home team rest score (0=fatigued, 1=rested)
            home_congestion: Home team congestion score (0=congested, 1=light)
            away_rest_days: Away team rest score
            away_congestion: Away team congestion score

        Returns:
            Feature array sized for the loaded model
        """
        # Try to use historical data
        if self.feature_state:
            home_stats = self.get_team_stats(home_team_id)
            away_stats = self.get_team_stats(away_team_id)

            if home_stats:
                home_attack = home_stats["attack_strength"]
                home_defense = home_stats["defense_strength"]
                home_form = home_stats["form"]

            if away_stats:
                away_attack = away_stats["attack_strength"]
                away_defense = away_stats["defense_strength"]
                away_form = away_stats["form"]

        # Calculate H2H if available
        h2h = 0.5
        if self.feature_state:
            h2h_data = self.feature_state.get("head_to_head", {})
            if home_team_id in h2h_data and away_team_id in h2h_data[home_team_id]:
                results = h2h_data[home_team_id][away_team_id]
                if results:
                    wins = sum(1 for r in results if r == 0)
                    draws = sum(1 for r in results if r == 1)
                    points = wins * 3 + draws
                    h2h = points / (len(results) * 3)

        # Normalize form to 0-1
        home_form_norm = home_form / 100.0
        away_form_norm = away_form / 100.0

        # Check which feature set the model expects
        expected_features = self._get_expected_feature_count()

        if expected_features >= FEATURE_SET_EXTENDED:
            # Extended feature set (19 features)
            # Base features (7)
            base = [
                home_attack,
                home_defense,
                away_attack,
                away_defense,
                home_form_norm,
                away_form_norm,
                h2h,
            ]

            # Fatigue features (4)
            fatigue = [
                home_rest_days,
                home_congestion,
                away_rest_days,
                away_congestion,
            ]

            # Interaction features (8)
            home_fatigue_combined = (home_rest_days + home_congestion) / 2
            away_fatigue_combined = (away_rest_days + away_congestion) / 2

            interactions = [
                home_attack - away_defense,  # attack_vs_defense_home
                away_attack - home_defense,  # attack_vs_defense_away
                home_form_norm - away_form_norm,  # form_differential
                home_attack * home_form_norm,  # home_attack_form
                away_attack * away_form_norm,  # away_attack_form
                home_fatigue_combined - away_fatigue_combined,  # fatigue_advantage
                home_attack * home_fatigue_combined,  # home_attack_fatigue
                away_attack * away_fatigue_combined,  # away_attack_fatigue
            ]

            return np.array([base + fatigue + interactions])

        else:
            # Legacy feature set (7 features)
            return np.array(
                [
                    [
                        home_attack,
                        home_defense,
                        away_attack,
                        away_defense,
                        home_form_norm,
                        away_form_norm,
                        h2h,
                    ]
                ]
            )

    def predict_xgboost(self, features: np.ndarray) -> tuple[np.ndarray, float] | None:
        """
        Make prediction with XGBoost model.

        Args:
            features: Feature vector

        Returns:
            Tuple of (probabilities, confidence) or None
        """
        if self.xgb_model is None:
            return None

        try:
            probs = self.xgb_model.predict_proba(features)[0]
            confidence = float(max(probs))
            return probs, confidence
        except Exception as e:
            logger.error(f"XGBoost prediction failed: {e}")
            return None

    def predict_random_forest(self, features: np.ndarray) -> tuple[np.ndarray, float] | None:
        """
        Make prediction with Random Forest model.

        Args:
            features: Feature vector

        Returns:
            Tuple of (probabilities, confidence) or None
        """
        if self.rf_model is None:
            return None

        try:
            probs = self.rf_model.predict_proba(features)[0]
            confidence = float(max(probs))
            return probs, confidence
        except Exception as e:
            logger.error(f"Random Forest prediction failed: {e}")
            return None

    def predict_ensemble(
        self,
        home_team_id: int,
        away_team_id: int,
        home_attack: float = 1.3,
        home_defense: float = 1.3,
        away_attack: float = 1.3,
        away_defense: float = 1.3,
        home_form: float = 50.0,
        away_form: float = 50.0,
        xgb_weight: float = 0.7,
        rf_weight: float = 0.3,
        # Fatigue features (for extended feature set)
        home_rest_days: float = 0.5,
        home_congestion: float = 0.5,
        away_rest_days: float = 0.5,
        away_congestion: float = 0.5,
    ) -> dict[str, Any] | None:
        """
        Make ensemble prediction combining both models.

        Returns:
            Dictionary with probabilities and metadata
        """
        features = self.create_features(
            home_team_id,
            away_team_id,
            home_attack,
            home_defense,
            away_attack,
            away_defense,
            home_form,
            away_form,
            home_rest_days,
            home_congestion,
            away_rest_days,
            away_congestion,
        )

        xgb_result = self.predict_xgboost(features)
        rf_result = self.predict_random_forest(features)

        if xgb_result is None and rf_result is None:
            return None

        # Combine predictions
        if xgb_result is not None and rf_result is not None:
            xgb_probs, xgb_conf = xgb_result
            rf_probs, rf_conf = rf_result

            # Weighted average
            combined_probs = xgb_probs * xgb_weight + rf_probs * rf_weight
            combined_probs = combined_probs / combined_probs.sum()  # Normalize

            confidence = xgb_conf * xgb_weight + rf_conf * rf_weight
            model_used = "ensemble"

        elif xgb_result is not None:
            combined_probs, confidence = xgb_result
            model_used = "xgboost"

        else:
            assert rf_result is not None  # Guaranteed by earlier None check
            combined_probs, confidence = rf_result
            model_used = "random_forest"

        return {
            "home_win": float(combined_probs[0]),
            "draw": float(combined_probs[1]),
            "away_win": float(combined_probs[2]),
            "confidence": float(confidence),
            "model_used": model_used,
            "is_trained_model": True,
            "feature_count": self._get_expected_feature_count(),
            "uses_fatigue_features": self._get_expected_feature_count() >= FEATURE_SET_EXTENDED,
        }


# Global instance
model_loader = TrainedModelLoader()


def get_ml_prediction(
    home_team_id: int,
    away_team_id: int,
    home_attack: float = 1.3,
    home_defense: float = 1.3,
    away_attack: float = 1.3,
    away_defense: float = 1.3,
    home_form: float = 50.0,
    away_form: float = 50.0,
    # Fatigue features (for extended feature set)
    home_rest_days: float = 0.5,
    home_congestion: float = 0.5,
    away_rest_days: float = 0.5,
    away_congestion: float = 0.5,
) -> dict[str, Any] | None:
    """
    Convenience function to get ML prediction.

    Falls back to None if no trained models available.
    Supports both legacy (7 features) and extended (19 features) models.
    """
    if not model_loader.is_trained():
        return None

    return model_loader.predict_ensemble(
        home_team_id,
        away_team_id,
        home_attack,
        home_defense,
        away_attack,
        away_defense,
        home_form,
        away_form,
        home_rest_days=home_rest_days,
        home_congestion=home_congestion,
        away_rest_days=away_rest_days,
        away_congestion=away_congestion,
    )
