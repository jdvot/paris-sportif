# Modèles de Prédiction - Paris Sportif

Documentation technique des modèles de prédiction utilisés pour les pronostics football.

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────────┐
│                      EnsemblePredictor                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Poisson  │  │   ELO    │  │    xG    │  │     XGBoost      │ │
│  │   25%    │  │   15%    │  │   25%    │  │       35%        │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │             │             │                  │          │
│       └─────────────┴──────┬──────┴──────────────────┘          │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │ Weighted Average │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  LLM Adjustments │ (±0.5 max via log-odds)  │
│                   └────────┬────────┘                           │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │ Final Prediction │                           │
│                   └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Modèle Poisson

**Fichier**: `src/prediction_engine/models/poisson.py`

### Principe

Le modèle de Poisson modélise le nombre de buts marqués par chaque équipe comme des événements indépendants suivant une distribution de Poisson.

### Formule Mathématique

```
P(X = k) = (λ^k × e^(-λ)) / k!

où:
- X = nombre de buts
- λ = expected goals (paramètre)
- k = nombre exact de buts (0, 1, 2, ...)
```

### Calcul des Expected Goals (λ)

```python
λ_home = home_attack_strength × away_defense_weakness × home_advantage × league_avg
λ_away = away_attack_strength × home_defense_weakness × league_avg

où:
- home_advantage = 1.15 (15% boost)
- league_avg = 1.375 buts/équipe (2.75 total)
```

### Paramètres

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `HOME_ADVANTAGE` | 1.15 | Multiplicateur buts domicile |
| `MAX_GOALS` | 8 | Maximum buts considérés |
| `league_avg_goals` | 2.75 | Moyenne buts/match |

### Sortie

```python
@dataclass
class PoissonPrediction:
    home_win_prob: float      # P(home > away)
    draw_prob: float          # P(home = away)
    away_win_prob: float      # P(home < away)
    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: tuple[int, int]  # e.g., (2, 1)
    score_probabilities: dict[tuple[int, int], float]
```

### Forces et Faiblesses

| Forces | Faiblesses |
|--------|------------|
| Fondement statistique solide | Suppose indépendance des buts |
| Prédit les scores exacts | Ne capture pas les corrélations |
| Interprétable | Sensible aux outliers |

---

## 2. Système ELO

**Fichier**: `src/prediction_engine/models/elo.py`

### Principe

Système de classement adapté du chess. Chaque équipe a un rating qui évolue après chaque match selon le résultat et la différence de rating.

### Formule ELO Standard

```
E_A = 1 / (1 + 10^((R_B - R_A) / 400))

où:
- E_A = score attendu pour équipe A
- R_A, R_B = ratings des équipes
```

### Mise à Jour Post-Match

```
R'_A = R_A + K × (S_A - E_A)

où:
- K = 20 (facteur de volatilité)
- S_A = résultat réel (1=victoire, 0.5=nul, 0=défaite)
```

### Paramètres

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `INITIAL_RATING` | 1500 | Rating initial nouvelles équipes |
| `K_FACTOR` | 20 | Volatilité des changements |
| `HOME_ADVANTAGE` | 100 | Points ELO avantage domicile |
| `DRAW_FACTOR` | 0.4 | Facteur probabilité nul |

### Conversion Rating → Probabilités

```python
def calculate_outcome_probabilities(home_rating, away_rating):
    # Ajuster pour avantage domicile
    adjusted_home = home_rating + 100

    # Score attendu
    exp_score = 1 / (1 + 10**((away_rating - adjusted_home) / 400))

    # Probabilité nul basée sur proximité des ratings
    draw_prob = 0.26 × (1 - abs(exp_score - 0.5) × 2)

    # Distribuer le reste
    remaining = 1 - draw_prob
    home_prob = remaining × exp_score
    away_prob = remaining × (1 - exp_score)
```

### Forces et Faiblesses

| Forces | Faiblesses |
|--------|------------|
| Simple et robuste | Ignore le contexte du match |
| Auto-ajustement continu | Lent à réagir aux changements |
| Historique long terme | Pas de features additionnelles |

---

## 3. Modèle xG (Expected Goals)

**Fichier**: `src/prediction_engine/models/poisson.py` (méthode `predict_with_xg`)

### Principe

Utilise les données xG (Expected Goals) des matchs précédents au lieu des buts réels. Le xG mesure la qualité des occasions créées.

### Différence avec Poisson Standard

```
Poisson Standard:   λ = buts_marqués_moyens
Poisson xG:         λ = xG_moyen

xG est plus prédictif car:
- Élimine la variance due à la finition
- Capture la création d'occasions
- Moins sensible aux scores atypiques
```

### Calcul

```python
λ_home = home_xG_avg × (away_xGA_avg / league_xGA_avg) × home_advantage
λ_away = away_xG_avg × (home_xGA_avg / league_xGA_avg)

où:
- xG = expected goals créés
- xGA = expected goals concédés
```

### Forces et Faiblesses

| Forces | Faiblesses |
|--------|------------|
| Plus stable que buts réels | Nécessite données xG |
| Capture qualité du jeu | Données pas toujours disponibles |
| Meilleur prédicteur long terme | Ignore finition exceptionnelle |

---

## 4. Modèle XGBoost

**Fichier**: `src/prediction_engine/models/xgboost_model.py`

### Principe

Gradient Boosting sur arbres de décision. Apprend les patterns complexes et interactions entre features.

### Features Utilisées (14 features)

**Base (7 features):**
```python
FEATURE_NAMES = [
    "home_attack",      # Force offensive domicile
    "home_defense",     # Force défensive domicile
    "away_attack",      # Force offensive extérieur
    "away_defense",     # Force défensive extérieur
    "home_form",        # Forme récente (0-100)
    "away_form",        # Forme récente (0-100)
    "head_to_head",     # Historique confrontations (0-1)
]
```

**Interactions (7 features):**
```python
INTERACTION_FEATURES = [
    "attack_diff",           # home_attack - away_defense
    "defense_diff",          # away_attack - home_defense
    "form_diff",             # home_form - away_form
    "attack_ratio",          # home_attack / away_attack
    "defense_ratio",         # home_defense / away_defense
    "overall_strength_home", # (attack + 1/defense) × form
    "overall_strength_away", # (attack + 1/defense) × form
]
```

### Hyperparamètres

```python
DEFAULT_PARAMS = {
    "objective": "multi:softprob",
    "num_class": 3,
    "max_depth": 6,
    "learning_rate": 0.1,
    "n_estimators": 200,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 1,
    "gamma": 0,
    "eval_metric": "mlogloss",
}
```

### Optimisation Optuna

Le module `model_trainer.py` utilise Optuna pour optimiser les hyperparamètres:

```python
def objective(trial):
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("lr", 0.01, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample", 0.6, 1.0),
    }
    return cross_val_score(model, X, y, cv=5).mean()
```

### Calibration des Probabilités

**Fichier**: `src/prediction_engine/calibration.py`

Deux méthodes disponibles:

1. **Platt Scaling**: Régression logistique sur les scores
2. **Isotonic Regression**: Transformation monotone non-paramétrique

```python
calibrator = ProbabilityCalibrator(method="platt")  # ou "isotonic"
calibrator.fit(raw_probs, actual_outcomes)
calibrated = calibrator.calibrate(new_probs)
```

### Forces et Faiblesses

| Forces | Faiblesses |
|--------|------------|
| Capture interactions complexes | Boîte noire |
| Performant avec peu de données | Risque d'overfitting |
| Gère les valeurs manquantes | Nécessite entraînement |

---

## 5. Ensemble et Pondération

**Fichier**: `src/prediction_engine/ensemble.py`

### Poids par Défaut

```python
WEIGHT_POISSON = 0.25   # 25%
WEIGHT_ELO = 0.15       # 15%
WEIGHT_XG = 0.25        # 25%
WEIGHT_XGBOOST = 0.35   # 35%
```

### Poids Adaptatifs (PAR-69)

**Fichier**: `src/prediction_engine/adaptive_weights.py`

Les poids s'ajustent selon la performance récente:

```python
class AdaptiveWeightCalculator:
    def calculate_weights(self):
        # Performance sur 30 derniers jours
        accuracies = {model: self.get_rolling_accuracy(model) for model in MODELS}

        # Softmax avec température
        weights = softmax(accuracies / temperature)

        # Minimum 5% par modèle
        weights = np.maximum(weights, 0.05)
        return normalize(weights)
```

### Combinaison Pondérée

```python
final_home = Σ(weight_i × prob_home_i)
final_draw = Σ(weight_i × prob_draw_i)
final_away = Σ(weight_i × prob_away_i)

# Normalisation
total = final_home + final_draw + final_away
final_probs = (final_home/total, final_draw/total, final_away/total)
```

---

## 6. Ajustements LLM

**Fichiers**: `src/llm/adjustments.py`, `src/prediction_engine/ensemble.py`

### Types d'Ajustements

| Type | Plage | Description |
|------|-------|-------------|
| `injury_impact` | -0.3 à 0.0 | Impact blessures clés |
| `sentiment` | -0.1 à 0.1 | Moral équipe (news) |
| `tactical_edge` | -0.05 à 0.05 | Avantage tactique |
| `form_adjustment` | -0.15 à 0.15 | Tendance forme récente |

### Application via Log-Odds

Les ajustements sont appliqués dans l'espace log-odds pour préserver la cohérence:

```python
def apply_adjustment(prob, adjustment):
    # Clamp pour éviter log(0)
    prob = np.clip(prob, 0.01, 0.99)

    # Convertir en log-odds
    logit = np.log(prob / (1 - prob))

    # Appliquer ajustement (max ±0.5)
    adjusted_logit = logit + np.clip(adjustment, -0.5, 0.5)

    # Reconvertir en probabilité
    return 1 / (1 + np.exp(-adjusted_logit))
```

### Validation Pydantic (PAR-66)

```python
class InjuryAnalysis(BaseModel):
    player_name: str | None
    impact_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    is_key_player: bool = False

    @field_validator("impact_score", mode="before")
    def coerce_impact(cls, v):
        if isinstance(v, str):
            return float(v)
        return v
```

---

## 7. Métriques de Performance

### Backtesting (PAR-63)

**Fichier**: `src/prediction_engine/backtesting.py`

```python
class WalkForwardBacktest:
    def run(self, matches, train_window=365, test_window=30):
        results = []
        for fold in rolling_splits(matches, train_window, test_window):
            model.train(fold.train_data)
            preds = model.predict(fold.test_data)
            metrics = calculate_metrics(preds, fold.actuals)
            results.append(metrics)
        return aggregate(results)
```

### Métriques Calculées

| Métrique | Description | Cible |
|----------|-------------|-------|
| **Accuracy** | % prédictions correctes | > 60% |
| **Brier Score** | Erreur quadratique probabilités | < 0.22 |
| **Log Loss** | Cross-entropy | < 1.0 |
| **Calibration Error** | Écart prédit vs réel | < 5% |
| **ROI** | Return on Investment simulé | > 5% |

### Explicabilité SHAP (PAR-73)

**Fichier**: `src/prediction_engine/explainability.py`

```python
explainer = PredictionExplainer(model)
explanation = explainer.explain(features)

# Output
{
    "predicted_outcome": "home_win",
    "confidence": 0.65,
    "top_factors": [
        {"feature": "home_attack", "contribution": 0.15, "direction": "positive"},
        {"feature": "away_form", "contribution": -0.08, "direction": "negative"},
    ]
}
```

---

## 8. Références

### Académiques

1. **Poisson pour le football**: [Maher, M.J. (1982)](https://www.jstor.org/stable/2348066)
2. **ELO pour le sport**: [Hvattum & Arntzen (2010)](https://www.sciencedirect.com/science/article/abs/pii/S0169207009001459)
3. **XGBoost**: [Chen & Guestrin (2016)](https://arxiv.org/abs/1603.02754)

### Tutoriels

- [Predicting Football Results with Statistical Modelling](https://dashee87.github.io/data%20science/football/r/predicting-football-results-with-statistical-modelling/)
- [ELO Ratings Explained](https://www.eloratings.net/about)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)

---

## 9. Schéma de Données

### Input Match

```python
@dataclass
class MatchInput:
    home_team: str
    away_team: str
    home_attack: float       # Moyenne buts marqués dom
    home_defense: float      # Moyenne buts encaissés dom
    away_attack: float       # Moyenne buts marqués ext
    away_defense: float      # Moyenne buts encaissés ext
    home_xg: float | None    # xG moyen (optionnel)
    away_xg: float | None
    home_elo: float          # Rating ELO
    away_elo: float
    home_form: float         # 0-100
    away_form: float
    head_to_head: float      # 0-1 (avantage historique)
```

### Output Prediction

```python
@dataclass
class EnsemblePrediction:
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    recommended_bet: Literal["home", "draw", "away"]
    confidence: float        # 0-1
    value_score: float | None
    model_contributions: dict[str, ModelContribution]
    llm_adjustments: LLMAdjustments | None
```
