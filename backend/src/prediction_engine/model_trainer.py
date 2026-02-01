"""Model training and evaluation utilities.

This module handles:
- Data preparation from match history
- Model training for XGBoost and Random Forest
- Cross-validation and evaluation
- Model persistence (saving/loading)
- Performance metrics calculation
"""

from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
import logging

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, log_loss
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from src.prediction_engine.models.xgboost_model import XGBoostModel
from src.prediction_engine.models.random_forest_model import RandomForestModel
from src.prediction_engine.feature_engineering import FeatureEngineer, FeatureVector


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""

    accuracy: float
    precision_home: float
    precision_draw: float
    precision_away: float
    recall_home: float
    recall_draw: float
    recall_away: float
    f1_home: float
    f1_draw: float
    f1_away: float
    logloss: float


class ModelTrainer:
    """
    Utility for training and evaluating ML models for football predictions.

    Handles the full pipeline:
    1. Data preparation
    2. Train/validation split
    3. Model training
    4. Evaluation and metrics
    5. Model persistence
    """

    def __init__(self):
        """Initialize trainer."""
        self.xgboost_model = XGBoostModel()
        self.random_forest_model = RandomForestModel()
        self.training_metrics: Dict[str, ModelMetrics] = {}

    def prepare_data(
        self,
        match_data: List[Dict],
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare data for training.

        Expected match_data format:
        [
            {
                "home_attack": float,
                "home_defense": float,
                "away_attack": float,
                "away_defense": float,
                "recent_form_home": float (optional),
                "recent_form_away": float (optional),
                "head_to_head_home": float (optional),
                "outcome": int (0=home_win, 1=draw, 2=away_win)
            },
            ...
        ]

        Args:
            match_data: List of match dictionaries
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility

        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        if not match_data:
            logger.error("No match data provided")
            raise ValueError("match_data cannot be empty")

        try:
            # Extract features and outcomes
            features = []
            outcomes = []

            for match in match_data:
                # Use engineer to normalize features
                feature_vec = FeatureEngineer.engineer_features(
                    home_attack=match.get("home_attack", 1.4),
                    home_defense=match.get("home_defense", 1.4),
                    away_attack=match.get("away_attack", 1.4),
                    away_defense=match.get("away_defense", 1.4),
                    home_recent_results=match.get("home_recent_results"),
                    away_recent_results=match.get("away_recent_results"),
                    h2h_results=match.get("h2h_results"),
                )

                features.append(feature_vec.to_array())
                outcomes.append(match.get("outcome", 1))  # Default to draw

            X = np.array(features)
            y = np.array(outcomes)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=random_state,
                stratify=y,
            )

            logger.info(f"Data prepared: {len(X_train)} training, {len(X_test)} test")
            return X_train, X_test, y_train, y_test

        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            raise

    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> Optional[ModelMetrics]:
        """
        Train XGBoost model.

        Args:
            X_train: Training features
            y_train: Training outcomes
            X_val: Validation features (optional)
            y_val: Validation outcomes (optional)

        Returns:
            ModelMetrics or None if training failed
        """
        try:
            logger.info("Starting XGBoost training...")

            # Train model
            self.xgboost_model.train(
                X_train, y_train,
                X_val=X_val,
                y_val=y_val,
                early_stopping_rounds=20,
            )

            # Evaluate on test set
            if X_val is not None and y_val is not None:
                metrics = self._evaluate_model(
                    self.xgboost_model,
                    X_val, y_val,
                    "XGBoost",
                )
                self.training_metrics["xgboost"] = metrics
                return metrics

            return None

        except Exception as e:
            logger.error(f"Error training XGBoost: {e}")
            return None

    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> Optional[ModelMetrics]:
        """
        Train Random Forest model.

        Args:
            X_train: Training features
            y_train: Training outcomes
            X_val: Validation features (optional)
            y_val: Validation outcomes (optional)

        Returns:
            ModelMetrics or None if training failed
        """
        try:
            logger.info("Starting Random Forest training...")

            # Train model
            self.random_forest_model.train(X_train, y_train)

            # Evaluate
            if X_val is not None and y_val is not None:
                metrics = self._evaluate_model(
                    self.random_forest_model,
                    X_val, y_val,
                    "Random Forest",
                )
                self.training_metrics["random_forest"] = metrics
                return metrics

            return None

        except Exception as e:
            logger.error(f"Error training Random Forest: {e}")
            return None

    def train_both_models(
        self,
        match_data: List[Dict],
        test_size: float = 0.2,
    ) -> Dict[str, Optional[ModelMetrics]]:
        """
        Prepare data and train both XGBoost and Random Forest models.

        Args:
            match_data: List of match dictionaries with features and outcomes
            test_size: Fraction of data to use for testing

        Returns:
            Dictionary with metrics for each model
        """
        try:
            # Prepare data
            X_train, X_test, y_train, y_test = self.prepare_data(
                match_data,
                test_size=test_size,
            )

            results = {}

            # Train XGBoost
            xgb_metrics = self.train_xgboost(
                X_train, y_train,
                X_val=X_test,
                y_val=y_test,
            )
            results["xgboost"] = xgb_metrics

            # Train Random Forest
            rf_metrics = self.train_random_forest(
                X_train, y_train,
                X_val=X_test,
                y_val=y_test,
            )
            results["random_forest"] = rf_metrics

            logger.info("Both models trained successfully")
            return results

        except Exception as e:
            logger.error(f"Error in train_both_models: {e}")
            return {"xgboost": None, "random_forest": None}

    def _evaluate_model(
        self,
        model,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "Model",
    ) -> ModelMetrics:
        """
        Evaluate model on test set.

        Args:
            model: Trained model with predict_proba method
            X_test: Test features
            y_test: Test outcomes
            model_name: Name for logging

        Returns:
            ModelMetrics with evaluation results
        """
        try:
            # Get predictions
            y_pred_proba = model.predict_batch(X_test)
            y_pred = np.argmax(y_pred_proba, axis=1)

            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)

            # Per-class metrics
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred,
                average=None,
                zero_division=0,
            )

            # Log loss
            logloss_val = log_loss(y_test, y_pred_proba)

            metrics = ModelMetrics(
                accuracy=float(accuracy),
                precision_home=float(precision[0]),
                precision_draw=float(precision[1]),
                precision_away=float(precision[2]),
                recall_home=float(recall[0]),
                recall_draw=float(recall[1]),
                recall_away=float(recall[2]),
                f1_home=float(f1[0]),
                f1_draw=float(f1[1]),
                f1_away=float(f1[2]),
                logloss=float(logloss_val),
            )

            logger.info(f"{model_name} - Accuracy: {accuracy:.4f}, LogLoss: {logloss_val:.4f}")

            return metrics

        except Exception as e:
            logger.error(f"Error evaluating {model_name}: {e}")
            # Return zero metrics on error
            return ModelMetrics(
                accuracy=0.0,
                precision_home=0.0,
                precision_draw=0.0,
                precision_away=0.0,
                recall_home=0.0,
                recall_draw=0.0,
                recall_away=0.0,
                f1_home=0.0,
                f1_draw=0.0,
                f1_away=0.0,
                logloss=0.0,
            )

    def save_models(self, directory: str) -> bool:
        """
        Save both trained models to disk.

        Args:
            directory: Directory to save models

        Returns:
            True if successful
        """
        try:
            import os
            os.makedirs(directory, exist_ok=True)

            xgb_path = os.path.join(directory, "xgboost_model.pkl")
            rf_path = os.path.join(directory, "random_forest_model.pkl")

            xgb_saved = self.xgboost_model.save_model(xgb_path)
            rf_saved = self.random_forest_model.save_model(rf_path)

            if xgb_saved and rf_saved:
                logger.info(f"Models saved to {directory}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return False

    def load_models(self, directory: str) -> bool:
        """
        Load trained models from disk.

        Args:
            directory: Directory containing saved models

        Returns:
            True if successful
        """
        try:
            import os
            xgb_path = os.path.join(directory, "xgboost_model.pkl")
            rf_path = os.path.join(directory, "random_forest_model.pkl")

            xgb_loaded = self.xgboost_model.load_model(xgb_path) if os.path.exists(xgb_path) else False
            rf_loaded = self.random_forest_model.load_model(rf_path) if os.path.exists(rf_path) else False

            if xgb_loaded or rf_loaded:
                logger.info(f"Models loaded from {directory}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
