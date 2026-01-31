# Architecture de l'API Prédictions

## Structure de l'Implémentation

```
/backend/src/api/routes/predictions.py (525 lignes)
├── Imports & Router Setup
├── Modèles Pydantic (7 classes)
│   ├── PredictionProbabilities
│   ├── ModelContributions
│   ├── LLMAdjustments
│   ├── PredictionResponse
│   ├── DailyPickResponse
│   ├── DailyPicksResponse
│   └── PredictionStatsResponse
├── Mock Data (10 matchs)
│   ├── MOCK_MATCHES
│   ├── COMPETITION_NAMES
│   ├── KEY_FACTORS_TEMPLATES
│   ├── RISK_FACTORS_TEMPLATES
│   └── EXPLANATIONS_TEMPLATES
├── Fonctions Utilitaires (3)
│   ├── _generate_realistic_probabilities()
│   ├── _get_recommended_bet()
│   └── _generate_prediction()
└── Endpoints (4)
    ├── GET /daily
    ├── GET /{match_id}
    ├── GET /stats
    └── POST /{match_id}/refresh
```

## Flux de Données pour GET /api/v1/predictions/daily

```
Client Request (GET /daily?date=2025-02-02)
    ↓
get_daily_picks(date)
    ├── Parse date or default to today
    ├── Filter MOCK_MATCHES by date
    │
    ├── For each match:
    │   └── _generate_prediction(match)
    │       ├── _generate_realistic_probabilities(strength_ratio)
    │       │   ├── Base probabilities (home, draw, away)
    │       │   └── Normalize to sum = 1.0
    │       ├── _get_recommended_bet(probabilities)
    │       ├── Generate confidence (60-85%)
    │       ├── Generate value_score (5-18%)
    │       ├── Select key_factors (français)
    │       ├── Select risk_factors (français)
    │       ├── Generate explanation (français)
    │       └── (Optional) Model contributions & LLM adjustments
    │
    ├── Calculate pick_scores (confidence × value_score)
    ├── Sort by pick_score descending
    ├── Select top 5 picks
    ├── Wrap in DailyPickResponse with rank
    │
    └── Return DailyPicksResponse
        ├── date: "2025-02-02"
        ├── picks: [DailyPickResponse × 5]
        └── total_matches_analyzed: int
    ↓
Client Response (JSON)
```

## Flux de Données pour GET /api/v1/predictions/{match_id}

```
Client Request (GET /1?include_model_details=true)
    ↓
get_prediction(match_id=1, include_model_details=True)
    ├── Find match in MOCK_MATCHES
    │
    └── _generate_prediction(match, include_model_details=True)
        ├── _generate_realistic_probabilities(strength_ratio)
        ├── _get_recommended_bet()
        ├── Generate confidence, value_score
        ├── Select factors and explanation
        │
        ├── if include_model_details:
        │   ├── Generate ModelContributions
        │   │   ├── Poisson variations
        │   │   ├── XGBoost (consensus)
        │   │   ├── XG Model variations
        │   │   └── Elo rating variations
        │   │
        │   └── Generate LLMAdjustments
        │       ├── injury_impact_home/away
        │       ├── sentiment_home/away
        │       ├── tactical_edge
        │       ├── total_adjustment
        │       └── reasoning
        │
        └── Return PredictionResponse
    ↓
Client Response (JSON)
```

## Flux de Données pour GET /api/v1/predictions/stats

```
Client Request (GET /stats?days=30)
    ↓
get_prediction_stats(days=30)
    ├── Generate total_predictions (150-250)
    ├── Generate correct_predictions (52-62% accuracy)
    ├── Calculate accuracy ratio
    ├── Generate roi_simulated (8-25%)
    │
    ├── For each competition:
    │   ├── Generate total predictions
    │   ├── Generate correct predictions
    │   └── Calculate accuracy
    │
    ├── For each bet_type:
    │   ├── Generate total predictions
    │   ├── Generate correct predictions
    │   ├── Calculate accuracy
    │   └── Generate avg_value
    │
    └── Return PredictionStatsResponse
    ↓
Client Response (JSON)
```

## Modèles de Données

### Hiérarchie des Modèles

```
PredictionResponse (Principal)
├── match_id: int
├── home_team: str
├── away_team: str
├── competition: str
├── match_date: datetime
├── probabilities: PredictionProbabilities
│   ├── home_win: float
│   ├── draw: float
│   └── away_win: float
├── recommended_bet: Literal["home_win", "draw", "away_win"]
├── confidence: float
├── value_score: float
├── explanation: str (français)
├── key_factors: list[str] (français)
├── risk_factors: list[str] (français)
├── model_contributions: ModelContributions | None
│   ├── poisson: PredictionProbabilities
│   ├── xgboost: PredictionProbabilities
│   ├── xg_model: PredictionProbabilities
│   └── elo: PredictionProbabilities
├── llm_adjustments: LLMAdjustments | None
│   ├── injury_impact_home: float
│   ├── injury_impact_away: float
│   ├── sentiment_home: float
│   ├── sentiment_away: float
│   ├── tactical_edge: float
│   ├── total_adjustment: float
│   └── reasoning: str
├── created_at: datetime
└── is_daily_pick: bool

DailyPickResponse
├── rank: int (1-5)
├── prediction: PredictionResponse
└── pick_score: float

DailyPicksResponse
├── date: str
├── picks: list[DailyPickResponse]
└── total_matches_analyzed: int

PredictionStatsResponse
├── total_predictions: int
├── correct_predictions: int
├── accuracy: float
├── roi_simulated: float
├── by_competition: dict[str, dict]
│   └── {competition: {total, correct, accuracy}}
├── by_bet_type: dict[str, dict]
│   └── {bet_type: {total, correct, accuracy, avg_value}}
└── last_updated: datetime
```

## Algorithme de Sélection des Picks du Jour

```python
def select_daily_picks():
    matches_today = filter_by_date(today)
    
    for match in matches_today:
        prediction = generate_prediction(match)
        pick_score = prediction.confidence * prediction.value_score
        predictions.append((prediction, pick_score))
    
    # Sort by pick_score descending
    predictions.sort(by=pick_score, reverse=True)
    
    # Select top 5
    top_5 = predictions[:5]
    
    # Rank from 1 to 5
    for rank, (pred, score) in enumerate(top_5, 1):
        yield DailyPickResponse(
            rank=rank,
            prediction=pred,
            pick_score=score
        )
```

## Algorithme de Génération de Probabilités

```python
def generate_realistic_probabilities(strength_ratio):
    if strength_ratio > 1.1:  # Home dominant
        home = uniform(0.50, 0.68)
        draw = uniform(0.20, 0.30)
        away = 1.0 - home - draw
    elif strength_ratio < 0.9:  # Away dominant
        away = uniform(0.40, 0.55)
        draw = uniform(0.22, 0.32)
        home = 1.0 - away - draw
    else:  # Balanced
        home = uniform(0.35, 0.45)
        away = uniform(0.35, 0.45)
        draw = 1.0 - home - away
    
    # Normalize to ensure sum = 1.0
    total = home + draw + away
    return (home/total, draw/total, away/total)
```

## Mock Data Structure

```
MOCK_MATCHES = [
    {
        "id": int,
        "home_team": str,
        "away_team": str,
        "competition": str ("PL", "PD", "BL1", "SA", "FL1"),
        "match_date": datetime
    },
    ...
]

COMPETITION_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}

KEY_FACTORS_TEMPLATES = {
    "home_dominant": [...],
    "away_strong": [...],
    "balanced": [...]
}

RISK_FACTORS_TEMPLATES = [...]

EXPLANATIONS_TEMPLATES = {
    "home_win": "...",
    "draw": "...",
    "away_win": "..."
}
```

## Validations et Contraintes

```
Probabilités:
  - Chaque valeur: 0.0 ≤ x ≤ 1.0
  - Somme totale: 1.0 (exactement)

Confidence:
  - Min: 0.60 (60%)
  - Max: 0.85 (85%)

Value Score:
  - Min: 0.05 (5%)
  - Max: 0.18 (18%)

Pick Rank:
  - Min: 1
  - Max: 5

Recommended Bet:
  - "home_win" si max(home_prob, draw_prob, away_prob) == home_prob
  - "draw" si max(...) == draw_prob
  - "away_win" si max(...) == away_prob

LLM Adjustments:
  - injury_impact_*: -0.3 ≤ x ≤ 0.0
  - sentiment_*: -0.1 ≤ x ≤ 0.1
  - tactical_edge: -0.05 ≤ x ≤ 0.05
  - total_adjustment: -0.5 ≤ x ≤ 0.5
```

## Route Registration

```python
# In main.py
app.include_router(
    predictions.router,
    prefix="/api/v1/predictions",
    tags=["Predictions"]
)

# Routes registered:
GET    /api/v1/predictions/daily
GET    /api/v1/predictions/{match_id}
GET    /api/v1/predictions/stats
POST   /api/v1/predictions/{match_id}/refresh
```

## Évolution Possible (Production)

```
Current State (Mock):
  predictions.py → MOCK_MATCHES → Response

Future State (DB):
  predictions.py → database.py → MATCHES table → Response

With ML Models:
  predictions.py → prediction_engine/
                   ├── models/poisson.py
                   ├── models/xgboost.py
                   ├── models/xg.py
                   └── models/elo.py
                   → Ensemble → Response

With LLM:
  predictions.py → llm/tasks/explanation.py
                 → Claude/Groq API
                 → Adjustments & Analysis
                 → Response
```

## Performance Considerations

```
Current (Mock):
  - GET /daily: ~1-5ms (in-memory generation)
  - GET /{match_id}: ~1-3ms (in-memory generation)
  - GET /stats: ~5-10ms (in-memory generation)

Future (Production):
  - GET /daily: ~100-500ms (DB query + ML)
  - GET /{match_id}: ~50-200ms (DB query + ML + LLM)
  - GET /stats: ~200-1000ms (DB aggregation)

Caching Strategy:
  - /daily: Redis 30 min TTL
  - /{match_id}: Redis 30 min TTL
  - /stats: Redis 60 min TTL
```

## Error Handling

```
Match not found (/{match_id}):
  ValueError("Match with ID {match_id} not found")
  → 400 Bad Request

Invalid date format (/daily?date=invalid):
  datetime.strptime() raises ValueError
  → FastAPI validation error → 422 Unprocessable Entity

Invalid days parameter (/stats?days=5):
  Field constraint: days must be 7-365
  → FastAPI validation error → 422 Unprocessable Entity
```

## Documentation Endpoints

```
GET /docs              → Swagger UI (OpenAPI)
GET /redoc             → ReDoc documentation
GET /openapi.json      → OpenAPI schema
```

L'API génère automatiquement la documentation interactive basée
sur les modèles Pydantic et les docstrings des endpoints.
