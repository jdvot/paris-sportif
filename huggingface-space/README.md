---
title: Paris Sportif ML
emoji: ⚽
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# Paris Sportif ML Service

Machine Learning prediction service for football match outcomes using XGBoost and Random Forest models.

## Features

- **XGBoost Classifier**: Gradient boosting for match outcome prediction
- **Random Forest Classifier**: Ensemble learning for robust predictions
- **Ensemble Predictions**: Combined predictions from both models
- **REST API**: FastAPI endpoints for health checks, model status, and predictions

## API Endpoints

### `GET /`
Root endpoint with service information.

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": true,
  "loaded_at": "2026-02-05T08:00:00",
  "backend_url": "https://paris-sportif-api.onrender.com"
}
```

### `GET /models`
Get loaded models status.

**Response:**
```json
{
  "xgboost": {"loaded": true, "type": "XGBClassifier"},
  "random_forest": {"loaded": true, "type": "RandomForestClassifier"},
  "loaded_at": "2026-02-05T08:00:00"
}
```

### `POST /predict`
Generate match outcome predictions.

**Request:**
```json
{
  "home_attack": 1.5,
  "home_defense": 1.2,
  "away_attack": 1.3,
  "away_defense": 1.4,
  "home_elo": 1600,
  "away_elo": 1550,
  "home_form": 0.6,
  "away_form": 0.5,
  "home_rest_days": 7.0,
  "away_rest_days": 7.0,
  "home_fixture_congestion": 0.0,
  "away_fixture_congestion": 0.0
}
```

**Response:**
```json
{
  "xgboost": {
    "home_win": 0.45,
    "draw": 0.30,
    "away_win": 0.25
  },
  "random_forest": {
    "home_win": 0.42,
    "draw": 0.32,
    "away_win": 0.26
  },
  "ensemble": {
    "home_win": 0.435,
    "draw": 0.31,
    "away_win": 0.255
  },
  "predicted_at": "2026-02-05T08:30:00"
}
```

### `POST /train`
Trigger model training (placeholder for future implementation).

## Environment Variables

Set these in the HuggingFace Space settings:

- `BACKEND_API_URL`: URL of the Paris Sportif backend API (default: `https://paris-sportif-api.onrender.com`)
- `HF_TRAINING_API_KEY`: Shared secret for accessing training data from backend

## Architecture

This service is part of the Paris Sportif prediction ensemble:

1. **Backend (Render)**: Statistical models (Poisson, ELO, Dixon-Coles)
2. **HuggingFace Space**: ML models (XGBoost, Random Forest)
3. **Ensemble**: Weighted combination of all models

The HuggingFace Space handles compute-intensive ML inference separately from the main backend to optimize resource usage.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Test endpoints
curl http://localhost:7860/health
```

## Deployment

This Space is automatically deployed when changes are pushed to the repository.

The backend calls this service at: `https://jdevot244-paris-sportif.hf.space`
