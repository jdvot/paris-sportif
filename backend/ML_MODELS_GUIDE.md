# Machine Learning Models Guide

## Overview

This guide documents the machine learning models integrated into the Paris Sportif prediction engine. The system now includes XGBoost and Random Forest models alongside traditional statistical methods.

## Available Models

### Current Implementation

1. **Poisson Model** (25% weight)
   - Statistical baseline using goal distributions
   - Historical data: attack/defense strength metrics
   - Outputs: Win/Draw/Loss probabilities, Expected Goals

2. **ELO System** (15% weight)
   - Chess-inspired rating system adapted for football
   - Captures team strength dynamics
   - Updates after each match

3. **xG Model** (25% weight)
   - Uses Expected Goals (xG) data
   - More predictive than actual goals
   - Only available when xG stats present

4. **XGBoost Model** (35% weight) - **NEW**
   - Gradient boosting ensemble
   - Captures complex feature interactions
   - Available: XGBoost 2.1.0+ in requirements.txt

5. **Random Forest Model** (15% weight) - **NEW**
   - Decision tree ensemble backup
   - Robust to outliers
   - Complements XGBoost predictions

## Model Features

### Input Features

All ML models (XGBoost and Random Forest) use these features:

```python
[
    "home_attack",        # Home team attack strength (0.3-3.5 goals/match)
    "home_defense",       # Home team defense strength
    "away_attack",        # Away team attack strength
    "away_defense",       # Away team defense strength
    "recent_form_home",   # Home team form (0-100 scale)
    "recent_form_away",   # Away team form (0-100 scale)
    "head_to_head_home",  # H2H advantage (-1.0 to 1.0)
]
```

### Feature Engineering

The `feature_engineering.py` module provides:

1. **Normalization**
   - Scales attack/defense to [0, 1] range
   - Normalizes form scores
   - Clips outliers

2. **Recent Form Calculation**
   - Time-weighted results (recent matches weighted higher)
   - Decay rate: 0.9 (90% of previous match weight)
   - Formula: win=1.0, draw=0.5, loss=0.0
   - Bonus for goal differential (+0.2 max)

3. **Head-to-Head Scoring**
   - Win percentage minus loss percentage
   - Range: -1.0 (always lose) to 1.0 (always win)
   - Recency bonus for recent matches

4. **Interaction Features** (optional)
   - Attack vs Defense matchups
   - Strength ratios
   - Form advantages
   - Combined team strength

## Training

### Model Trainer Class

Located in `src/prediction_engine/model_trainer.py`:

```python
from src.prediction_engine.model_trainer import ModelTrainer

trainer = ModelTrainer()

# Prepare data
match_data = [
    {
        "home_attack": 2.1,
        "home_defense": 1.3,
        "away_attack": 1.8,
        "away_defense": 1.5,
        "recent_form_home": 65.0,
        "recent_form_away": 45.0,
        "head_to_head_home": 0.2,
        "outcome": 0,  # 0=home_win, 1=draw, 2=away_win
    },
    # ... more matches
]

# Train both models
results = trainer.train_both_models(match_data, test_size=0.2)
# Returns: {"xgboost": ModelMetrics, "random_forest": ModelMetrics}

# Save trained models
trainer.save_models("/path/to/models/")

# Load trained models
trainer.load_models("/path/to/models/")
```

### Data Format

Match data should contain:

- **Required**: home_attack, home_defense, away_attack, away_defense, outcome
- **Optional**: recent_form_home, recent_form_away, head_to_head_home
- **Optional**: home_recent_results, away_recent_results, h2h_results (for auto-calculation)

Outcome classes:
- `0`: Home team wins
- `1`: Draw
- `2`: Away team wins

### Training Parameters

**XGBoost**:
- Max depth: 6
- Learning rate: 0.1
- Estimators: 200
- Subsample: 0.8
- Colsample: 0.8

**Random Forest**:
- Estimators: 100
- Max depth: 12
- Min samples split: 5
- Max features: sqrt
- OOB score: enabled

## Usage

### Direct Model Usage

```python
from src.prediction_engine.models.xgboost_model import XGBoostModel
from src.prediction_engine.models.random_forest_model import RandomForestModel

# XGBoost
xgb_model = XGBoostModel()
xgb_pred = xgb_model.predict(
    home_attack=2.1,
    home_defense=1.3,
    away_attack=1.8,
    away_defense=1.5,
    recent_form_home=65.0,
    recent_form_away=45.0,
    head_to_head_home=0.2,
)
print(f"Home win: {xgb_pred.home_win_prob:.2%}")
print(f"Draw: {xgb_pred.draw_prob:.2%}")
print(f"Away win: {xgb_pred.away_win_prob:.2%}")

# Random Forest
rf_model = RandomForestModel()
rf_pred = rf_model.predict(...)
```

### Ensemble Integration

```python
from src.prediction_engine.ensemble import EnsemblePredictor

predictor = EnsemblePredictor()

prediction = predictor.predict(
    # Poisson/ELO features
    home_attack=2.1,
    home_defense=1.3,
    away_attack=1.8,
    away_defense=1.5,
    home_elo=1650,
    away_elo=1550,

    # Optional xG
    home_xg_for=1.8,
    home_xg_against=0.9,
    away_xg_for=1.5,
    away_xg_against=1.2,

    # ML model features
    recent_form_home=65.0,
    recent_form_away=45.0,
    head_to_head_home=0.2,
)

# Results
print(f"Final prediction: {prediction.recommended_bet}")
print(f"Confidence: {prediction.confidence:.2%}")
print(f"Model agreement: {prediction.model_agreement:.2%}")
print(f"Expected goals: {prediction.expected_home_goals:.1f}-{prediction.expected_away_goals:.1f}")
```

## Evaluation Metrics

Models are evaluated on a test set with:

- **Accuracy**: Overall correctness
- **Precision** (per outcome): Positive prediction accuracy
- **Recall** (per outcome): True positive rate
- **F1 Score** (per outcome): Harmonic mean of precision/recall
- **Log Loss**: Probability calibration quality

## Model Agreement

The ensemble calculates "model agreement" (0-1 scale) indicating consensus:

- `0.8+`: Strong agreement, high confidence
- `0.5-0.8`: Moderate agreement
- `<0.5`: Low agreement, models disagree

High disagreement can indicate uncertain matches (e.g., evenly matched teams).

## Feature Importance

After training, inspect which features matter most:

```python
# For XGBoost
importance = xgb_model.get_feature_importance()
for feature, score in importance.items():
    print(f"{feature}: {score:.4f}")

# For Random Forest
importance = rf_model.get_feature_importance()
for feature, score in importance.items():
    print(f"{feature}: {score:.4f}")
```

## Fallback Behavior

When models are not trained or libraries unavailable:

1. XGBoost unavailable → Random Forest used
2. Random Forest unavailable → Simple heuristic
3. Heuristic: `home_strength / (home_strength + away_strength + 1)`

## Performance Notes

### Advantages of XGBoost
- Captures non-linear patterns
- Handles feature interactions
- Often achieves higher accuracy
- Gradient boosting typically beats random forests

### Advantages of Random Forest
- More interpretable
- Less hyperparameter tuning needed
- Robust to outliers
- Good for initial validation

### Recommended Usage
- **XGBoost** (35%): Primary ML model, highest weight
- **Random Forest** (15%): Backup, validates XGBoost
- **Poisson + ELO + xG** (65%): Stable baselines

## Integration with Betting Systems

The ensemble provides:

1. **Predicted Probabilities**: Combined from all models
2. **Confidence Score**: Calibrated to [0.52, 0.98] range
3. **Model Agreement**: Helps detect uncertain predictions
4. **Expected Goals**: From Poisson distribution
5. **Value Score**: Against bookmaker odds (if provided)

## Future Enhancements

Potential additions:

1. **Neural Networks** (if TensorFlow available)
2. **LSTM** for form trends
3. **Gradient Boosting Variants** (LightGBM, CatBoost)
4. **Ensemble Stacking** (meta-learner on top of models)
5. **Temporal Features** (recent momentum, seasonality)
6. **Team-specific Models** (per-league calibration)
7. **Injury Data Integration**
8. **Sentiment Analysis** (from news/social media)

## Troubleshooting

### Models not training
Check that XGBoost/scikit-learn are installed:
```bash
python -c "import xgboost; import sklearn; print('OK')"
```

### Low accuracy
- Ensure outcome labels are correct (0, 1, 2)
- Check feature distributions (outliers?)
- Verify training data quality
- Consider feature engineering improvements

### Predictions don't match expectations
- Verify input features are in expected ranges
- Check that models are trained (is_trained flag)
- Compare with Poisson baseline
- Review model agreement score

### Performance regression
- Retrain models with latest data
- Check for data quality issues
- Monitor concept drift over time
- Consider rebalancing ensemble weights

## Files Structure

```
prediction_engine/
├── models/
│   ├── xgboost_model.py           # XGBoost implementation
│   ├── random_forest_model.py     # Random Forest implementation
│   ├── poisson.py                 # Poisson model
│   ├── elo.py                     # ELO system
│   └── elo_advanced.py            # Advanced ELO
├── feature_engineering.py          # Feature preparation
├── model_trainer.py               # Training utilities
├── ensemble.py                    # Main ensemble (updated)
├── ensemble_advanced.py           # Advanced ensemble variant
└── ML_MODELS_GUIDE.md            # This file
```

## References

- XGBoost: https://xgboost.readthedocs.io/
- Random Forest: https://scikit-learn.org/stable/modules/ensemble.html
- Football prediction: https://dashee87.github.io/data%20science/football/
- Poisson regression: https://www.sas.com/en_us/insights/analytics/poisson-regression.html
