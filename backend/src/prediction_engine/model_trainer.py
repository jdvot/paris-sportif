"""Model training and evaluation utilities.

This module handles:
- Data preparation from match history
- Model training for XGBoost and Random Forest
- Hyperparameter optimization with Optuna
- Cross-validation and evaluation
- Model persistence (saving/loading)
- Performance metrics calculation
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from src.prediction_engine.feature_engineering import FeatureEngineer
from src.prediction_engine.models.random_forest_model import RandomForestModel
from src.prediction_engine.models.xgboost_model import XGBoostModel

logger = logging.getLogger(__name__)

# Optional sklearn imports
try:
    from sklearn.metrics import accuracy_score, log_loss, precision_recall_fscore_support
    from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    if TYPE_CHECKING:
        from sklearn.metrics import accuracy_score, log_loss, precision_recall_fscore_support
        from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

# Optional Optuna import
try:
    import optuna
    from optuna.samplers import TPESampler

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna not available - hyperparameter optimization disabled")

# Optional XGBoost import for optimization
try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# Optional sklearn RandomForest for optimization
try:
    from sklearn.ensemble import RandomForestClassifier

    RF_AVAILABLE = True
except ImportError:
    RF_AVAILABLE = False


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


@dataclass
class OptimizationResult:
    """Result of hyperparameter optimization."""

    best_params: dict[str, Any]
    best_score: float
    n_trials: int
    optimization_history: list[float] = field(default_factory=list)
    study_name: str = ""


class ModelTrainer:
    """
    Utility for training and evaluating ML models for football predictions.

    Handles the full pipeline:
    1. Data preparation
    2. Hyperparameter optimization (Optuna)
    3. Train/validation split
    4. Model training
    5. Evaluation and metrics
    6. Model persistence
    """

    # Default hyperparameter search spaces
    XGBOOST_PARAM_SPACE = {
        "max_depth": (3, 10),
        "learning_rate": (0.01, 0.3),
        "n_estimators": (50, 500),
        "subsample": (0.6, 1.0),
        "colsample_bytree": (0.6, 1.0),
        "min_child_weight": (1, 10),
        "gamma": (0.0, 0.5),
    }

    RF_PARAM_SPACE = {
        "n_estimators": (50, 300),
        "max_depth": (5, 20),
        "min_samples_split": (2, 20),
        "min_samples_leaf": (1, 10),
        "max_features": ["sqrt", "log2", None],
    }

    def __init__(self) -> None:
        """Initialize trainer."""
        self.xgboost_model = XGBoostModel()
        self.random_forest_model = RandomForestModel()
        self.training_metrics: dict[str, ModelMetrics] = {}
        self.optimization_results: dict[str, OptimizationResult] = {}

    def prepare_data(
        self,
        match_data: list[dict[str, Any]],
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
                X,
                y,
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
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> ModelMetrics | None:
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
                X_train,
                y_train,
                X_val=X_val,
                y_val=y_val,
                early_stopping_rounds=20,
            )

            # Evaluate on test set
            if X_val is not None and y_val is not None:
                metrics = self._evaluate_model(
                    self.xgboost_model,
                    X_val,
                    y_val,
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
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> ModelMetrics | None:
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
                    X_val,
                    y_val,
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
        match_data: list[dict[str, Any]],
        test_size: float = 0.2,
    ) -> dict[str, ModelMetrics | None]:
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
                X_train,
                y_train,
                X_val=X_test,
                y_val=y_test,
            )
            results["xgboost"] = xgb_metrics

            # Train Random Forest
            rf_metrics = self.train_random_forest(
                X_train,
                y_train,
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
        model: Any,
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
                y_test,
                y_pred,
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

            xgb_loaded = (
                self.xgboost_model.load_model(xgb_path) if os.path.exists(xgb_path) else False
            )
            rf_loaded = (
                self.random_forest_model.load_model(rf_path) if os.path.exists(rf_path) else False
            )

            if xgb_loaded or rf_loaded:
                logger.info(f"Models loaded from {directory}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False

    # ==================== Optuna Hyperparameter Optimization ====================

    def optimize_xgboost(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_trials: int = 50,
        cv_folds: int = 5,
        timeout: int | None = None,
        study_name: str = "xgboost_optimization",
    ) -> OptimizationResult:
        """
        Optimize XGBoost hyperparameters using Optuna with cross-validation.

        Args:
            X: Feature matrix
            y: Target labels
            n_trials: Number of optimization trials
            cv_folds: Number of cross-validation folds
            timeout: Maximum optimization time in seconds (None for no limit)
            study_name: Name for the Optuna study

        Returns:
            OptimizationResult with best parameters and score
        """
        if not OPTUNA_AVAILABLE:
            logger.error("Optuna not available - cannot optimize hyperparameters")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not available - cannot optimize")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

        def objective(trial: "optuna.Trial") -> float:
            """Optuna objective function for XGBoost."""
            params = {
                "max_depth": trial.suggest_int(
                    "max_depth",
                    self.XGBOOST_PARAM_SPACE["max_depth"][0],
                    self.XGBOOST_PARAM_SPACE["max_depth"][1],
                ),
                "learning_rate": trial.suggest_float(
                    "learning_rate",
                    self.XGBOOST_PARAM_SPACE["learning_rate"][0],
                    self.XGBOOST_PARAM_SPACE["learning_rate"][1],
                    log=True,
                ),
                "n_estimators": trial.suggest_int(
                    "n_estimators",
                    self.XGBOOST_PARAM_SPACE["n_estimators"][0],
                    self.XGBOOST_PARAM_SPACE["n_estimators"][1],
                ),
                "subsample": trial.suggest_float(
                    "subsample",
                    self.XGBOOST_PARAM_SPACE["subsample"][0],
                    self.XGBOOST_PARAM_SPACE["subsample"][1],
                ),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree",
                    self.XGBOOST_PARAM_SPACE["colsample_bytree"][0],
                    self.XGBOOST_PARAM_SPACE["colsample_bytree"][1],
                ),
                "min_child_weight": trial.suggest_int(
                    "min_child_weight",
                    self.XGBOOST_PARAM_SPACE["min_child_weight"][0],
                    self.XGBOOST_PARAM_SPACE["min_child_weight"][1],
                ),
                "gamma": trial.suggest_float(
                    "gamma",
                    self.XGBOOST_PARAM_SPACE["gamma"][0],
                    self.XGBOOST_PARAM_SPACE["gamma"][1],
                ),
                "random_state": 42,
                "eval_metric": "mlogloss",
                "verbosity": 0,
            }

            model = xgb.XGBClassifier(**params)

            # Use stratified k-fold cross-validation
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)

            return float(scores.mean())

        try:
            # Create Optuna study with TPE sampler
            sampler = TPESampler(seed=42)
            study = optuna.create_study(
                study_name=study_name,
                direction="maximize",
                sampler=sampler,
            )

            # Suppress Optuna logs during optimization
            optuna.logging.set_verbosity(optuna.logging.WARNING)

            logger.info(f"Starting XGBoost optimization with {n_trials} trials...")
            study.optimize(
                objective,
                n_trials=n_trials,
                timeout=timeout,
                show_progress_bar=False,
            )

            # Extract optimization history
            history = [trial.value for trial in study.trials if trial.value is not None]

            result = OptimizationResult(
                best_params=study.best_params,
                best_score=study.best_value,
                n_trials=len(study.trials),
                optimization_history=history,
                study_name=study_name,
            )

            self.optimization_results["xgboost"] = result
            logger.info(
                f"XGBoost optimization complete. Best accuracy: {result.best_score:.4f}"
            )
            logger.info(f"Best params: {result.best_params}")

            return result

        except Exception as e:
            logger.error(f"Error during XGBoost optimization: {e}")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

    def optimize_random_forest(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_trials: int = 50,
        cv_folds: int = 5,
        timeout: int | None = None,
        study_name: str = "random_forest_optimization",
    ) -> OptimizationResult:
        """
        Optimize Random Forest hyperparameters using Optuna with cross-validation.

        Args:
            X: Feature matrix
            y: Target labels
            n_trials: Number of optimization trials
            cv_folds: Number of cross-validation folds
            timeout: Maximum optimization time in seconds (None for no limit)
            study_name: Name for the Optuna study

        Returns:
            OptimizationResult with best parameters and score
        """
        if not OPTUNA_AVAILABLE:
            logger.error("Optuna not available - cannot optimize hyperparameters")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

        if not RF_AVAILABLE:
            logger.error("scikit-learn RandomForest not available - cannot optimize")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

        def objective(trial: "optuna.Trial") -> float:
            """Optuna objective function for Random Forest."""
            max_features_choices = self.RF_PARAM_SPACE["max_features"]
            max_features = trial.suggest_categorical("max_features", max_features_choices)

            params = {
                "n_estimators": trial.suggest_int(
                    "n_estimators",
                    self.RF_PARAM_SPACE["n_estimators"][0],
                    self.RF_PARAM_SPACE["n_estimators"][1],
                ),
                "max_depth": trial.suggest_int(
                    "max_depth",
                    self.RF_PARAM_SPACE["max_depth"][0],
                    self.RF_PARAM_SPACE["max_depth"][1],
                ),
                "min_samples_split": trial.suggest_int(
                    "min_samples_split",
                    self.RF_PARAM_SPACE["min_samples_split"][0],
                    self.RF_PARAM_SPACE["min_samples_split"][1],
                ),
                "min_samples_leaf": trial.suggest_int(
                    "min_samples_leaf",
                    self.RF_PARAM_SPACE["min_samples_leaf"][0],
                    self.RF_PARAM_SPACE["min_samples_leaf"][1],
                ),
                "max_features": max_features,
                "random_state": 42,
                "n_jobs": -1,
            }

            model = RandomForestClassifier(**params)

            # Use stratified k-fold cross-validation
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)

            return float(scores.mean())

        try:
            # Create Optuna study with TPE sampler
            sampler = TPESampler(seed=42)
            study = optuna.create_study(
                study_name=study_name,
                direction="maximize",
                sampler=sampler,
            )

            # Suppress Optuna logs during optimization
            optuna.logging.set_verbosity(optuna.logging.WARNING)

            logger.info(f"Starting Random Forest optimization with {n_trials} trials...")
            study.optimize(
                objective,
                n_trials=n_trials,
                timeout=timeout,
                show_progress_bar=False,
            )

            # Extract optimization history
            history = [trial.value for trial in study.trials if trial.value is not None]

            result = OptimizationResult(
                best_params=study.best_params,
                best_score=study.best_value,
                n_trials=len(study.trials),
                optimization_history=history,
                study_name=study_name,
            )

            self.optimization_results["random_forest"] = result
            logger.info(
                f"Random Forest optimization complete. Best accuracy: {result.best_score:.4f}"
            )
            logger.info(f"Best params: {result.best_params}")

            return result

        except Exception as e:
            logger.error(f"Error during Random Forest optimization: {e}")
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                n_trials=0,
                study_name=study_name,
            )

    def train_xgboost_optimized(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        params: dict[str, Any] | None = None,
    ) -> ModelMetrics | None:
        """
        Train XGBoost with optimized hyperparameters.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            params: Optimized parameters (uses stored optimization result if None)

        Returns:
            ModelMetrics or None if training failed
        """
        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not available")
            return None

        # Use provided params or get from optimization results
        if params is None:
            if "xgboost" in self.optimization_results:
                params = self.optimization_results["xgboost"].best_params
            else:
                logger.warning("No optimization results found, using default params")
                params = {}

        try:
            logger.info(f"Training XGBoost with optimized params: {params}")

            # Merge with defaults for any missing params
            eval_set = [(X_val, y_val)] if X_val is not None and y_val is not None else None

            full_params = {
                "max_depth": params.get("max_depth", 6),
                "learning_rate": params.get("learning_rate", 0.1),
                "n_estimators": params.get("n_estimators", 200),
                "subsample": params.get("subsample", 0.8),
                "colsample_bytree": params.get("colsample_bytree", 0.8),
                "min_child_weight": params.get("min_child_weight", 1),
                "gamma": params.get("gamma", 0),
                "random_state": 42,
                "eval_metric": "mlogloss",
                "verbosity": 0,
                "early_stopping_rounds": 20 if eval_set else None,
            }

            model = xgb.XGBClassifier(**full_params)

            # Train model
            model.fit(
                X_train,
                y_train,
                eval_set=eval_set,
                verbose=False,
            )

            # Store the trained model
            self.xgboost_model.model = model
            self.xgboost_model.is_trained = True

            # Store feature importance
            if hasattr(model, "feature_importances_"):
                feature_names = XGBoostModel.FEATURE_NAMES
                for i, importance in enumerate(model.feature_importances_):
                    if i < len(feature_names):
                        self.xgboost_model.feature_importance[feature_names[i]] = float(
                            importance
                        )

            # Evaluate if validation set provided
            if X_val is not None and y_val is not None:
                metrics = self._evaluate_model(
                    self.xgboost_model,
                    X_val,
                    y_val,
                    "XGBoost (Optimized)",
                )
                self.training_metrics["xgboost"] = metrics
                return metrics

            return None

        except Exception as e:
            logger.error(f"Error training optimized XGBoost: {e}")
            return None

    def train_random_forest_optimized(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        params: dict[str, Any] | None = None,
    ) -> ModelMetrics | None:
        """
        Train Random Forest with optimized hyperparameters.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            params: Optimized parameters (uses stored optimization result if None)

        Returns:
            ModelMetrics or None if training failed
        """
        if not RF_AVAILABLE:
            logger.error("scikit-learn RandomForest not available")
            return None

        # Use provided params or get from optimization results
        if params is None:
            if "random_forest" in self.optimization_results:
                params = self.optimization_results["random_forest"].best_params
            else:
                logger.warning("No optimization results found, using default params")
                params = {}

        try:
            logger.info(f"Training Random Forest with optimized params: {params}")

            # Merge with defaults for any missing params
            full_params = {
                "n_estimators": params.get("n_estimators", 100),
                "max_depth": params.get("max_depth", 12),
                "min_samples_split": params.get("min_samples_split", 5),
                "min_samples_leaf": params.get("min_samples_leaf", 2),
                "max_features": params.get("max_features", "sqrt"),
                "random_state": 42,
                "n_jobs": -1,
                "oob_score": True,
                "bootstrap": True,
            }

            model = RandomForestClassifier(**full_params)
            model.fit(X_train, y_train)

            # Store the trained model
            self.random_forest_model.model = model
            self.random_forest_model.is_trained = True

            # Store OOB score
            if hasattr(model, "oob_score_"):
                self.random_forest_model.oob_score = float(model.oob_score_)

            # Store feature importance
            if hasattr(model, "feature_importances_"):
                feature_names = RandomForestModel.FEATURE_NAMES
                for i, importance in enumerate(model.feature_importances_):
                    if i < len(feature_names):
                        self.random_forest_model.feature_importance[feature_names[i]] = float(
                            importance
                        )

            # Evaluate if validation set provided
            if X_val is not None and y_val is not None:
                metrics = self._evaluate_model(
                    self.random_forest_model,
                    X_val,
                    y_val,
                    "Random Forest (Optimized)",
                )
                self.training_metrics["random_forest"] = metrics
                return metrics

            return None

        except Exception as e:
            logger.error(f"Error training optimized Random Forest: {e}")
            return None

    def optimize_and_train_both(
        self,
        match_data: list[dict[str, Any]],
        n_trials: int = 50,
        cv_folds: int = 5,
        test_size: float = 0.2,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Full pipeline: optimize hyperparameters and train both models.

        Args:
            match_data: List of match dictionaries with features and outcomes
            n_trials: Number of Optuna trials per model
            cv_folds: Number of cross-validation folds
            test_size: Fraction of data for final evaluation
            timeout: Maximum optimization time per model in seconds

        Returns:
            Dictionary with optimization results and final metrics
        """
        try:
            # Prepare data
            X_train, X_test, y_train, y_test = self.prepare_data(
                match_data,
                test_size=test_size,
            )

            results: dict[str, Any] = {
                "xgboost": {"optimization": None, "metrics": None},
                "random_forest": {"optimization": None, "metrics": None},
            }

            # Optimize XGBoost
            logger.info("=" * 50)
            logger.info("Optimizing XGBoost hyperparameters...")
            xgb_opt = self.optimize_xgboost(
                X_train,
                y_train,
                n_trials=n_trials,
                cv_folds=cv_folds,
                timeout=timeout,
            )
            results["xgboost"]["optimization"] = xgb_opt

            # Train XGBoost with best params
            if xgb_opt.best_params:
                xgb_metrics = self.train_xgboost_optimized(
                    X_train,
                    y_train,
                    X_val=X_test,
                    y_val=y_test,
                    params=xgb_opt.best_params,
                )
                results["xgboost"]["metrics"] = xgb_metrics

            # Optimize Random Forest
            logger.info("=" * 50)
            logger.info("Optimizing Random Forest hyperparameters...")
            rf_opt = self.optimize_random_forest(
                X_train,
                y_train,
                n_trials=n_trials,
                cv_folds=cv_folds,
                timeout=timeout,
            )
            results["random_forest"]["optimization"] = rf_opt

            # Train Random Forest with best params
            if rf_opt.best_params:
                rf_metrics = self.train_random_forest_optimized(
                    X_train,
                    y_train,
                    X_val=X_test,
                    y_val=y_test,
                    params=rf_opt.best_params,
                )
                results["random_forest"]["metrics"] = rf_metrics

            logger.info("=" * 50)
            logger.info("Optimization and training complete!")

            return results

        except Exception as e:
            logger.error(f"Error in optimize_and_train_both: {e}")
            return {
                "xgboost": {"optimization": None, "metrics": None},
                "random_forest": {"optimization": None, "metrics": None},
            }
