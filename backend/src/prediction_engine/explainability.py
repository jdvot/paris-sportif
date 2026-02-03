"""Prediction explainability for football match predictions.

Provides explanations for XGBoost model predictions using feature contribution analysis.
When SHAP is not available (Python 3.13+ compatibility), uses XGBoost's native
feature importance and marginal contribution analysis.

Output format:
    {
        "prediction": "home",
        "confidence": 0.72,
        "explanations": [
            {"feature": "home_attack", "contribution": +0.15},
            {"feature": "away_defense", "contribution": +0.08},
            {"feature": "form_advantage", "contribution": -0.05}
        ]
    }

References:
- Lundberg & Lee (2017). A Unified Approach to Interpreting Model Predictions
- XGBoost feature importance: https://xgboost.readthedocs.io/en/stable/python/python_api.html
"""

import logging
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

# Try to import SHAP for better explanations (may fail on Python 3.13+)
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.info("SHAP not available - using XGBoost native feature contributions")


@dataclass
class FeatureContribution:
    """Single feature contribution to prediction."""

    feature: str
    contribution: float
    value: float  # Feature value used in prediction
    importance_rank: int  # 1 = most important


@dataclass
class PredictionExplanation:
    """Complete explanation for a prediction."""

    predicted_outcome: Literal["home_win", "draw", "away_win"]
    confidence: float
    explanations: list[FeatureContribution] = field(default_factory=list)
    base_prediction: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)  # Baseline
    method: str = "xgboost_native"  # or "shap" if available

    def to_dict(self) -> dict:
        """Convert to API-friendly dictionary format."""
        return {
            "prediction": self.predicted_outcome.replace("_", " ").title(),
            "confidence": round(self.confidence, 3),
            "explanations": [
                {
                    "feature": exp.feature,
                    "contribution": round(exp.contribution, 4),
                    "value": round(exp.value, 3),
                    "rank": exp.importance_rank,
                }
                for exp in self.explanations
            ],
            "method": self.method,
        }

    def top_features(self, n: int = 3) -> list[FeatureContribution]:
        """Get top N contributing features by absolute contribution."""
        sorted_exp = sorted(
            self.explanations, key=lambda x: abs(x.contribution), reverse=True
        )
        return sorted_exp[:n]


class PredictionExplainer:
    """
    Explains XGBoost model predictions.

    Uses SHAP TreeExplainer when available, otherwise falls back to
    XGBoost's native feature importance combined with marginal contribution
    analysis.
    """

    # Feature names matching XGBoost model
    FEATURE_NAMES = [
        "home_attack",
        "home_defense",
        "away_attack",
        "away_defense",
        "recent_form_home",
        "recent_form_away",
        "head_to_head_home",
    ]

    # Human-readable feature labels
    FEATURE_LABELS = {
        "home_attack": "Home Attack Strength",
        "home_defense": "Home Defense Strength",
        "away_attack": "Away Attack Strength",
        "away_defense": "Away Defense Strength",
        "recent_form_home": "Home Recent Form",
        "recent_form_away": "Away Recent Form",
        "head_to_head_home": "Head-to-Head Advantage",
    }

    OUTCOMES = ["home_win", "draw", "away_win"]

    def __init__(self, model: object):
        """
        Initialize explainer with trained XGBoost model.

        Args:
            model: Trained XGBClassifier instance
        """
        self.model = model
        self._shap_explainer: object | None = None
        self._baseline_prediction: np.ndarray | None = None
        self._feature_importance: dict[str, float] = {}

        # Initialize explainer
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the explainer with model metadata."""
        if self.model is None:
            logger.warning("No model provided to explainer")
            return

        # Get feature importance from model
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            for i, importance in enumerate(importances):
                if i < len(self.FEATURE_NAMES):
                    self._feature_importance[self.FEATURE_NAMES[i]] = float(importance)

        # Initialize SHAP if available
        if SHAP_AVAILABLE:
            try:
                self._shap_explainer = shap.TreeExplainer(self.model)
                logger.info("SHAP TreeExplainer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize SHAP: {e}")
                self._shap_explainer = None

    def explain(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        recent_form_home: float = 50.0,
        recent_form_away: float = 50.0,
        head_to_head_home: float = 0.0,
    ) -> PredictionExplanation:
        """
        Explain a single prediction.

        Args:
            home_attack: Home team attack strength
            home_defense: Home team defense strength
            away_attack: Away team attack strength
            away_defense: Away team defense strength
            recent_form_home: Home team recent form (0-100)
            recent_form_away: Away team recent form (0-100)
            head_to_head_home: Head-to-head advantage (-1 to 1)

        Returns:
            PredictionExplanation with feature contributions
        """
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

        return self.explain_batch(features)[0]

    def explain_batch(
        self,
        features: np.ndarray,
    ) -> list[PredictionExplanation]:
        """
        Explain multiple predictions.

        Args:
            features: Array of shape (N, 7) with feature vectors

        Returns:
            List of PredictionExplanation objects
        """
        if self.model is None:
            return [self._fallback_explanation(f) for f in features]

        # Get predictions
        try:
            probs = self.model.predict_proba(features)
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return [self._fallback_explanation(f) for f in features]

        # Use SHAP if available
        if SHAP_AVAILABLE and self._shap_explainer is not None:
            return self._explain_with_shap(features, probs)

        # Fallback to marginal contribution analysis
        return self._explain_with_marginal(features, probs)

    def _explain_with_shap(
        self,
        features: np.ndarray,
        probs: np.ndarray,
    ) -> list[PredictionExplanation]:
        """Explain predictions using SHAP values."""
        explanations = []

        try:
            # Get SHAP values for all samples
            shap_values = self._shap_explainer.shap_values(features)  # type: ignore

            for i in range(len(features)):
                # Determine predicted outcome
                pred_idx = int(np.argmax(probs[i]))
                predicted_outcome = self.OUTCOMES[pred_idx]
                confidence = float(probs[i, pred_idx])

                # Get SHAP values for predicted class
                if isinstance(shap_values, list):
                    # Multi-class: list of arrays, one per class
                    sample_shap = shap_values[pred_idx][i]
                else:
                    # Binary or single array
                    sample_shap = shap_values[i]

                # Build feature contributions
                contributions = self._build_contributions(
                    features[i], sample_shap, "shap"
                )

                explanations.append(
                    PredictionExplanation(
                        predicted_outcome=predicted_outcome,  # type: ignore
                        confidence=confidence,
                        explanations=contributions,
                        base_prediction=tuple(probs[i]),  # type: ignore
                        method="shap",
                    )
                )

        except Exception as e:
            logger.warning(f"SHAP explanation failed: {e}, using marginal")
            return self._explain_with_marginal(features, probs)

        return explanations

    def _explain_with_marginal(
        self,
        features: np.ndarray,
        probs: np.ndarray,
    ) -> list[PredictionExplanation]:
        """
        Explain predictions using marginal contribution analysis.

        Calculates how much each feature contributes by comparing the prediction
        with and without that feature (using mean value as baseline).
        """
        explanations = []

        # Calculate mean feature values for baseline
        mean_features = np.mean(features, axis=0) if len(features) > 1 else features[0]

        for i in range(len(features)):
            # Determine predicted outcome
            pred_idx = int(np.argmax(probs[i]))
            predicted_outcome = self.OUTCOMES[pred_idx]
            confidence = float(probs[i, pred_idx])

            # Calculate marginal contributions
            contributions_values = self._calculate_marginal_contributions(
                features[i], mean_features, pred_idx
            )

            # Build feature contributions
            contributions = self._build_contributions(
                features[i], contributions_values, "marginal"
            )

            explanations.append(
                PredictionExplanation(
                    predicted_outcome=predicted_outcome,  # type: ignore
                    confidence=confidence,
                    explanations=contributions,
                    base_prediction=tuple(probs[i]),  # type: ignore
                    method="xgboost_native",
                )
            )

        return explanations

    def _calculate_marginal_contributions(
        self,
        sample: np.ndarray,
        baseline: np.ndarray,
        outcome_idx: int,
    ) -> np.ndarray:
        """
        Calculate marginal contribution of each feature.

        For each feature, measures the change in predicted probability when
        replacing that feature with its baseline value.
        """
        contributions = np.zeros(len(self.FEATURE_NAMES))

        # Get original prediction
        original_prob = self.model.predict_proba(sample.reshape(1, -1))[0, outcome_idx]

        for j in range(len(self.FEATURE_NAMES)):
            # Create modified sample with feature j set to baseline
            modified = sample.copy()
            modified[j] = baseline[j]

            # Get prediction with modified feature
            modified_prob = self.model.predict_proba(modified.reshape(1, -1))[
                0, outcome_idx
            ]

            # Contribution is how much probability drops when feature is removed
            contributions[j] = original_prob - modified_prob

        # Normalize contributions to sum to difference from uniform (1/3)
        total_diff = original_prob - (1 / 3)
        if abs(total_diff) > 0.01 and np.sum(np.abs(contributions)) > 0.01:
            contributions = contributions * (total_diff / np.sum(np.abs(contributions)))

        return contributions

    def _build_contributions(
        self,
        feature_values: np.ndarray,
        contribution_values: np.ndarray,
        method: str,
    ) -> list[FeatureContribution]:
        """Build sorted list of FeatureContribution objects."""
        contributions = []

        # Combine with feature importance for ranking
        for j, name in enumerate(self.FEATURE_NAMES):
            contributions.append(
                FeatureContribution(
                    feature=name,
                    contribution=float(contribution_values[j]),
                    value=float(feature_values[j]),
                    importance_rank=0,  # Will be set after sorting
                )
            )

        # Sort by absolute contribution and assign ranks
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        for rank, contrib in enumerate(contributions, start=1):
            contrib.importance_rank = rank

        return contributions

    def _fallback_explanation(self, features: np.ndarray) -> PredictionExplanation:
        """Generate fallback explanation when model unavailable."""
        # Use feature values to estimate contributions
        contributions = []
        for i, name in enumerate(self.FEATURE_NAMES):
            contributions.append(
                FeatureContribution(
                    feature=name,
                    contribution=0.0,
                    value=float(features[i]) if i < len(features) else 0.0,
                    importance_rank=i + 1,
                )
            )

        return PredictionExplanation(
            predicted_outcome="home_win",
            confidence=0.33,
            explanations=contributions,
            method="fallback",
        )

    def get_global_importance(self) -> dict[str, float]:
        """
        Get global feature importance from the model.

        Returns:
            Dictionary mapping feature names to importance scores (0-1)
        """
        if not self._feature_importance:
            return {name: 1.0 / len(self.FEATURE_NAMES) for name in self.FEATURE_NAMES}

        # Normalize to sum to 1
        total = sum(self._feature_importance.values())
        if total > 0:
            return {k: v / total for k, v in self._feature_importance.items()}
        return self._feature_importance.copy()

    def get_feature_label(self, feature_name: str) -> str:
        """Get human-readable label for a feature."""
        return self.FEATURE_LABELS.get(feature_name, feature_name)


def explain_prediction(
    model: object,
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    recent_form_home: float = 50.0,
    recent_form_away: float = 50.0,
    head_to_head_home: float = 0.0,
) -> dict:
    """
    Convenience function to explain a single prediction.

    Returns API-ready dictionary with prediction and explanations.
    """
    explainer = PredictionExplainer(model)
    explanation = explainer.explain(
        home_attack=home_attack,
        home_defense=home_defense,
        away_attack=away_attack,
        away_defense=away_defense,
        recent_form_home=recent_form_home,
        recent_form_away=recent_form_away,
        head_to_head_home=head_to_head_home,
    )
    return explanation.to_dict()
