"""ML Pipeline API endpoints.

Provides endpoints for:
- Checking ML model status (admin only)
- Running data collection (admin only)
- Running model training (admin only)
- Full pipeline execution (admin only)
- Training data export (API key protected, for HuggingFace)
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser
from src.db import get_db_context

router = APIRouter()
logger = logging.getLogger(__name__)

# API key for HuggingFace training data access
# Set via HF_TRAINING_API_KEY env var on both Render and HuggingFace
HF_TRAINING_API_KEY = os.getenv("HF_TRAINING_API_KEY", "")


class MLStatusResponse(BaseModel):
    """ML system status response."""

    models_trained: bool
    xgboost_available: bool
    random_forest_available: bool
    data_age_days: int | None
    last_training: datetime | None
    feature_state_loaded: bool


class PipelineResponse(BaseModel):
    """Pipeline execution response."""

    message: str
    status: str
    task_id: str | None = None


# Track background task status
_pipeline_status: dict[str, Any] = {
    "running": False,
    "last_run": None,
    "last_result": None,
}


@router.get("/status", response_model=MLStatusResponse, responses=ADMIN_RESPONSES)
async def get_ml_status(user: AdminUser) -> MLStatusResponse:
    """
    Get current ML system status.

    Returns information about:
    - Whether models are trained and available
    - Age of training data
    - Feature engineering state
    """
    try:
        from src.ml.data_collector import HistoricalDataCollector
        from src.ml.model_loader import model_loader

        collector = HistoricalDataCollector()
        data_age = collector.get_data_age_days()

        return MLStatusResponse(
            models_trained=model_loader.is_trained(),
            xgboost_available=model_loader.xgb_model is not None,
            random_forest_available=model_loader.rf_model is not None,
            data_age_days=data_age,
            last_training=None,  # TODO: Track this
            feature_state_loaded=model_loader.feature_state is not None,
        )
    except ImportError as e:
        logger.warning(f"ML module not available: {e}")
        return MLStatusResponse(
            models_trained=False,
            xgboost_available=False,
            random_forest_available=False,
            data_age_days=None,
            last_training=None,
            feature_state_loaded=False,
        )


@router.post("/collect", response_model=PipelineResponse, responses=ADMIN_RESPONSES)
async def collect_data(user: AdminUser, background_tasks: BackgroundTasks) -> PipelineResponse:
    """
    Start data collection in background.

    Collects historical match data from football-data.org API.
    This is a long-running task that runs in the background.
    """
    if _pipeline_status["running"]:
        raise HTTPException(status_code=409, detail="A pipeline task is already running")

    def run_collection_sync() -> None:
        global _pipeline_status
        _pipeline_status["running"] = True
        try:
            from src.ml.data_collector import HistoricalDataCollector

            async def _collect() -> None:
                collector = HistoricalDataCollector()
                await collector.collect_all_historical_data()

            asyncio.run(_collect())
            _pipeline_status["last_result"] = "success"
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            _pipeline_status["last_result"] = f"failed: {e}"
        finally:
            _pipeline_status["running"] = False
            _pipeline_status["last_run"] = datetime.now()

    background_tasks.add_task(run_collection_sync)

    return PipelineResponse(
        message="Data collection started in background",
        status="running",
    )


@router.post("/train", response_model=PipelineResponse, responses=ADMIN_RESPONSES)
async def train_models(user: AdminUser, background_tasks: BackgroundTasks) -> PipelineResponse:
    """
    Start model training in background.

    Trains XGBoost and Random Forest models on collected data.
    Requires data to be collected first.
    """
    if _pipeline_status["running"]:
        raise HTTPException(status_code=409, detail="A pipeline task is already running")

    def run_training() -> None:
        global _pipeline_status
        _pipeline_status["running"] = True
        try:
            from src.ml.model_loader import model_loader
            from src.ml.trainer import MLTrainer

            trainer = MLTrainer()
            success = trainer.train_all()

            if success:
                model_loader.reload_models()
                _pipeline_status["last_result"] = "success"
            else:
                _pipeline_status["last_result"] = "failed: training returned False"
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            _pipeline_status["last_result"] = f"failed: {e}"
        finally:
            _pipeline_status["running"] = False
            _pipeline_status["last_run"] = datetime.now()

    background_tasks.add_task(run_training)

    return PipelineResponse(
        message="Model training started in background",
        status="running",
    )


@router.post("/run-full", response_model=PipelineResponse, responses=ADMIN_RESPONSES)
async def run_full_pipeline(user: AdminUser, background_tasks: BackgroundTasks) -> PipelineResponse:
    """
    Run full ML pipeline in background.

    Executes:
    1. Data collection from API
    2. Model training on collected data
    3. Model reloading for inference

    This is a long-running task (5-15 minutes depending on API rate limits).
    """
    if _pipeline_status["running"]:
        raise HTTPException(status_code=409, detail="A pipeline task is already running")

    def run_full_sync() -> None:
        global _pipeline_status
        _pipeline_status["running"] = True
        try:
            from src.ml.pipeline import run_pipeline_now

            async def _run() -> bool:
                return await run_pipeline_now()

            success = asyncio.run(_run())
            _pipeline_status["last_result"] = "success" if success else "failed"
        except Exception as e:
            logger.error(f"Full pipeline failed: {e}")
            _pipeline_status["last_result"] = f"failed: {e}"
        finally:
            _pipeline_status["running"] = False
            _pipeline_status["last_run"] = datetime.now()

    background_tasks.add_task(run_full_sync)

    return PipelineResponse(
        message="Full ML pipeline started in background. This may take 5-15 minutes.",
        status="running",
    )


@router.get("/pipeline-status", response_model=PipelineResponse, responses=ADMIN_RESPONSES)
async def get_pipeline_status(user: AdminUser) -> PipelineResponse:
    """
    Get current pipeline execution status.

    Returns whether a pipeline task is running and the result of the last run.
    """
    if _pipeline_status["running"]:
        return PipelineResponse(
            message="Pipeline task is currently running",
            status="running",
        )

    last_run = _pipeline_status.get("last_run")
    last_result = _pipeline_status.get("last_result", "never_run")

    return PipelineResponse(
        message=f"Last run: {last_run.isoformat() if last_run else 'never'}, result: {last_result}",
        status="idle" if last_result in ["success", None, "never_run"] else "error",
    )


# ============================================================================
# Public endpoints for HuggingFace training data
# ============================================================================


class TrainingMatch(BaseModel):
    """A single match for ML training."""

    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float
    home_elo: float
    away_elo: float
    home_form: float
    away_form: float
    home_rest_days: float
    away_rest_days: float
    home_fixture_congestion: float
    away_fixture_congestion: float
    result: int  # 0=home_win, 1=draw, 2=away_win


class TrainingDataResponse(BaseModel):
    """Training data response for HuggingFace."""

    matches: list[TrainingMatch]
    count: int


@router.get("/training-data", response_model=TrainingDataResponse)
async def get_training_data(
    limit: int = 1000,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> TrainingDataResponse:
    """
    Get finished matches for ML training (API key protected).

    This endpoint is called by HuggingFace Spaces to fetch training data.
    Requires X-API-Key header matching HF_TRAINING_API_KEY env var.

    Returns matches with:
    - Team stats (attack, defense, ELO)
    - Form and fatigue metrics
    - Result (0=home_win, 1=draw, 2=away_win)
    """
    # Validate API key
    if not HF_TRAINING_API_KEY:
        raise HTTPException(status_code=503, detail="Training data API not configured")

    if x_api_key != HF_TRAINING_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    from sqlalchemy import text

    matches: list[TrainingMatch] = []

    try:
        with get_db_context() as db:
            # Fetch finished matches with team stats from teams table
            # Attack = avg_goals_scored, Defense = avg_goals_conceded
            # If no stats, use defaults (1.0 for attack/defense, 1500 for ELO)
            query = text("""
                SELECT
                    m.id,
                    m.home_score,
                    m.away_score,
                    m.status,
                    -- Home team stats from teams table
                    COALESCE(ht.avg_goals_scored_home, 1.0) as home_attack,
                    COALESCE(ht.avg_goals_conceded_home, 1.0) as home_defense,
                    COALESCE(ht.elo_rating, 1500) as home_elo,
                    -- Away team stats from teams table
                    COALESCE(at.avg_goals_scored_away, 1.0) as away_attack,
                    COALESCE(at.avg_goals_conceded_away, 1.0) as away_defense,
                    COALESCE(at.elo_rating, 1500) as away_elo
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams at ON m.away_team_id = at.id
                WHERE m.status = 'FINISHED'
                    AND m.home_score IS NOT NULL
                    AND m.away_score IS NOT NULL
                ORDER BY m.match_date DESC
                LIMIT :limit
            """)

            result = db.execute(query, {"limit": limit})
            rows = result.fetchall()

            for row in rows:
                # Determine result
                if row.home_score > row.away_score:
                    match_result = 0  # Home win
                elif row.home_score < row.away_score:
                    match_result = 2  # Away win
                else:
                    match_result = 1  # Draw

                # Use team stats, with defaults for form/fatigue (not tracked yet)
                matches.append(TrainingMatch(
                    home_attack=float(row.home_attack) if row.home_attack else 1.0,
                    home_defense=float(row.home_defense) if row.home_defense else 1.0,
                    away_attack=float(row.away_attack) if row.away_attack else 1.0,
                    away_defense=float(row.away_defense) if row.away_defense else 1.0,
                    home_elo=float(row.home_elo) if row.home_elo else 1500.0,
                    away_elo=float(row.away_elo) if row.away_elo else 1500.0,
                    home_form=0.5,  # Default - not tracked in teams table
                    away_form=0.5,
                    home_rest_days=7.0,  # Default - not tracked
                    away_rest_days=7.0,
                    home_fixture_congestion=0.0,  # Default - not tracked
                    away_fixture_congestion=0.0,
                    result=match_result,
                ))

            logger.info(f"Returning {len(matches)} matches for ML training")

    except Exception as e:
        logger.error(f"Failed to fetch training data: {e}")
        # Return empty list on error
        pass

    return TrainingDataResponse(matches=matches, count=len(matches))
