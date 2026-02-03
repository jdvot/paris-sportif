"""Integration tests for prediction endpoints."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.data.sources.football_data import MatchData


class TestPredictionEndpointsAuth:
    """Test suite for prediction endpoint authentication."""

    def test_get_daily_picks_without_auth(self, client_no_auth: TestClient):
        """Test that daily picks endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/predictions/daily")
        assert response.status_code == 401

    def test_get_prediction_without_auth(self, client_no_auth: TestClient):
        """Test that prediction endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/predictions/12345")
        assert response.status_code == 401

    def test_get_prediction_stats_without_auth(self, client_no_auth: TestClient):
        """Test that prediction stats endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/predictions/stats")
        assert response.status_code == 401


class TestGetDailyPicks:
    """Test suite for GET /predictions/daily endpoint."""

    @patch("src.api.routes.predictions.get_football_data_client")
    @patch("src.api.routes.predictions.get_predictions_by_date")
    def test_get_daily_picks_from_cache(
        self,
        mock_db_predictions: MagicMock,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test daily picks retrieval from database cache."""
        # Mock cached predictions
        mock_db_predictions.return_value = [
            {
                "match_id": 12345,
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "competition_code": "PL",
                "match_date": "2026-02-05T20:00:00+00:00",
                "home_win_prob": 0.45,
                "draw_prob": 0.28,
                "away_win_prob": 0.27,
                "confidence": 0.72,
                "recommendation": "home_win",
                "explanation": "Test explanation",
                "created_at": "2026-02-03T10:00:00+00:00",
            }
        ]

        response = client.get("/api/v1/predictions/daily")

        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "picks" in data
        assert "total_matches_analyzed" in data

    @patch("src.api.routes.predictions.get_football_data_client")
    @patch("src.api.routes.predictions.get_predictions_by_date")
    @patch("src.api.routes.predictions.save_prediction")
    def test_get_daily_picks_generates_new(
        self,
        mock_save: MagicMock,
        mock_db_predictions: MagicMock,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test daily picks generation when no cache exists."""
        mock_db_predictions.return_value = []  # No cached predictions

        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/daily")

        assert response.status_code == 200
        data = response.json()
        assert "picks" in data

    @patch("src.api.routes.predictions.get_football_data_client")
    @patch("src.api.routes.predictions.get_predictions_by_date")
    def test_get_daily_picks_with_date_param(
        self,
        mock_db_predictions: MagicMock,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test daily picks with specific date parameter."""
        mock_db_predictions.return_value = []

        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/daily", params={"date": "2026-02-10"})

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-02-10"

    @patch("src.api.routes.predictions.get_football_data_client")
    @patch("src.api.routes.predictions.get_predictions_by_date")
    def test_get_daily_picks_empty_response(
        self,
        mock_db_predictions: MagicMock,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test daily picks returns empty list when no matches."""
        mock_db_predictions.return_value = []

        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/daily")

        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["total_matches_analyzed"] == 0


class TestGetPrediction:
    """Test suite for GET /predictions/{match_id} endpoint."""

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_get_prediction_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test successful prediction retrieval."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == 12345
        assert "probabilities" in data
        assert "recommended_bet" in data
        assert "confidence" in data
        assert "explanation" in data
        assert "key_factors" in data
        assert "risk_factors" in data

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_get_prediction_with_model_details(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test prediction with model details included."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.get(
            "/api/v1/predictions/12345",
            params={"include_model_details": True},
        )

        assert response.status_code == 200
        data = response.json()
        # Model details should be present when requested
        assert "model_contributions" in data or data.get("model_contributions") is None
        assert "llm_adjustments" in data or data.get("llm_adjustments") is None

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_get_prediction_api_error_fallback(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test prediction fallback on API error."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(side_effect=FootballDataAPIError("API Error"))
        mock_api_client.return_value = mock_client

        # Should return fallback prediction
        response = client.get("/api/v1/predictions/99999")

        assert response.status_code == 200
        data = response.json()
        assert "probabilities" in data

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_get_prediction_not_found(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test prediction for non-existent match returns 404."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(
            side_effect=FootballDataAPIError("Match not found")
        )
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/00000")

        assert response.status_code == 404

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_get_prediction_rate_limit(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test prediction fallback on rate limit."""
        from src.core.exceptions import RateLimitError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(side_effect=RateLimitError("Rate limited"))
        mock_api_client.return_value = mock_client

        # Should return fallback prediction
        response = client.get("/api/v1/predictions/12345")

        assert response.status_code == 200


class TestPredictionProbabilities:
    """Test suite for prediction probability validation."""

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_probabilities_sum_to_one(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test that prediction probabilities sum to approximately 1."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/12345")

        assert response.status_code == 200
        data = response.json()
        probs = data["probabilities"]
        total = probs["home_win"] + probs["draw"] + probs["away_win"]

        # Allow small floating point errors
        assert 0.99 <= total <= 1.01

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_probabilities_in_valid_range(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test that all probabilities are between 0 and 1."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/predictions/12345")

        assert response.status_code == 200
        data = response.json()
        probs = data["probabilities"]

        assert 0 <= probs["home_win"] <= 1
        assert 0 <= probs["draw"] <= 1
        assert 0 <= probs["away_win"] <= 1
        assert 0 <= data["confidence"] <= 1


class TestGetPredictionStats:
    """Test suite for GET /predictions/stats endpoint."""

    @patch("src.data.database.verify_finished_matches")
    @patch("src.data.database.get_prediction_statistics")
    @patch("src.data.database.get_all_predictions_stats")
    def test_get_prediction_stats_success(
        self,
        mock_all_stats: MagicMock,
        mock_stats: MagicMock,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test successful stats retrieval."""
        mock_verify.return_value = None
        mock_stats.return_value = {
            "total_predictions": 100,
            "correct_predictions": 65,
            "accuracy": 0.65,
            "roi_simulated": 0.08,
            "by_competition": {"PL": {"total": 50, "correct": 35}},
            "by_bet_type": {"home_win": {"total": 40, "correct": 28}},
        }

        response = client.get("/api/v1/predictions/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_predictions" in data
        assert "correct_predictions" in data
        assert "accuracy" in data
        assert "roi_simulated" in data
        assert "by_competition" in data
        assert "by_bet_type" in data

    @patch("src.data.database.verify_finished_matches")
    @patch("src.data.database.get_prediction_statistics")
    @patch("src.data.database.get_all_predictions_stats")
    def test_get_prediction_stats_with_days_param(
        self,
        mock_all_stats: MagicMock,
        mock_stats: MagicMock,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test stats with days parameter."""
        mock_verify.return_value = None
        mock_stats.return_value = {
            "total_predictions": 50,
            "correct_predictions": 30,
            "accuracy": 0.60,
            "roi_simulated": 0.05,
            "by_competition": {},
            "by_bet_type": {},
        }

        response = client.get("/api/v1/predictions/stats", params={"days": 7})

        assert response.status_code == 200


class TestRefreshPrediction:
    """Test suite for POST /predictions/{match_id}/refresh endpoint."""

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_refresh_prediction_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test successful prediction refresh."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.post("/api/v1/predictions/12345/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["match_id"] == "12345"

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_refresh_prediction_not_found(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test refresh for non-existent match."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(
            side_effect=FootballDataAPIError("Match not found")
        )
        mock_api_client.return_value = mock_client

        response = client.post("/api/v1/predictions/00000/refresh")

        assert response.status_code == 404

    @patch("src.api.routes.predictions.get_football_data_client")
    def test_refresh_prediction_rate_limit(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test refresh on rate limit."""
        from src.core.exceptions import RateLimitError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(side_effect=RateLimitError("Rate limited"))
        mock_api_client.return_value = mock_client

        response = client.post("/api/v1/predictions/12345/refresh")

        assert response.status_code == 429
