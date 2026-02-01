"""Machine Learning module for football predictions.

This module provides:
- Historical data collection from football-data.org
- Feature engineering for match prediction
- XGBoost and Random Forest model training
- Automated retraining pipeline
- Model inference for predictions

Usage:
    # Collect data
    python -m src.ml.data_collector

    # Train models
    python -m src.ml.trainer

    # Run full pipeline
    python -m src.ml.pipeline full

    # Get prediction
    from src.ml.model_loader import get_ml_prediction
    result = get_ml_prediction(home_team_id=1, away_team_id=2)
"""

from .model_loader import get_ml_prediction, model_loader, TrainedModelLoader
from .pipeline import ml_pipeline, start_ml_scheduler, run_pipeline_now

__all__ = [
    "get_ml_prediction",
    "model_loader",
    "TrainedModelLoader",
    "ml_pipeline",
    "start_ml_scheduler",
    "run_pipeline_now",
]
