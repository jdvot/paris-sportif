"""ML Pipeline API endpoints.

Admin only endpoints.

Provides endpoints for:
- Checking ML model status
- Running data collection
- Running model training
- Full pipeline execution
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.auth import ADMIN_RESPONSES, AdminUser

router = APIRouter()
logger = logging.getLogger(__name__)


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
