# Testing Guide for Prediction Engine Improvements

## Quick Validation Tests

### 1. Poisson Model - Edge Case Handling

```python
from src.prediction_engine.models.poisson import PoissonModel

# Test case 1: Very low attack/defense (edge case)
poisson = PoissonModel()
exp_home, exp_away = poisson.calculate_expected_goals(
    home_attack=0.05,      # Very low
    home_defense=0.1,      # Very low
    away_attack=0.05,
    away_defense=0.05
)

print(f"Low stats test:")
print(f"  Expected home goals: {exp_home:.3f} (should be ~0.3-0.4)")
print(f"  Expected away goals: {exp_away:.3f} (should be ~0.3-0.4)")
assert 0.3 <= exp_home <= 5.0, "Home goals out of bounds"
assert 0.3 <= exp_away <= 5.0, "Away goals out of bounds"
print("  ✓ PASS - Smoothing prevents extreme values\n")

# Test case 2: High attack/defense (edge case)
exp_home, exp_away = poisson.calculate_expected_goals(
    home_attack=3.5,       # High
    home_defense=0.5,      # Good defense
    away_attack=2.0,
    away_defense=3.0       # Poor defense
)

print(f"High stats test:")
print(f"  Expected home goals: {exp_home:.3f} (should be reasonable)")
print(f"  Expected away goals: {exp_away:.3f} (should be reasonable)")
assert exp_home <= 5.0, "Home goals clamped too high"
assert exp_away <= 5.0, "Away goals clamped too high"
print("  ✓ PASS - High values clamped appropriately\n")

# Test case 3: Normal stats (typical match)
exp_home, exp_away = poisson.calculate_expected_goals(
    home_attack=1.5,       # Average to good attack
    home_defense=1.2,      # Slightly better defense
    away_attack=1.3,
    away_defense=1.4
)

print(f"Normal stats test:")
print(f"  Expected home goals: {exp_home:.3f} (should be ~1.3-1.5)")
print(f"  Expected away goals: {exp_away:.3f} (should be ~1.1-1.3)")
assert 0.8 <= exp_home <= 2.5, "Home goals not in typical range"
assert 0.8 <= exp_away <= 2.5, "Away goals not in typical range"
print("  ✓ PASS - Typical predictions look good\n")
```

### 2. Dixon-Coles Model - Time Decay

```python
from src.prediction_engine.models.dixon_coles import DixonColesModel
import math

# Test case: Time decay calculation
dc = DixonColesModel()

# Weight should be ~0.5 at half-life
days_at_half_life = 46  # Should be ~46 days with new xi=0.0015
weight = dc.time_weight(days_at_half_life)

print(f"Time decay test:")
print(f"  Weight at {days_at_half_life} days: {weight:.3f} (should be ~0.5)")
assert 0.45 <= weight <= 0.55, f"Half-life not at {days_at_half_life} days"
print("  ✓ PASS - Time decay properly configured\n")

# Older matches should get less weight
old_weight = dc.time_weight(120)
recent_weight = dc.time_weight(7)
print(f"  Recent (7 days): {recent_weight:.3f}")
print(f"  Old (120 days): {old_weight:.3f}")
assert recent_weight > old_weight, "Recent matches not weighted higher"
print("  ✓ PASS - Recent matches weighted higher\n")
```

### 3. ELO Model - Draw Probability Calibration

```python
from src.prediction_engine.models.elo import ELOSystem

# Test case: Draw probability with even teams
elo = ELOSystem()

# Even teams (same rating, no home advantage difference)
home_prob, draw_prob, away_prob = elo.calculate_outcome_probabilities(
    home_rating=1500,
    away_rating=1500
)

print(f"Even teams draw probability test:")
print(f"  Home: {home_prob:.3f}")
print(f"  Draw: {draw_prob:.3f}")
print(f"  Away: {away_prob:.3f}")
print(f"  Sum: {home_prob + draw_prob + away_prob:.3f}")
assert 0.26 <= draw_prob <= 0.28, f"Draw prob should be ~0.27, got {draw_prob}"
assert abs((home_prob + draw_prob + away_prob) - 1.0) < 0.001, "Probabilities don't sum to 1"
print("  ✓ PASS - Draw probability ~27% for even teams\n")

# Test case: Draw probability with uneven teams
home_prob, draw_prob, away_prob = elo.calculate_outcome_probabilities(
    home_rating=1800,  # Strong home team
    away_rating=1200   # Weak away team
)

print(f"Uneven teams draw probability test:")
print(f"  Home: {home_prob:.3f}")
print(f"  Draw: {draw_prob:.3f}")
print(f"  Away: {away_prob:.3f}")
assert draw_prob < 0.27, f"Draw prob should be <0.27, got {draw_prob}"
assert home_prob > away_prob, "Strong home should have higher win prob"
print("  ✓ PASS - Draw probability decreases with rating difference\n")
```

### 4. Advanced ELO - Recent Form Rating

```python
from src.prediction_engine.models.elo_advanced import AdvancedELOSystem

# Test case: Recent form rating
adv_elo = AdvancedELOSystem()

# Perfect form
perf = adv_elo.recent_performance_rating(["W", "W", "W", "W", "W"])
print(f"Perfect form test:")
print(f"  Performance rating: {perf:.3f} (should be ~+0.8)")
assert 0.7 <= perf <= 0.8, f"Perfect form should be ~0.8, got {perf}"
print("  ✓ PASS - Perfect form properly recognized\n")

# Poor form
perf = adv_elo.recent_performance_rating(["L", "L", "L", "L", "L"])
print(f"Poor form test:")
print(f"  Performance rating: {perf:.3f} (should be ~-0.8)")
assert -0.8 <= perf <= -0.7, f"Poor form should be ~-0.8, got {perf}"
print("  ✓ PASS - Poor form properly penalized\n")

# Mixed form (recent W, older L)
perf = adv_elo.recent_performance_rating(["L", "L", "L", "W", "W", "W"])
print(f"Mixed form (improving) test:")
print(f"  Performance rating: {perf:.3f} (should be positive)")
assert perf > 0, f"Improving form should be positive, got {perf}"
print("  ✓ PASS - Recent wins weighted more\n")

# Clamping test - shouldn't exceed bounds
extreme = ["W"] * 20
perf = adv_elo.recent_performance_rating(extreme)
print(f"Extreme form clamping test:")
print(f"  Performance rating: {perf:.3f} (clamped to max 0.8)")
assert perf <= 0.8, f"Performance rating should be clamped to 0.8, got {perf}"
print("  ✓ PASS - Performance rating clamped\n")
```

### 5. Ensemble Confidence - Multi-factor

```python
from src.prediction_engine.ensemble import EnsemblePredictor

# Test case: Confidence calculation
ens = EnsemblePredictor()

# High confidence prediction (one outcome clearly dominant)
conf = ens._calculate_confidence(
    home_prob=0.70,
    draw_prob=0.20,
    away_prob=0.10
)
print(f"High confidence prediction test:")
print(f"  Confidence: {conf:.3f} (should be high, ~0.8-0.95)")
assert conf > 0.75, f"Clear prediction should have high confidence"
print("  ✓ PASS - High confidence for clear predictions\n")

# Low confidence prediction (probabilities spread)
conf = ens._calculate_confidence(
    home_prob=0.40,
    draw_prob=0.35,
    away_prob=0.25
)
print(f"Low confidence prediction test:")
print(f"  Confidence: {conf:.3f} (should be low, ~0.52-0.65)")
assert conf < 0.70, f"Close prediction should have lower confidence"
print("  ✓ PASS - Low confidence for uncertain predictions\n")

# Uncertainty test
conf = ens._calculate_confidence(
    home_prob=0.33,
    draw_prob=0.34,
    away_prob=0.33
)
print(f"Maximum uncertainty test:")
print(f"  Confidence: {conf:.3f} (should be minimum, ~0.52)")
assert 0.50 <= conf <= 0.54, f"Maximum uncertainty should be ~0.52"
print("  ✓ PASS - Baseline confidence for uniform distribution\n")
```

### 6. Advanced Ensemble - Model Agreement

```python
from src.prediction_engine.ensemble_advanced import AdvancedEnsemblePredictor

# Test case: Model agreement metric
adv_ens = AdvancedEnsemblePredictor()

# Perfect agreement (all models predict same)
predictions = [
    (0.70, 0.20, 0.10),  # All predict home
    (0.72, 0.18, 0.10),
    (0.68, 0.22, 0.10),
    (0.71, 0.19, 0.10),
]
weights = [0.40, 0.35, 0.15, 0.10]

agreement = adv_ens._calculate_model_agreement(predictions, weights)
print(f"Perfect agreement test:")
print(f"  Agreement: {agreement:.3f} (should be high, ~0.9-1.0)")
assert agreement > 0.85, f"Perfect agreement should be >0.85"
print("  ✓ PASS - Perfect agreement detected\n")

# Disagreement (mixed predictions)
predictions = [
    (0.50, 0.25, 0.25),  # Slight home lean
    (0.25, 0.50, 0.25),  # Draw prediction
    (0.20, 0.20, 0.60),  # Away prediction
    (0.40, 0.35, 0.25),  # Home lean
]
weights = [0.40, 0.35, 0.15, 0.10]

agreement = adv_ens._calculate_model_agreement(predictions, weights)
print(f"Disagreement test:")
print(f"  Agreement: {agreement:.3f} (should be low, ~0.3-0.5)")
assert agreement < 0.70, f"Disagreement should give low agreement"
print("  ✓ PASS - Model disagreement detected\n")
```

### 7. LLM Adjustment Safety

```python
from src.prediction_engine.ensemble import EnsemblePredictor, LLMAdjustments

# Test case: LLM adjustment doesn't override predictions
ens = EnsemblePredictor()

base_probs = (0.60, 0.30, 0.10)  # Clear home prediction

# Extreme LLM adjustments (shouldn't completely flip prediction)
adjustments = LLMAdjustments(
    injury_impact_home=-0.3,  # Max injury impact
    injury_impact_away=0.0,
    sentiment_home=0.0,
    sentiment_away=0.0,
    tactical_edge=0.0,
    reasoning="Test extreme adjustment"
)

adj_probs = ens._apply_llm_adjustments(
    base_probs[0], base_probs[1], base_probs[2],
    adjustments
)

print(f"LLM adjustment safety test:")
print(f"  Base: {base_probs[0]:.3f} (home)")
print(f"  After: {adj_probs[0]:.3f} (home)")
print(f"  Still predicts home: {adj_probs[0] > max(adj_probs[1], adj_probs[2])}")
assert adj_probs[0] > max(adj_probs[1], adj_probs[2]), "LLM overrode prediction"
assert base_probs[0] - 0.20 <= adj_probs[0] <= base_probs[0], "LLM adjustment too extreme"
print("  ✓ PASS - LLM adjusts but doesn't override\n")
```

## Backtesting Guide

### Full Backtest Implementation

```python
from datetime import datetime, timedelta
from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor
import numpy as np

# Pseudo-code for backtest
def backtest_ensemble(historical_matches: list) -> dict:
    """
    Run backtesting on historical matches.

    Args:
        historical_matches: List of dicts with:
            - date, home_team, away_team
            - home_attack, home_defense, away_attack, away_defense
            - home_xg_for, home_xg_against, away_xg_for, away_xg_against
            - home_recent_form, away_recent_form
            - actual_result (0=away, 1=draw, 2=home)

    Returns:
        Calibration metrics and statistics
    """
    predictions = []
    actuals = []
    confidences = []

    for match in historical_matches:
        pred = advanced_ensemble_predictor.predict(
            home_attack=match['home_attack'],
            home_defense=match['home_defense'],
            away_attack=match['away_attack'],
            away_defense=match['away_defense'],
            home_elo=match['home_elo'],
            away_elo=match['away_elo'],
            home_xg_for=match.get('home_xg_for'),
            home_xg_against=match.get('home_xg_against'),
            away_xg_for=match.get('away_xg_for'),
            away_xg_against=match.get('away_xg_against'),
            home_recent_form=match.get('home_recent_form'),
            away_recent_form=match.get('away_recent_form'),
        )

        # Map prediction to 0-2
        if pred.recommended_bet == 'home':
            pred_outcome = 2
        elif pred.recommended_bet == 'away':
            pred_outcome = 0
        else:
            pred_outcome = 1

        predictions.append(pred_outcome)
        actuals.append(match['actual_result'])

        # Store probabilities for calibration
        if match['actual_result'] == 0:  # Away win
            confidences.append(pred.away_win_prob)
        elif match['actual_result'] == 1:  # Draw
            confidences.append(pred.draw_prob)
        else:  # Home win
            confidences.append(pred.home_win_prob)

    # Calculate metrics
    accuracy = np.mean(np.array(predictions) == np.array(actuals))

    # Calibration: group by confidence and check agreement
    calibration = check_calibration(actuals, confidences)

    # Brier score
    brier = calculate_brier_score(actuals, confidences)

    return {
        'accuracy': accuracy,
        'calibration': calibration,
        'brier_score': brier,
    }

def check_calibration(actuals, confidences):
    """
    Check if predicted probabilities match actual frequencies.
    Perfect calibration: 60% predictions win ~60% of time
    """
    bins = [0.0, 0.33, 0.5, 0.67, 1.0]
    calibration_data = []

    for low, high in zip(bins[:-1], bins[1:]):
        mask = (np.array(confidences) >= low) & (np.array(confidences) < high)
        if mask.any():
            bin_conf = np.mean(np.array(confidences)[mask])
            bin_accuracy = np.mean(np.array(actuals)[mask])
            calibration_data.append({
                'confidence_range': f"{low:.2f}-{high:.2f}",
                'predicted_prob': bin_conf,
                'actual_freq': bin_accuracy,
                'calibration_error': abs(bin_conf - bin_accuracy),
                'sample_size': mask.sum()
            })

    return calibration_data

def calculate_brier_score(actuals, predicted_probs):
    """
    Brier Score = mean((predicted - actual)^2)
    Lower is better, perfect = 0, random = 0.667
    """
    # Convert actuals to binary (win vs loss)
    binary_actuals = np.array([1.0 if a > 0.5 else 0.0 for a in actuals])
    return np.mean((np.array(predicted_probs) - binary_actuals) ** 2)
```

## Expected Results

After improvements, you should see:

1. **Better Calibration**: Confidence scores match actual accuracy
   - 60% predictions should win ~58-62% of time
   - 70% predictions should win ~68-72% of time
   - Calibration error reduced

2. **Better Accuracy**: Improved model predictions
   - Fewer extreme predictions
   - Better handling of recent form
   - Better home/away balance

3. **Better Robustness**: More stable with edge cases
   - No NaN or infinite values
   - Consistent behavior with extreme stats
   - Graceful degradation with limited data

4. **Lower Brier Score**: Better probability estimates
   - Before: Typical ~0.18-0.22
   - After: Expected ~0.16-0.20
   - Improvement: ~5-15%

## Regression Testing

Make sure improvements didn't break anything:

```python
# Test all predictions complete without error
from src.prediction_engine.models import (
    poisson_model, dixon_coles_model, elo_system, advanced_elo_system
)
from src.prediction_engine.ensemble import ensemble_predictor
from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor

test_stats = {
    'home_attack': 1.5,
    'home_defense': 1.2,
    'away_attack': 1.3,
    'away_defense': 1.4,
    'home_elo': 1600,
    'away_elo': 1400,
    'home_xg_for': 1.8,
    'home_xg_against': 1.2,
    'away_xg_for': 1.5,
    'away_xg_against': 1.6,
    'home_recent_form': ['W', 'D', 'W'],
    'away_recent_form': ['L', 'L', 'D'],
}

# All models should return predictions without error
print("Regression Testing:")
print("✓ Poisson:", poisson_model.predict(**{k: v for k, v in test_stats.items() if k in ['home_attack', 'home_defense', 'away_attack', 'away_defense']}))
print("✓ Dixon-Coles:", dixon_coles_model.predict(**{k: v for k, v in test_stats.items() if k in ['home_attack', 'home_defense', 'away_attack', 'away_defense']}))
print("✓ ELO:", elo_system.predict(test_stats['home_elo'], test_stats['away_elo']))
print("✓ Advanced ELO:", advanced_elo_system.predict(**{k: v for k, v in test_stats.items() if k in ['home_elo', 'away_elo', 'home_recent_form', 'away_recent_form']}))
print("✓ Ensemble:", ensemble_predictor.predict(**{k: v for k, v in test_stats.items() if k in ['home_attack', 'home_defense', 'away_attack', 'away_defense', 'home_elo', 'away_elo']}))
print("✓ Advanced Ensemble:", advanced_ensemble_predictor.predict(**test_stats))
print("\nAll models working correctly!")
```

---

## Success Criteria

✓ All models return valid predictions
✓ No NaN or infinite values in outputs
✓ Confidence scores in valid range [0, 1]
✓ Probabilities sum to 1.0
✓ Better calibration on backtests
✓ No breaking changes to existing code
