"""
HuggingFace ML Service Client

Calls the HuggingFace Space for ML predictions instead of loading models locally.
This reduces memory usage on Render (512MB limit).
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# HuggingFace Space URL
HF_ML_SERVICE_URL = os.getenv("HF_ML_SERVICE_URL", "https://jdevot244-paris-sportif.hf.space")

# Timeout for ML requests (training can take longer)
PREDICT_TIMEOUT = 30.0
TRAIN_TIMEOUT = 300.0  # 5 minutes for training

# Cache for service availability
_hf_service_available: bool | None = None


class HuggingFaceMLClient:
    """Client for HuggingFace ML Service."""

    def __init__(self, base_url: str = HF_ML_SERVICE_URL):
        self.base_url = base_url.rstrip("/")

    async def health_check(self) -> dict:
        """Check if ML service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.json()
        except Exception as e:
            logger.error(f"ML service health check failed: {e}")
            return {"status": "error", "message": str(e)}

    async def get_models_status(self) -> dict:
        """Get status of loaded models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models")
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get models status: {e}")
            return {"error": str(e)}

    async def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        home_elo: float = 1500.0,
        away_elo: float = 1500.0,
        home_form: float = 0.5,
        away_form: float = 0.5,
        home_rest_days: float = 7.0,
        away_rest_days: float = 7.0,
        home_fixture_congestion: float = 0.0,
        away_fixture_congestion: float = 0.0,
    ) -> dict[str, Any] | None:
        """
        Get ML predictions from HuggingFace service.

        Returns:
            Dict with xgboost, random_forest, and ensemble predictions
            or None if service is unavailable.
        """
        try:
            async with httpx.AsyncClient(timeout=PREDICT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    json={
                        "home_attack": home_attack,
                        "home_defense": home_defense,
                        "away_attack": away_attack,
                        "away_defense": away_defense,
                        "home_elo": home_elo,
                        "away_elo": away_elo,
                        "home_form": home_form,
                        "away_form": away_form,
                        "home_rest_days": home_rest_days,
                        "away_rest_days": away_rest_days,
                        "home_fixture_congestion": home_fixture_congestion,
                        "away_fixture_congestion": away_fixture_congestion,
                    },
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"ML prediction failed: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.warning("ML prediction timed out")
            return None
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return None

    async def trigger_training(self) -> dict:
        """Trigger auto-training on HuggingFace service."""
        try:
            async with httpx.AsyncClient(timeout=TRAIN_TIMEOUT) as client:
                response = await client.post(f"{self.base_url}/train/auto")
                return response.json()
        except Exception as e:
            logger.error(f"Failed to trigger training: {e}")
            return {"status": "error", "message": str(e)}

    async def get_training_status(self) -> dict:
        """Get current training status."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/train/status")
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get training status: {e}")
            return {"status": "error", "message": str(e)}

    def predict_sync(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
        home_elo: float = 1500.0,
        away_elo: float = 1500.0,
        home_form: float = 0.5,
        away_form: float = 0.5,
        home_rest_days: float = 7.0,
        away_rest_days: float = 7.0,
        home_fixture_congestion: float = 0.0,
        away_fixture_congestion: float = 0.0,
    ) -> dict[str, Any] | None:
        """
        Synchronous version of predict for use in non-async contexts.

        Returns:
            Dict with xgboost, random_forest, and ensemble predictions
            or None if service is unavailable.
        """
        global _hf_service_available

        # Skip if we know service is down
        if _hf_service_available is False:
            return None

        try:
            with httpx.Client(timeout=PREDICT_TIMEOUT) as client:
                response = client.post(
                    f"{self.base_url}/predict",
                    json={
                        "home_attack": home_attack,
                        "home_defense": home_defense,
                        "away_attack": away_attack,
                        "away_defense": away_defense,
                        "home_elo": home_elo,
                        "away_elo": away_elo,
                        "home_form": home_form,
                        "away_form": away_form,
                        "home_rest_days": home_rest_days,
                        "away_rest_days": away_rest_days,
                        "home_fixture_congestion": home_fixture_congestion,
                        "away_fixture_congestion": away_fixture_congestion,
                    },
                )

                if response.status_code == 200:
                    _hf_service_available = True
                    return response.json()
                else:
                    logger.warning(f"ML prediction failed: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.warning("ML prediction timed out")
            return None
        except httpx.ConnectError:
            logger.warning("HuggingFace ML service unavailable")
            _hf_service_available = False
            return None
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return None

    def health_check_sync(self) -> dict:
        """Synchronous health check."""
        global _hf_service_available

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/health")
                result = response.json()
                _hf_service_available = result.get("status") == "healthy"
                return result
        except Exception as e:
            _hf_service_available = False
            logger.error(f"ML service health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def is_available(self) -> bool:
        """Check if HuggingFace ML service is available."""
        global _hf_service_available

        if _hf_service_available is None:
            self.health_check_sync()

        return _hf_service_available or False


# Singleton instance
_client: HuggingFaceMLClient | None = None


def get_hf_ml_client() -> HuggingFaceMLClient:
    """Get or create HuggingFace ML client singleton."""
    global _client
    if _client is None:
        _client = HuggingFaceMLClient()
    return _client


async def get_ml_prediction_from_hf(
    home_attack: float, home_defense: float, away_attack: float, away_defense: float, **kwargs
) -> dict[str, float] | None:
    """
    Convenience function to get ML predictions.

    Returns ensemble probabilities or None if unavailable.
    """
    client = get_hf_ml_client()
    result = await client.predict(
        home_attack=home_attack,
        home_defense=home_defense,
        away_attack=away_attack,
        away_defense=away_defense,
        **kwargs,
    )

    if result and result.get("ensemble"):
        return result["ensemble"]

    return None
