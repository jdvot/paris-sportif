"""
Example usage of the ML models and ensemble predictor.

This file demonstrates:
1. Using the ensemble predictor with all models
2. Training new models from scratch
3. Feature engineering
4. Model evaluation
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


# Example 1: Using the Ensemble Predictor
def example_ensemble_prediction() -> None:
    """Demonstrate ensemble prediction with all models."""
    from src.prediction_engine.ensemble import EnsemblePredictor

    predictor = EnsemblePredictor()

    # Match data
    prediction = predictor.predict(
        # Team statistics for statistical models
        home_attack=2.1,  # Goals per match at home
        home_defense=1.3,  # Goals conceded per match at home
        away_attack=1.8,  # Goals per match away
        away_defense=1.5,  # Goals conceded per match away
        # ELO ratings
        home_elo=1650,
        away_elo=1550,
        # Optional: Expected Goals data
        home_xg_for=1.8,
        home_xg_against=0.9,
        away_xg_for=1.5,
        away_xg_against=1.2,
        # Optional: ML features
        recent_form_home=65.0,  # 0-100 scale
        recent_form_away=45.0,
        head_to_head_home=0.2,  # -1.0 to 1.0
        # Optional: Bookmaker odds for value calculation
        odds_home=2.1,
        odds_draw=3.2,
        odds_away=3.5,
    )

    # Results
    logger.info("=== Ensemble Prediction ===")
    logger.info("Home Win: %.1f%%", prediction.home_win_prob * 100)
    logger.info("Draw: %.1f%%", prediction.draw_prob * 100)
    logger.info("Away Win: %.1f%%", prediction.away_win_prob * 100)
    logger.info("Recommended Bet: %s", prediction.recommended_bet)
    logger.info("Confidence: %.1f%%", prediction.confidence * 100)
    logger.info("Model Agreement: %.1f%%", prediction.model_agreement * 100)
    logger.info("Value Score: %s", prediction.value_score)
    logger.info(
        "Expected Goals: %.1f-%.1f",
        prediction.expected_home_goals,
        prediction.expected_away_goals,
    )

    # Model contributions
    if prediction.poisson_contribution:
        logger.info("Poisson: %.1f%%", prediction.poisson_contribution.home_prob * 100)
    if prediction.elo_contribution:
        logger.info("ELO: %.1f%%", prediction.elo_contribution.home_prob * 100)
    if prediction.xgboost_contribution:
        logger.info("XGBoost: %.1f%%", prediction.xgboost_contribution.home_prob * 100)
    if prediction.random_forest_contribution:
        logger.info("Random Forest: %.1f%%", prediction.random_forest_contribution.home_prob * 100)


# Example 2: Feature Engineering
def example_feature_engineering() -> None:
    """Demonstrate feature engineering capabilities."""
    from src.prediction_engine.feature_engineering import FeatureEngineer

    logger.info("=== Feature Engineering ===")

    # Calculate recent form from match results
    home_results = [
        (2, 1),  # Won 2-1 (most recent)
        (1, 0),  # Won 1-0
        (0, 1),  # Lost 0-1
        (1, 1),  # Drew 1-1
    ]
    home_form = FeatureEngineer.calculate_recent_form(home_results, is_home=True)
    logger.info("Home team recent form: %.1f/100", home_form)

    # Calculate head-to-head
    h2h_results = [
        (1, 0),  # Won 1-0 (most recent)
        (2, 2),  # Drew 2-2
        (0, 1),  # Lost 0-1
    ]
    h2h_home = FeatureEngineer.calculate_head_to_head(h2h_results, is_home=True)
    logger.info("H2H advantage (home): %.2f", h2h_home)

    # Create engineered feature vector
    features = FeatureEngineer.engineer_features(
        home_attack=2.1,
        home_defense=1.3,
        away_attack=1.8,
        away_defense=1.5,
        home_recent_results=home_results,
        away_recent_results=[(1, 1), (2, 0), (1, 2)],
        h2h_results=h2h_results,
    )

    logger.info("Engineered features shape: %s", features.to_array().shape)
    logger.info("Feature vector: %s", features)


# Example 3: Training Models
def example_training() -> None:
    """Demonstrate model training."""
    from src.prediction_engine.model_trainer import ModelTrainer

    logger.info("=== Model Training ===")

    # Generate synthetic training data
    # In real usage, you'd load historical match data
    np.random.seed(42)
    match_data = []

    for _ in range(500):
        # Random team strengths
        home_attack = np.random.uniform(1.0, 2.5)
        home_defense = np.random.uniform(0.8, 2.0)
        away_attack = np.random.uniform(1.0, 2.5)
        away_defense = np.random.uniform(0.8, 2.0)

        # Random form scores
        home_form = np.random.uniform(20, 80)
        away_form = np.random.uniform(20, 80)

        # Generate outcome based on strength (biased toward stronger team)
        home_strength = home_attack / (away_defense + 0.1)
        away_strength = away_attack / (home_defense + 0.1)
        home_win_prob = home_strength / (home_strength + away_strength + 1)

        rand = np.random.random()
        if rand < home_win_prob:
            outcome = 0  # Home win
        elif rand < home_win_prob + 0.25:
            outcome = 1  # Draw
        else:
            outcome = 2  # Away win

        match_data.append(
            {
                "home_attack": home_attack,
                "home_defense": home_defense,
                "away_attack": away_attack,
                "away_defense": away_defense,
                "recent_form_home": home_form,
                "recent_form_away": away_form,
                "head_to_head_home": np.random.uniform(-1, 1),
                "outcome": outcome,
            }
        )

    logger.info("Generated %d synthetic matches", len(match_data))

    # Train models
    trainer = ModelTrainer()
    metrics = trainer.train_both_models(match_data, test_size=0.2)

    if metrics["xgboost"]:
        logger.info("XGBoost:")
        logger.info("  Accuracy: %.2f%%", metrics["xgboost"].accuracy * 100)
        logger.info("  LogLoss: %.4f", metrics["xgboost"].logloss)
        logger.info("  Home F1: %.3f", metrics["xgboost"].f1_home)

    if metrics["random_forest"]:
        logger.info("Random Forest:")
        logger.info("  Accuracy: %.2f%%", metrics["random_forest"].accuracy * 100)
        logger.info("  LogLoss: %.4f", metrics["random_forest"].logloss)
        logger.info("  Home F1: %.3f", metrics["random_forest"].f1_home)


# Example 4: Direct Model Usage
def example_direct_models() -> None:
    """Demonstrate using models directly."""
    from src.prediction_engine.models.random_forest_model import RandomForestModel
    from src.prediction_engine.models.xgboost_model import XGBoostModel

    logger.info("=== Direct Model Usage ===")

    # XGBoost
    xgb_model = XGBoostModel()

    # Make prediction (will use fallback if not trained)
    xgb_pred = xgb_model.predict(
        home_attack=2.1,
        home_defense=1.3,
        away_attack=1.8,
        away_defense=1.5,
        recent_form_home=65.0,
        recent_form_away=45.0,
        head_to_head_home=0.2,
    )

    logger.info("XGBoost Prediction:")
    logger.info("  Home Win: %.1f%%", xgb_pred.home_win_prob * 100)
    logger.info("  Draw: %.1f%%", xgb_pred.draw_prob * 100)
    logger.info("  Away Win: %.1f%%", xgb_pred.away_win_prob * 100)
    logger.info("  Confidence: %.1f%%", xgb_pred.prediction_confidence * 100)

    # Random Forest
    rf_model = RandomForestModel()
    rf_pred = rf_model.predict(
        home_attack=2.1,
        home_defense=1.3,
        away_attack=1.8,
        away_defense=1.5,
        recent_form_home=65.0,
        recent_form_away=45.0,
        head_to_head_home=0.2,
    )

    logger.info("Random Forest Prediction:")
    logger.info("  Home Win: %.1f%%", rf_pred.home_win_prob * 100)
    logger.info("  Draw: %.1f%%", rf_pred.draw_prob * 100)
    logger.info("  Away Win: %.1f%%", rf_pred.away_win_prob * 100)


# Example 5: Batch Predictions
def example_batch_predictions() -> None:
    """Demonstrate batch predictions for multiple matches."""
    import numpy as np

    from src.prediction_engine.models.xgboost_model import XGBoostModel

    logger.info("=== Batch Predictions ===")

    model = XGBoostModel()

    # Create feature matrix for multiple matches
    features = np.array(
        [
            [0.7, 0.4, 0.6, 0.5, 0.65, 0.45, 0.2],  # Match 1
            [0.8, 0.5, 0.5, 0.6, 0.55, 0.55, 0.0],  # Match 2
            [0.6, 0.3, 0.8, 0.4, 0.45, 0.65, -0.1],  # Match 3
        ]
    )

    probs = model.predict_batch(features)

    logger.info("Predicted probabilities for %d matches:", len(features))
    for i, prob in enumerate(probs):
        logger.info(
            "  Match %d: Home %.1f%%, Draw %.1f%%, Away %.1f%%",
            i + 1,
            prob[0] * 100,
            prob[1] * 100,
            prob[2] * 100,
        )


# Example 6: Feature Importance
def example_feature_importance() -> None:
    """Demonstrate feature importance inspection."""
    import numpy as np

    from src.prediction_engine.models.xgboost_model import XGBoostModel

    logger.info("=== Feature Importance ===")

    # Create simple training data
    X_train = np.random.randn(100, 7)
    y_train = np.random.randint(0, 3, 100)

    # Train model
    xgb_model = XGBoostModel()

    try:
        xgb_model.train(X_train, y_train)
        importance = xgb_model.get_feature_importance()

        if importance:
            logger.info("XGBoost Feature Importance:")
            for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                logger.info("  %s: %.4f", feature, score)
        else:
            logger.info("(Models not trained with real data yet)")
    except Exception as e:
        logger.warning("Note: %s", e)


def run_all_examples() -> None:
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("ML Models and Ensemble Predictor Examples")
    logger.info("=" * 60)

    try:
        example_ensemble_prediction()
    except Exception as e:
        logger.error("Ensemble example error: %s", e)

    try:
        example_feature_engineering()
    except Exception as e:
        logger.error("Feature engineering example error: %s", e)

    try:
        example_direct_models()
    except Exception as e:
        logger.error("Direct models example error: %s", e)

    try:
        example_batch_predictions()
    except Exception as e:
        logger.error("Batch predictions example error: %s", e)

    logger.info("=" * 60)
    logger.info("Examples completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Run individual examples
    example_ensemble_prediction()
    example_feature_engineering()
    example_direct_models()
    example_batch_predictions()

    # Or run all with:
    # run_all_examples()
