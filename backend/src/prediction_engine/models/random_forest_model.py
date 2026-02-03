"""Random Forest-based prediction model for football match outcomes.

Random Forest is an ensemble of decision trees that captures feature interactions
and is robust to outliers. It serves as a good backup/alternative to XGBoost
for predictions.

Features used:
- home_attack, home_defense: Home team capabilities
- away_attack, away_defense: Away team capabilities
- recent_form_home, recent_form_away: Recent performance
- head_to_head_home: Head-to-head advantage

The model is less prone to overfitting than single decision trees and often
provides different insights than gradient boosting methods.

References:
- Random Forest: https://scikit-learn.org/stable/modules/ensemble.html#forests
- Comparison with XGBoost: https://www.kaggle.com/getting-started/xgboost-vs-random-forest
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - Random Forest predictions will use fallback")


@dataclass
class RandomForestPrediction:
    """Random Forest model prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    prediction_confidence: float
    model_type: str = "random_forest"


class RandomForestModel:
    """
    Random Forest classifier for football match predictions.

    This model uses an ensemble of decision trees to learn patterns in match data.
    It's more interpretable than XGBoost and less sensitive to hyperparameters.

    Model characteristics:
    - Non-linear decision boundaries
    - Robust to outliers
    - Feature importance rankings
    - Handles missing data through mean imputation
    - Lower variance than single trees due to averaging
    """

    # Feature names expected by the model
    FEATURE_NAMES = [
        "home_attack",
        "home_defense",
        "away_attack",
        "away_defense",
        "recent_form_home",
        "recent_form_away",
        "head_to_head_home",
    ]

    # Outcome classes
    OUTCOME_HOME_WIN = 0
    OUTCOME_DRAW = 1
    OUTCOME_AWAY_WIN = 2

    # Default Random Forest parameters
    DEFAULT_PARAMS = {
        "n_estimators": 100,
        "max_depth": 12,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "bootstrap": True,
        "oob_score": True,
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, pretrained_model: object | None = None):
        """
        Initialize Random Forest model.

        Args:
            pretrained_model: Optional pre-trained Random Forest model
        """
        self.model = pretrained_model
        self.is_trained = pretrained_model is not None
        self.feature_importance: dict[str, float] = {}
        self.oob_score: float | None = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict[str, float]:
        """
        Train the Random Forest model on historical match data.

        Args:
            X_train: Training features (N, 7) where 7 = number of features
            y_train: Training outcomes (N,) with values 0=home_win, 1=draw, 2=away_win
            X_val: Validation features (optional, for OOB score comparison)
            y_val: Validation outcomes (optional)

        Returns:
            Dictionary with training metrics
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available - cannot train model")
            return {"oob_score": 0.0, "val_score": 0.0}

        try:
            # Create and train Random Forest
            self.model = RandomForestClassifier(
                n_estimators=self.DEFAULT_PARAMS["n_estimators"],
                max_depth=self.DEFAULT_PARAMS["max_depth"],
                min_samples_split=self.DEFAULT_PARAMS["min_samples_split"],
                min_samples_leaf=self.DEFAULT_PARAMS["min_samples_leaf"],
                max_features=self.DEFAULT_PARAMS["max_features"],
                bootstrap=self.DEFAULT_PARAMS["bootstrap"],
                oob_score=self.DEFAULT_PARAMS["oob_score"],
                random_state=self.DEFAULT_PARAMS["random_state"],
                n_jobs=self.DEFAULT_PARAMS["n_jobs"],
            )

            # Train the model
            self.model.fit(X_train, y_train)

            self.is_trained = True

            # Store OOB score and feature importance
            if hasattr(self.model, "oob_score_"):
                self.oob_score = float(self.model.oob_score_)

            if hasattr(self.model, "feature_importances_"):
                for i, importance in enumerate(self.model.feature_importances_):
                    if i < len(self.FEATURE_NAMES):
                        self.feature_importance[self.FEATURE_NAMES[i]] = float(importance)

            # Validation score if provided
            val_score = 0.0
            if X_val is not None and y_val is not None:
                val_score = float(self.model.score(X_val, y_val))

            metrics = {
                "oob_score": self.oob_score or 0.0,
                "val_score": val_score,
            }

            logger.info(f"Random Forest model trained successfully: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error training Random Forest model: {e}")
            self.is_trained = False
            return {"oob_score": 0.0, "val_score": 0.0}

    def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        recent_form_home: float = 50.0,
        recent_form_away: float = 50.0,
        head_to_head_home: float = 0.0,
    ) -> RandomForestPrediction:
        """
        Make a prediction for a single match.

        Args:
            home_attack: Home team attack strength
            home_defense: Home team defense strength
            away_attack: Away team attack strength
            away_defense: Away team defense strength
            recent_form_home: Home team recent form score (0-100)
            recent_form_away: Away team recent form score (0-100)
            head_to_head_home: Head-to-head advantage for home team (-1.0 to 1.0)

        Returns:
            RandomForestPrediction with probabilities
        """
        # Fallback if model not available
        if not SKLEARN_AVAILABLE or not self.is_trained:
            return self._fallback_prediction(home_attack, home_defense, away_attack, away_defense)

        try:
            # Prepare feature vector
            features = np.array(
                [
                    [
                        home_attack,
                        home_defense,
                        away_attack,
                        away_defense,
                        recent_form_home,
                        recent_form_away,
                        head_to_head_home,
                    ]
                ]
            )

            # Get probability predictions
            probs = self.model.predict_proba(features)[0]

            # Extract probabilities
            home_win_prob = float(probs[self.OUTCOME_HOME_WIN])
            draw_prob = float(probs[self.OUTCOME_DRAW])
            away_win_prob = float(probs[self.OUTCOME_AWAY_WIN])

            # Confidence as max probability
            confidence = float(np.max(probs))

            # Normalize
            total = home_win_prob + draw_prob + away_win_prob
            if total > 0:
                home_win_prob /= total
                draw_prob /= total
                away_win_prob /= total

            return RandomForestPrediction(
                home_win_prob=home_win_prob,
                draw_prob=draw_prob,
                away_win_prob=away_win_prob,
                prediction_confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return self._fallback_prediction(home_attack, home_defense, away_attack, away_defense)

    def predict_batch(self, features: np.ndarray) -> np.ndarray:
        """
        Make predictions for multiple matches in batch.

        Args:
            features: Array of shape (N, 7) with feature vectors

        Returns:
            Array of shape (N, 3) with probabilities
        """
        if not SKLEARN_AVAILABLE or not self.is_trained:
            return np.ones((features.shape[0], 3)) / 3

        try:
            return self.model.predict_proba(features)
        except Exception as e:
            logger.error(f"Error during batch prediction: {e}")
            return np.ones((features.shape[0], 3)) / 3

    def _fallback_prediction(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
    ) -> RandomForestPrediction:
        """Simple fallback prediction using heuristics."""
        home_strength = home_attack / (away_defense + 0.1)
        away_strength = away_attack / (home_defense + 0.1)

        home_win_prob = home_strength / (home_strength + away_strength + 1)
        away_win_prob = away_strength / (home_strength + away_strength + 1)
        draw_prob = 1 / (home_strength + away_strength + 1)

        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total
        else:
            home_win_prob = draw_prob = away_win_prob = 1 / 3

        return RandomForestPrediction(
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            prediction_confidence=0.55,
        )

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance scores."""
        return self.feature_importance.copy()

    def save_model(self, filepath: str) -> bool:
        """Save the trained model to disk."""
        if not self.is_trained or not SKLEARN_AVAILABLE:
            logger.error("Cannot save untrained model")
            return False

        try:
            import joblib

            joblib.dump(self.model, filepath)
            logger.info(f"Model saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """Load a pre-trained model from disk."""
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return False

        try:
            import joblib

            self.model = joblib.load(filepath)
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


# Default instance
random_forest_model = RandomForestModel()
