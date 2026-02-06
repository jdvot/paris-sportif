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

    Checks HuggingFace ML service (remote) instead of local models
    to avoid OOM on 512MB Render.
    """
    import httpx

    hf_url = os.getenv("HF_SPACE_URL", "https://jdevot244-paris-sportif.hf.space")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{hf_url}/models")

            if response.status_code == 200:
                data = response.json()
                return MLStatusResponse(
                    models_trained=data.get("xgboost", {}).get("loaded", False),
                    xgboost_available=data.get("xgboost", {}).get("loaded", False),
                    random_forest_available=data.get("random_forest", {}).get("loaded", False),
                    data_age_days=None,  # Not tracked on HuggingFace
                    last_training=None,
                    feature_state_loaded=True,  # HuggingFace handles features
                )

    except Exception as e:
        logger.warning(f"HuggingFace ML status check failed: {e}")

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
async def train_models(user: AdminUser) -> PipelineResponse:
    """
    Deprecated: Use /train-remote instead.

    Local training is disabled to avoid OOM on 512MB Render.
    Models are trained on HuggingFace Spaces (16GB RAM).
    """
    return PipelineResponse(
        message=(
            "Local training disabled (OOM risk). "
            "Use POST /api/v1/ml/train-remote to train on HuggingFace."
        ),
        status="disabled",
    )


@router.post("/run-full", response_model=PipelineResponse, responses=ADMIN_RESPONSES)
async def run_full_pipeline(user: AdminUser) -> PipelineResponse:
    """
    Deprecated: Use /train-remote instead.

    Local ML pipeline is disabled to avoid OOM on 512MB Render.
    Models are trained on HuggingFace Spaces (16GB RAM).
    """
    return PipelineResponse(
        message=(
            "Local pipeline disabled (OOM risk). "
            "Use POST /api/v1/ml/train-remote to train on HuggingFace."
        ),
        status="disabled",
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
            query = text(
                """
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
            """
            )

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
                matches.append(
                    TrainingMatch(
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
                    )
                )

            logger.info(f"Returning {len(matches)} matches for ML training")

    except Exception as e:
        logger.error(f"Failed to fetch training data: {e}")
        # Return empty list on error
        pass

    return TrainingDataResponse(matches=matches, count=len(matches))


# HuggingFace Space URL
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "https://jdevot244-paris-sportif.hf.space")


class HFTrainingResponse(BaseModel):
    """Response from HuggingFace training endpoint."""

    status: str
    models_trained: list[str] | None = None
    training_samples: int | None = None
    accuracy_xgboost: float | None = None
    accuracy_random_forest: float | None = None
    message: str | None = None
    error: str | None = None


@router.post("/train-remote", response_model=HFTrainingResponse, responses=ADMIN_RESPONSES)
async def train_on_huggingface(user: AdminUser) -> HFTrainingResponse:
    """
    Trigger model training on HuggingFace Spaces.

    This endpoint:
    1. Fetches training data from database (finished matches with stats)
    2. Sends data to HuggingFace /train endpoint
    3. Returns training results (accuracy, feature importance)

    Requires admin authentication.
    """
    import httpx
    from sqlalchemy import text

    logger.info("Triggering training on HuggingFace Spaces...")

    # Step 1: Fetch training data from database
    training_matches: list[dict[str, Any]] = []

    try:
        with get_db_context() as db:
            query = text(
                """
                SELECT
                    m.id,
                    m.home_score,
                    m.away_score,
                    COALESCE(ht.avg_goals_scored_home, 1.0) as home_attack,
                    COALESCE(ht.avg_goals_conceded_home, 1.0) as home_defense,
                    COALESCE(ht.elo_rating, 1500) as home_elo,
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
                LIMIT 2000
            """
            )

            result = db.execute(query)
            rows = result.fetchall()

            for row in rows:
                training_matches.append(
                    {
                        "home_attack": float(row.home_attack) if row.home_attack else 1.0,
                        "home_defense": float(row.home_defense) if row.home_defense else 1.0,
                        "away_attack": float(row.away_attack) if row.away_attack else 1.0,
                        "away_defense": float(row.away_defense) if row.away_defense else 1.0,
                        "home_elo": float(row.home_elo) if row.home_elo else 1500.0,
                        "away_elo": float(row.away_elo) if row.away_elo else 1500.0,
                        "home_form": 0.5,
                        "away_form": 0.5,
                        "home_rest_days": 7.0,
                        "away_rest_days": 7.0,
                        "home_fixture_congestion": 0.0,
                        "away_fixture_congestion": 0.0,
                        "home_score": row.home_score,
                        "away_score": row.away_score,
                    }
                )

        logger.info(f"Fetched {len(training_matches)} matches for training")

    except Exception as e:
        logger.error(f"Failed to fetch training data: {e}")
        return HFTrainingResponse(
            status="error",
            error=f"Failed to fetch training data: {str(e)}",
        )

    if len(training_matches) < 50:
        return HFTrainingResponse(
            status="error",
            error=f"Not enough training data: {len(training_matches)} matches (need 50+)",
        )

    # Step 2: Send to HuggingFace for training
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for training
            response = await client.post(
                f"{HF_SPACE_URL}/train",
                json={"matches": training_matches},
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"Training complete: XGB={data.get('accuracy_xgboost')}, "
                    f"RF={data.get('accuracy_random_forest')}"
                )

                return HFTrainingResponse(
                    status="success",
                    models_trained=data.get("models_trained"),
                    training_samples=data.get("training_samples"),
                    accuracy_xgboost=data.get("accuracy_xgboost"),
                    accuracy_random_forest=data.get("accuracy_random_forest"),
                    message=f"Models trained with {data.get('training_samples')} matches",
                )
            else:
                error_detail = response.text
                logger.error(
                    f"HuggingFace training failed: {response.status_code} - {error_detail}"
                )
                return HFTrainingResponse(
                    status="error",
                    error=f"HuggingFace returned {response.status_code}: {error_detail}",
                )

    except httpx.TimeoutException:
        logger.error("HuggingFace training timed out")
        return HFTrainingResponse(
            status="error",
            error="Training timed out (>5 minutes)",
        )
    except Exception as e:
        logger.error(f"Failed to call HuggingFace: {e}")
        return HFTrainingResponse(
            status="error",
            error=f"Failed to call HuggingFace: {str(e)}",
        )
