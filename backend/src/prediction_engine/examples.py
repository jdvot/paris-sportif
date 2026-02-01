"""
Example usage of the ML models and ensemble predictor.

This file demonstrates:
1. Using the ensemble predictor with all models
2. Training new models from scratch
3. Feature engineering
4. Model evaluation
"""

from typing import List, Dict
import numpy as np

# Example 1: Using the Ensemble Predictor
def example_ensemble_prediction():
    """Demonstrate ensemble prediction with all models."""
    from src.prediction_engine.ensemble import EnsemblePredictor

    predictor = EnsemblePredictor()

    # Match data
    prediction = predictor.predict(
        # Team statistics for statistical models
        home_attack=2.1,      # Goals per match at home
        home_defense=1.3,     # Goals conceded per match at home
        away_attack=1.8,      # Goals per match away
        away_defense=1.5,     # Goals conceded per match away

        # ELO ratings
        home_elo=1650,
        away_elo=1550,

        # Optional: Expected Goals data
        home_xg_for=1.8,
        home_xg_against=0.9,
        away_xg_for=1.5,
        away_xg_against=1.2,

        # Optional: ML features
        recent_form_home=65.0,      # 0-100 scale
        recent_form_away=45.0,
        head_to_head_home=0.2,      # -1.0 to 1.0

        # Optional: Bookmaker odds for value calculation
        odds_home=2.1,
        odds_draw=3.2,
        odds_away=3.5,
    )

    # Results
    print("=== Ensemble Prediction ===")
    print(f"Home Win: {prediction.home_win_prob:.1%}")
    print(f"Draw: {prediction.draw_prob:.1%}")
    print(f"Away Win: {prediction.away_win_prob:.1%}")
    print(f"Recommended Bet: {prediction.recommended_bet}")
    print(f"Confidence: {prediction.confidence:.1%}")
    print(f"Model Agreement: {prediction.model_agreement:.1%}")
    print(f"Value Score: {prediction.value_score}")
    print(f"Expected Goals: {prediction.expected_home_goals:.1f}-{prediction.expected_away_goals:.1f}")

    # Model contributions
    if prediction.poisson_contribution:
        print(f"\nPoisson: {prediction.poisson_contribution.home_prob:.1%}")
    if prediction.elo_contribution:
        print(f"ELO: {prediction.elo_contribution.home_prob:.1%}")
    if prediction.xgboost_contribution:
        print(f"XGBoost: {prediction.xgboost_contribution.home_prob:.1%}")
    if prediction.random_forest_contribution:
        print(f"Random Forest: {prediction.random_forest_contribution.home_prob:.1%}")


# Example 2: Feature Engineering
def example_feature_engineering():
    """Demonstrate feature engineering capabilities."""
    from src.prediction_engine.feature_engineering import FeatureEngineer

    print("\n=== Feature Engineering ===")

    # Calculate recent form from match results
    home_results = [
        (2, 1),  # Won 2-1 (most recent)
        (1, 0),  # Won 1-0
        (0, 1),  # Lost 0-1
        (1, 1),  # Drew 1-1
    ]
    home_form = FeatureEngineer.calculate_recent_form(home_results, is_home=True)
    print(f"Home team recent form: {home_form:.1f}/100")

    # Calculate head-to-head
    h2h_results = [
        (1, 0),  # Won 1-0 (most recent)
        (2, 2),  # Drew 2-2
        (0, 1),  # Lost 0-1
    ]
    h2h_home = FeatureEngineer.calculate_head_to_head(h2h_results, is_home=True)
    print(f"H2H advantage (home): {h2h_home:.2f}")

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

    print(f"Engineered features shape: {features.to_array().shape}")
    print(f"Feature vector: {features}")


# Example 3: Training Models
def example_training():
    """Demonstrate model training."""
    from src.prediction_engine.model_trainer import ModelTrainer

    print("\n=== Model Training ===")

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

        match_data.append({
            "home_attack": home_attack,
            "home_defense": home_defense,
            "away_attack": away_attack,
            "away_defense": away_defense,
            "recent_form_home": home_form,
            "recent_form_away": away_form,
            "head_to_head_home": np.random.uniform(-1, 1),
            "outcome": outcome,
        })

    print(f"Generated {len(match_data)} synthetic matches")

    # Train models
    trainer = ModelTrainer()
    metrics = trainer.train_both_models(match_data, test_size=0.2)

    if metrics["xgboost"]:
        print(f"\nXGBoost:")
        print(f"  Accuracy: {metrics['xgboost'].accuracy:.2%}")
        print(f"  LogLoss: {metrics['xgboost'].logloss:.4f}")
        print(f"  Home F1: {metrics['xgboost'].f1_home:.3f}")

    if metrics["random_forest"]:
        print(f"\nRandom Forest:")
        print(f"  Accuracy: {metrics['random_forest'].accuracy:.2%}")
        print(f"  LogLoss: {metrics['random_forest'].logloss:.4f}")
        print(f"  Home F1: {metrics['random_forest'].f1_home:.3f}")


# Example 4: Direct Model Usage
def example_direct_models():
    """Demonstrate using models directly."""
    from src.prediction_engine.models.xgboost_model import XGBoostModel
    from src.prediction_engine.models.random_forest_model import RandomForestModel

    print("\n=== Direct Model Usage ===")

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

    print(f"XGBoost Prediction:")
    print(f"  Home Win: {xgb_pred.home_win_prob:.1%}")
    print(f"  Draw: {xgb_pred.draw_prob:.1%}")
    print(f"  Away Win: {xgb_pred.away_win_prob:.1%}")
    print(f"  Confidence: {xgb_pred.prediction_confidence:.1%}")

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

    print(f"\nRandom Forest Prediction:")
    print(f"  Home Win: {rf_pred.home_win_prob:.1%}")
    print(f"  Draw: {rf_pred.draw_prob:.1%}")
    print(f"  Away Win: {rf_pred.away_win_prob:.1%}")


# Example 5: Batch Predictions
def example_batch_predictions():
    """Demonstrate batch predictions for multiple matches."""
    from src.prediction_engine.models.xgboost_model import XGBoostModel
    import numpy as np

    print("\n=== Batch Predictions ===")

    model = XGBoostModel()

    # Create feature matrix for multiple matches
    features = np.array([
        [0.7, 0.4, 0.6, 0.5, 0.65, 0.45, 0.2],  # Match 1
        [0.8, 0.5, 0.5, 0.6, 0.55, 0.55, 0.0],  # Match 2
        [0.6, 0.3, 0.8, 0.4, 0.45, 0.65, -0.1], # Match 3
    ])

    probs = model.predict_batch(features)

    print(f"Predicted probabilities for {len(features)} matches:")
    for i, prob in enumerate(probs):
        print(f"  Match {i+1}: Home {prob[0]:.1%}, Draw {prob[1]:.1%}, Away {prob[2]:.1%}")


# Example 6: Feature Importance
def example_feature_importance():
    """Demonstrate feature importance inspection."""
    from src.prediction_engine.model_trainer import ModelTrainer
    from src.prediction_engine.models.xgboost_model import XGBoostModel
    import numpy as np

    print("\n=== Feature Importance ===")

    # Create simple training data
    X_train = np.random.randn(100, 7)
    y_train = np.random.randint(0, 3, 100)

    # Train model
    xgb_model = XGBoostModel()

    try:
        xgb_model.train(X_train, y_train)
        importance = xgb_model.get_feature_importance()

        if importance:
            print("XGBoost Feature Importance:")
            for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                print(f"  {feature}: {score:.4f}")
        else:
            print("(Models not trained with real data yet)")
    except Exception as e:
        print(f"Note: {e}")


def run_all_examples():
    """Run all examples."""
    print("=" * 60)
    print("ML Models and Ensemble Predictor Examples")
    print("=" * 60)

    try:
        example_ensemble_prediction()
    except Exception as e:
        print(f"Ensemble example error: {e}")

    try:
        example_feature_engineering()
    except Exception as e:
        print(f"Feature engineering example error: {e}")

    try:
        example_direct_models()
    except Exception as e:
        print(f"Direct models example error: {e}")

    try:
        example_batch_predictions()
    except Exception as e:
        print(f"Batch predictions example error: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run individual examples
    example_ensemble_prediction()
    example_feature_engineering()
    example_direct_models()
    example_batch_predictions()

    # Or run all with:
    # run_all_examples()
