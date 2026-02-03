"""XGBoost-based prediction model for football match outcomes.

XGBoost is a gradient boosting library that captures complex feature interactions
and non-linear relationships in football data.

Features used:
- home_attack, home_defense: Home team attacking and defensive capabilities
- away_attack, away_defense: Away team attacking and defensive capabilities
- recent_form: Recent performance trend (0-100 scale)
- head_to_head: Historical head-to-head record against opponent

The model trains on historical match data and outputs probabilities for
home_win, draw, and away_win outcomes.

Calibration:
- Supports Platt scaling and isotonic regression for probability calibration
- Improves reliability of predicted probabilities

References:
- XGBoost: https://xgboost.readthedocs.io/
- Application to sports: https://www.sas.com/en_us/insights/analytics/xgboost.html
"""

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available - predictions will use fallback")


@dataclass
class XGBoostPrediction:
    """XGBoost model prediction result."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    prediction_confidence: float
    model_type: str = "xgboost"


@dataclass
class ExplainedPrediction:
    """XGBoost prediction with feature explanations."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    prediction_confidence: float
    predicted_outcome: str
    explanations: list[dict]
    model_type: str = "xgboost_explained"


class XGBoostModel:
    """
    XGBoost gradient boosting model for football match predictions.

    This model learns patterns from historical match data to predict outcomes.
    It handles feature interactions and non-linear relationships better than
    linear models.

    Model characteristics:
    - Trained on historical match features
    - Outputs probabilities for 3 outcomes (win/draw/loss)
    - Uses multi-class classification with softmax output
    - Handles missing data gracefully
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

    # Default XGBoost parameters (optimized for football predictions)
    DEFAULT_PARAMS = {
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "objective": "multi:softprob" if XGBOOST_AVAILABLE else None,
        "num_class": 3,
        "random_state": 42,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 1,
        "gamma": 0,
    }

    def __init__(
        self,
        pretrained_model: object | None = None,
        calibration_method: Literal["platt", "isotonic", "none"] = "none",
    ):
        """
        Initialize XGBoost model.

        Args:
            pretrained_model: Optional pre-trained XGBoost model to use directly
            calibration_method: Calibration method ('platt', 'isotonic', or 'none')
        """
        self.model = pretrained_model
        self.is_trained = pretrained_model is not None
        self.feature_importance: dict[str, float] = {}
        self.training_history: dict[str, list[float]] = {"loss": [], "validation": []}
        self.calibration_method = calibration_method
        self.calibrator: object | None = None
        self.is_calibrated = False

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        early_stopping_rounds: int = 20,
    ) -> dict[str, list[float]]:
        """
        Train the XGBoost model on historical match data.

        Args:
            X_train: Training features (N, 7) where 7 = number of features
            y_train: Training outcomes (N,) with values 0=home_win, 1=draw, 2=away_win
            X_val: Validation features for early stopping
            y_val: Validation outcomes
            early_stopping_rounds: Rounds without improvement before stopping

        Returns:
            Training history with loss values
        """
        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not available - cannot train model")
            return {"loss": [], "validation": []}

        try:
            # Prepare evaluation set if validation data provided
            eval_set = None
            if X_val is not None and y_val is not None:
                eval_set = [(X_val, y_val)]

            # Create and train XGBoost classifier
            # Note: early_stopping_rounds moved to constructor in XGBoost 2.0+
            self.model = xgb.XGBClassifier(
                max_depth=self.DEFAULT_PARAMS["max_depth"],
                learning_rate=self.DEFAULT_PARAMS["learning_rate"],
                n_estimators=self.DEFAULT_PARAMS["n_estimators"],
                random_state=self.DEFAULT_PARAMS["random_state"],
                subsample=self.DEFAULT_PARAMS["subsample"],
                colsample_bytree=self.DEFAULT_PARAMS["colsample_bytree"],
                min_child_weight=self.DEFAULT_PARAMS["min_child_weight"],
                gamma=self.DEFAULT_PARAMS["gamma"],
                eval_metric="mlogloss",
                early_stopping_rounds=early_stopping_rounds if eval_set else None,
            )

            # Train model
            self.model.fit(  # type: ignore[union-attr]
                X_train,
                y_train,
                eval_set=eval_set,
                verbose=False,
            )

            self.is_trained = True

            # Store feature importance
            if hasattr(self.model, "feature_importances_"):
                for i, importance in enumerate(self.model.feature_importances_):
                    if i < len(self.FEATURE_NAMES):
                        self.feature_importance[self.FEATURE_NAMES[i]] = float(importance)

            logger.info("XGBoost model trained successfully")
            return self.training_history

        except Exception as e:
            logger.error(f"Error training XGBoost model: {e}")
            self.is_trained = False
            return {"loss": [], "validation": []}

    def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        recent_form_home: float = 50.0,
        recent_form_away: float = 50.0,
        head_to_head_home: float = 0.0,
    ) -> XGBoostPrediction:
        """
        Make a prediction for a single match.

        Args:
            home_attack: Home team attack strength (0-100 scale, typically 0.5-3.0)
            home_defense: Home team defense strength (0-100 scale, typically 0.5-3.0)
            away_attack: Away team attack strength (0-100 scale, typically 0.5-3.0)
            away_defense: Away team defense strength (0-100 scale, typically 0.5-3.0)
            recent_form_home: Home team recent form score (0-100)
            recent_form_away: Away team recent form score (0-100)
            head_to_head_home: Head-to-head advantage for home team (-1.0 to 1.0)

        Returns:
            XGBoostPrediction with probabilities for all outcomes
        """
        # If model not available or not trained, return neutral prediction
        if not XGBOOST_AVAILABLE or not self.is_trained:
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
            probs = self.model.predict_proba(features)[0]  # type: ignore[union-attr]

            # Extract probabilities for each outcome
            home_win_prob = float(probs[self.OUTCOME_HOME_WIN])
            draw_prob = float(probs[self.OUTCOME_DRAW])
            away_win_prob = float(probs[self.OUTCOME_AWAY_WIN])

            # Calculate confidence as max probability
            confidence = float(np.max(probs))

            # Normalize probabilities to ensure they sum to 1
            total = home_win_prob + draw_prob + away_win_prob
            if total > 0:
                home_win_prob /= total
                draw_prob /= total
                away_win_prob /= total

            return XGBoostPrediction(
                home_win_prob=home_win_prob,
                draw_prob=draw_prob,
                away_win_prob=away_win_prob,
                prediction_confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return self._fallback_prediction(home_attack, home_defense, away_attack, away_defense)

    def predict_batch(
        self,
        features: np.ndarray,
    ) -> np.ndarray:
        """
        Make predictions for multiple matches in batch.

        Args:
            features: Array of shape (N, 7) with feature vectors

        Returns:
            Array of shape (N, 3) with probabilities for each outcome
        """
        if not XGBOOST_AVAILABLE or not self.is_trained:
            # Fallback: return neutral predictions
            return np.ones((features.shape[0], 3)) / 3

        try:
            return self.model.predict_proba(features)  # type: ignore[union-attr, no-any-return]
        except Exception as e:
            logger.error(f"Error during batch prediction: {e}")
            return np.ones((features.shape[0], 3)) / 3

    def _fallback_prediction(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
    ) -> XGBoostPrediction:
        """
        Fallback prediction using simple heuristics when model unavailable.

        Uses attack/defense strength ratio to estimate probabilities.
        """
        # Simple prediction based on attack vs defense
        home_strength = home_attack / (away_defense + 0.1)
        away_strength = away_attack / (home_defense + 0.1)

        # Apply sigmoid-like transformation
        home_win_prob = home_strength / (home_strength + away_strength + 1)
        away_win_prob = away_strength / (home_strength + away_strength + 1)
        draw_prob = 1 / (home_strength + away_strength + 1)

        # Normalize
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total
        else:
            home_win_prob = draw_prob = away_win_prob = 1 / 3

        confidence = 0.55  # Low confidence for fallback

        return XGBoostPrediction(
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            prediction_confidence=confidence,
        )

    def get_feature_importance(self) -> dict[str, float]:
        """
        Get feature importance scores from the trained model.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        return self.feature_importance.copy()

    def save_model(self, filepath: str) -> bool:
        """
        Save the trained model to disk.

        Args:
            filepath: Path where to save the model

        Returns:
            True if successful, False otherwise
        """
        if not self.is_trained or not XGBOOST_AVAILABLE:
            logger.error("Cannot save untrained model")
            return False

        try:
            self.model.save_model(filepath)  # type: ignore[union-attr]
            logger.info(f"Model saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """
        Load a pre-trained model from disk.

        Args:
            filepath: Path to the saved model

        Returns:
            True if successful, False otherwise
        """
        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not available - cannot load model")
            return False

        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(filepath)  # type: ignore[union-attr]
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def fit_calibration(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        method: Literal["platt", "isotonic"] | None = None,
    ) -> dict[str, float]:
        """
        Fit calibration on validation data.

        Args:
            X_val: Validation features
            y_val: Validation labels (0=home, 1=draw, 2=away)
            method: Calibration method (uses instance default if not specified)

        Returns:
            Dict with calibration metrics (brier_before, brier_after, ece_before, ece_after)
        """
        if not self.is_trained:
            logger.error("Model must be trained before calibration")
            return {}

        from src.prediction_engine.calibration import ProbabilityCalibrator

        cal_method = method or self.calibration_method
        if cal_method == "none":
            cal_method = "isotonic"  # Default to isotonic

        try:
            # Get uncalibrated predictions
            uncalibrated_probs = self.model.predict_proba(X_val)  # type: ignore[union-attr]

            # Fit calibrator
            self.calibrator = ProbabilityCalibrator(method=cal_method)  # type: ignore[arg-type]
            pre_metrics = self.calibrator.fit(uncalibrated_probs, y_val)  # type: ignore[union-attr]

            # Evaluate improvement
            _, post_metrics = self.calibrator.evaluate(uncalibrated_probs, y_val)  # type: ignore[union-attr]

            self.is_calibrated = True
            self.calibration_method = cal_method  # type: ignore[assignment]

            improvement = {
                "brier_before": pre_metrics.brier_score,
                "brier_after": post_metrics.brier_score,
                "brier_improvement": pre_metrics.brier_score - post_metrics.brier_score,
                "ece_before": pre_metrics.expected_calibration_error,
                "ece_after": post_metrics.expected_calibration_error,
                "ece_improvement": (
                    pre_metrics.expected_calibration_error
                    - post_metrics.expected_calibration_error
                ),
                "n_samples": pre_metrics.n_samples,
            }

            logger.info(
                f"Calibration fitted: Brier {improvement['brier_before']:.4f} -> "
                f"{improvement['brier_after']:.4f}, ECE {improvement['ece_before']:.4f} -> "
                f"{improvement['ece_after']:.4f}"
            )

            return improvement

        except Exception as e:
            logger.error(f"Error fitting calibration: {e}")
            return {}

    def predict_calibrated(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        recent_form_home: float = 50.0,
        recent_form_away: float = 50.0,
        head_to_head_home: float = 0.0,
    ) -> XGBoostPrediction:
        """
        Make a calibrated prediction for a single match.

        Falls back to uncalibrated prediction if calibrator not fitted.
        """
        # Get base prediction
        pred = self.predict(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
            recent_form_home=recent_form_home,
            recent_form_away=recent_form_away,
            head_to_head_home=head_to_head_home,
        )

        # Apply calibration if available
        if self.is_calibrated and self.calibrator is not None:
            try:
                calibrated = self.calibrator.calibrate(  # type: ignore[union-attr]
                    pred.home_win_prob,
                    pred.draw_prob,
                    pred.away_win_prob,
                )
                return XGBoostPrediction(
                    home_win_prob=calibrated.home_win_prob,
                    draw_prob=calibrated.draw_prob,
                    away_win_prob=calibrated.away_win_prob,
                    prediction_confidence=max(
                        calibrated.home_win_prob,
                        calibrated.draw_prob,
                        calibrated.away_win_prob,
                    ),
                    model_type="xgboost_calibrated",
                )
            except Exception as e:
                logger.warning(f"Calibration failed, using raw prediction: {e}")

        return pred

    def predict_batch_calibrated(
        self,
        features: np.ndarray,
    ) -> np.ndarray:
        """
        Make calibrated predictions for multiple matches.

        Args:
            features: Array of shape (N, 7) with feature vectors

        Returns:
            Array of shape (N, 3) with calibrated probabilities
        """
        # Get base predictions
        probs = self.predict_batch(features)

        # Apply calibration if available
        if self.is_calibrated and self.calibrator is not None:
            try:
                probs = self.calibrator.calibrate_batch(probs)  # type: ignore[union-attr]
            except Exception as e:
                logger.warning(f"Batch calibration failed: {e}")

        return probs

    def predict_explained(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        recent_form_home: float = 50.0,
        recent_form_away: float = 50.0,
        head_to_head_home: float = 0.0,
        top_n: int = 5,
    ) -> ExplainedPrediction:
        """
        Make a prediction with feature explanations.

        Args:
            home_attack: Home team attack strength
            home_defense: Home team defense strength
            away_attack: Away team attack strength
            away_defense: Away team defense strength
            recent_form_home: Home team recent form (0-100)
            recent_form_away: Away team recent form (0-100)
            head_to_head_home: Head-to-head advantage (-1 to 1)
            top_n: Number of top contributing features to include

        Returns:
            ExplainedPrediction with probabilities and feature explanations
        """
        from src.prediction_engine.explainability import PredictionExplainer

        # Get base prediction
        pred = self.predict(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
            recent_form_home=recent_form_home,
            recent_form_away=recent_form_away,
            head_to_head_home=head_to_head_home,
        )

        # Get explanation
        explainer = PredictionExplainer(self.model)
        explanation = explainer.explain(
            home_attack=home_attack,
            home_defense=home_defense,
            away_attack=away_attack,
            away_defense=away_defense,
            recent_form_home=recent_form_home,
            recent_form_away=recent_form_away,
            head_to_head_home=head_to_head_home,
        )

        # Get top contributing features
        top_features = explanation.top_features(top_n)
        explanations_list = [
            {
                "feature": f.feature,
                "contribution": round(f.contribution, 4),
                "value": round(f.value, 3),
                "rank": f.importance_rank,
            }
            for f in top_features
        ]

        return ExplainedPrediction(
            home_win_prob=pred.home_win_prob,
            draw_prob=pred.draw_prob,
            away_win_prob=pred.away_win_prob,
            prediction_confidence=pred.prediction_confidence,
            predicted_outcome=explanation.predicted_outcome,
            explanations=explanations_list,
        )

    def get_explainer(self) -> "PredictionExplainer":  # type: ignore[name-defined]
        """
        Get a PredictionExplainer instance for this model.

        Returns:
            PredictionExplainer configured for this model
        """
        from src.prediction_engine.explainability import PredictionExplainer

        return PredictionExplainer(self.model)


# Default instance (untrained until models are available)
xgboost_model = XGBoostModel()
