"""
Paris Sportif ML Service
FastAPI app for XGBoost and Random Forest predictions
Deployed on HuggingFace Spaces
"""

import logging
import os
from datetime import datetime
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "https://paris-sportif-api.onrender.com")
HF_TRAINING_API_KEY = os.getenv("HF_TRAINING_API_KEY", "")

app = FastAPI(
    title="Paris Sportif ML Service",
    description="XGBoost and Random Forest predictions for football matches",
    version="1.0.0",
)

# Global models (loaded on startup)
xgboost_model = None
random_forest_model = None
models_loaded_at = None


class PredictRequest(BaseModel):
    """Match features for prediction."""
    home_attack: float = Field(..., description="Home team attack strength")
    home_defense: float = Field(..., description="Home team defense strength")
    away_attack: float = Field(..., description="Away team attack strength")
    away_defense: float = Field(..., description="Away team defense strength")
    home_elo: float = Field(1500.0, description="Home team ELO rating")
    away_elo: float = Field(1500.0, description="Away team ELO rating")
    home_form: float = Field(0.5, description="Home team recent form (0-1)")
    away_form: float = Field(0.5, description="Away team recent form (0-1)")
    home_rest_days: float = Field(7.0, description="Days since last match")
    away_rest_days: float = Field(7.0, description="Days since last match")
    home_fixture_congestion: float = Field(0.0, description="Fixture congestion score")
    away_fixture_congestion: float = Field(0.0, description="Fixture congestion score")


class PredictResponse(BaseModel):
    """Prediction results from both models."""
    xgboost: dict[str, Any]
    random_forest: dict[str, Any]
    ensemble: dict[str, Any]
    predicted_at: str


@app.on_event("startup")
async def load_models():
    """Load ML models on startup."""
    global xgboost_model, random_forest_model, models_loaded_at

    logger.info("Loading ML models...")

    try:
        # Try to load existing models
        xgboost_model = joblib.load("models/xgboost_model.pkl")
        random_forest_model = joblib.load("models/random_forest_model.pkl")
        models_loaded_at = datetime.utcnow().isoformat()
        logger.info("✅ Models loaded successfully")
    except FileNotFoundError:
        logger.warning("⚠️ No trained models found. Using dummy models with 12 features.")
        # Create dummy models that return reasonable probabilities
        from sklearn.ensemble import RandomForestClassifier
        xgboost_model = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=5)
        random_forest_model = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=5)

        # Train on dummy data with 12 features matching PredictRequest
        # Features: home_attack, home_defense, away_attack, away_defense,
        #           home_elo, away_elo, home_form, away_form,
        #           home_rest_days, away_rest_days, home_fixture_congestion, away_fixture_congestion
        np.random.seed(42)
        n_samples = 500
        X_dummy = np.random.randn(n_samples, 12)
        # Normalize features to realistic ranges
        X_dummy[:, 0:4] = np.abs(X_dummy[:, 0:4]) * 0.5 + 1.0  # Attack/defense: 1.0-1.5
        X_dummy[:, 4:6] = X_dummy[:, 4:6] * 100 + 1500  # ELO: 1400-1600
        X_dummy[:, 6:8] = np.clip(X_dummy[:, 6:8] * 0.2 + 0.5, 0, 1)  # Form: 0-1
        X_dummy[:, 8:10] = np.abs(X_dummy[:, 8:10]) * 3 + 3  # Rest days: 3-10
        X_dummy[:, 10:12] = np.clip(np.abs(X_dummy[:, 10:12]) * 0.3, 0, 1)  # Congestion: 0-0.5

        # Generate outcomes biased by features (home advantage + attack/defense)
        home_strength = X_dummy[:, 0] - X_dummy[:, 3] + (X_dummy[:, 4] - X_dummy[:, 5]) / 200
        y_dummy = np.zeros(n_samples, dtype=int)
        y_dummy[home_strength > 0.3] = 0  # Home win
        y_dummy[(home_strength >= -0.1) & (home_strength <= 0.3)] = 1  # Draw
        y_dummy[home_strength < -0.1] = 2  # Away win

        xgboost_model.fit(X_dummy, y_dummy)
        random_forest_model.fit(X_dummy, y_dummy)

        models_loaded_at = datetime.utcnow().isoformat()
        logger.info("✅ Dummy models initialized with 12 features")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Paris Sportif ML",
        "version": "1.0.0",
        "status": "running",
        "backend": BACKEND_API_URL,
        "models_loaded": models_loaded_at is not None,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_loaded": models_loaded_at is not None,
        "loaded_at": models_loaded_at,
        "backend_url": BACKEND_API_URL,
    }


@app.get("/models")
async def models_status():
    """Get models status."""
    return {
        "xgboost": {
            "loaded": xgboost_model is not None,
            "type": str(type(xgboost_model).__name__) if xgboost_model else None,
        },
        "random_forest": {
            "loaded": random_forest_model is not None,
            "type": str(type(random_forest_model).__name__) if random_forest_model else None,
        },
        "loaded_at": models_loaded_at,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Generate predictions using XGBoost and Random Forest.

    Returns probabilities for home_win, draw, away_win from both models.
    """
    if xgboost_model is None or random_forest_model is None:
        raise HTTPException(status_code=503, detail="Models not loaded")

    # Prepare features
    features = np.array([[
        request.home_attack,
        request.home_defense,
        request.away_attack,
        request.away_defense,
        request.home_elo,
        request.away_elo,
        request.home_form,
        request.away_form,
        request.home_rest_days,
        request.away_rest_days,
        request.home_fixture_congestion,
        request.away_fixture_congestion,
    ]])

    try:
        # XGBoost prediction
        xgb_proba = xgboost_model.predict_proba(features)[0]
        xgb_pred = {
            "home_win": float(xgb_proba[0]),
            "draw": float(xgb_proba[1]) if len(xgb_proba) > 1 else 0.0,
            "away_win": float(xgb_proba[2]) if len(xgb_proba) > 2 else 0.0,
        }

        # Random Forest prediction
        rf_proba = random_forest_model.predict_proba(features)[0]
        rf_pred = {
            "home_win": float(rf_proba[0]),
            "draw": float(rf_proba[1]) if len(rf_proba) > 1 else 0.0,
            "away_win": float(rf_proba[2]) if len(rf_proba) > 2 else 0.0,
        }

        # Ensemble (average of both models)
        ensemble_pred = {
            "home_win": (xgb_pred["home_win"] + rf_pred["home_win"]) / 2,
            "draw": (xgb_pred["draw"] + rf_pred["draw"]) / 2,
            "away_win": (xgb_pred["away_win"] + rf_pred["away_win"]) / 2,
        }

        return PredictResponse(
            xgboost=xgb_pred,
            random_forest=rf_pred,
            ensemble=ensemble_pred,
            predicted_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/train")
async def trigger_training():
    """
    Trigger model training (placeholder).

    In production, this would fetch training data from backend
    and retrain models.
    """
    return {
        "status": "training_not_implemented",
        "message": "Model training endpoint is a placeholder. Implement training logic here.",
        "backend_url": BACKEND_API_URL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
